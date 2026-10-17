"""Shared fixed-budget tactical evaluation of internal and external chess agents."""

import argparse
import json
import math
import random
import shutil
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from time import perf_counter

import chess

from chesslab.agents.external_uci import ExternalUciAgent, file_sha256
from chesslab.benchmark import search_budget_from_dict
from chesslab.config import json_object, nonempty_string, reject_unknown_fields
from chesslab.eval.artifacts import (
    capture_run_metadata,
    configuration_digest,
    write_artifact_json,
)
from chesslab.eval.benchmarks import BenchmarkPosition, budget_to_dict
from chesslab.games.chess import ChessState
from chesslab.match_suite import MatchAgentConfig, match_agent_config_from_dict
from chesslab.search import SearchBudget
from chesslab.search.results import SearchResult


@dataclass(frozen=True, slots=True)
class TacticalComparisonSpec:
    """Explicit labelled positions, named agents, seeds and one shared budget."""

    name: str
    question: str
    dataset: dict[str, str]
    positions: tuple[BenchmarkPosition, ...]
    agents: tuple[MatchAgentConfig, ...]
    seeds: tuple[int, ...]
    budget: SearchBudget

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "name": self.name,
            "question": self.question,
            "dataset": {
                **self.dataset,
                "positions": [p.to_dict() for p in self.positions],
            },
            "agents": [a.to_dict() for a in self.agents],
            "seeds": list(self.seeds),
            "budget": budget_to_dict(self.budget),
        }

    @property
    def digest(self) -> str:
        return configuration_digest(self.to_dict())

    def schedule(
        self,
    ) -> tuple[tuple[int, int, BenchmarkPosition, MatchAgentConfig], ...]:
        """Rotate agent order; share a derived RNG seed within each position pair."""
        cases = []
        for root_index, root_seed in enumerate(self.seeds):
            rng = random.Random(root_seed)
            for index, position in enumerate(self.positions):
                seed = rng.getrandbits(128)
                offset = (root_index + index) % len(self.agents)
                for agent in self.agents[offset:] + self.agents[:offset]:
                    cases.append((root_seed, seed, position, agent))
        return tuple(cases)


def comparison_spec_from_dict(value: object) -> TacticalComparisonSpec:
    """Reject ambiguous labels, duplicate positions and misspelled settings."""
    data = json_object(value, "comparison")
    reject_unknown_fields(
        data,
        {"schema_version", "name", "question", "dataset", "agents", "seeds", "budget"},
        "comparison",
    )
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    dataset = json_object(data.get("dataset"), "dataset")
    reject_unknown_fields(
        dataset, {"id", "version", "source", "split", "positions"}, "dataset"
    )
    identity = {
        key: nonempty_string(dataset.get(key), f"dataset.{key}")
        for key in ("id", "version", "source", "split")
    }
    if identity["split"] not in {"development", "validation", "test"}:
        raise ValueError("unsupported dataset split")
    raw_positions = dataset.get("positions")
    if not isinstance(raw_positions, list) or not raw_positions:
        raise ValueError("nonempty positions required")
    positions = []
    for raw in raw_positions:
        position = json_object(raw, "position")
        reject_unknown_fields(position, {"name", "fen", "expected_moves"}, "position")
        expected = position.get("expected_moves")
        if (
            not isinstance(expected, list)
            or not expected
            or any(not isinstance(move, str) for move in expected)
        ):
            raise ValueError("nonempty expected_moves strings required")
        if len(set(expected)) != len(expected):
            raise ValueError("duplicate expected moves")
        p = BenchmarkPosition(
            nonempty_string(position.get("name"), "position.name"),
            nonempty_string(position.get("fen"), "position.fen"),
            tuple(expected),
        )
        positions.append(p)
    keys = [
        " ".join(ChessState.from_fen(p.fen).to_fen().split()[:4]) for p in positions
    ]
    if len(set(keys)) != len(keys) or len({p.name for p in positions}) != len(
        positions
    ):
        raise ValueError("duplicate position identity or name")
    raw_agents = data.get("agents")
    if not isinstance(raw_agents, list) or len(raw_agents) < 2:
        raise ValueError("at least two agents required")
    agents = tuple(match_agent_config_from_dict(raw) for raw in raw_agents)
    if len({a.name for a in agents}) != len(agents):
        raise ValueError("duplicate agent names")
    seeds = data.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(type(s) is not int for s in seeds)
    ):
        raise ValueError("nonempty integer seeds required")
    if len(set(seeds)) != len(seeds):
        raise ValueError("duplicate seeds")
    budget = json_object(data.get("budget"), "budget")
    reject_unknown_fields(budget, {"kind", "value"}, "budget")
    return TacticalComparisonSpec(
        nonempty_string(data.get("name"), "name"),
        nonempty_string(data.get("question"), "question"),
        identity,
        tuple(positions),
        agents,
        tuple(seeds),
        search_budget_from_dict(budget),
    )


@dataclass(frozen=True, slots=True)
class TacticalCase:
    """One scheduled attempt; failed attempts never acquire synthetic labels."""

    index: int
    root_seed: int
    seed: int
    position: str
    agent: str
    action: str | None
    agreement: bool | None
    elapsed_seconds: float | None
    setup_seconds: float
    error: str | None
    phase: str
    diagnostics: dict[str, object]
    engine: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_case(
    index: int,
    root_seed: int,
    seed: int,
    position: BenchmarkPosition,
    config: MatchAgentConfig,
    budget: SearchBudget,
) -> TacticalCase:
    """Prepare outside the decision timer; fresh process/cache for every case."""
    agent = config.build()
    setup_start = perf_counter()
    setup_seconds = 0.0
    elapsed = None
    action = None
    agreement = None
    error_text = None
    phase = "setup"
    diagnostics: dict[str, object] = {}
    engine: dict[str, object] = {}
    try:
        state = ChessState.from_fen(position.fen)
        if isinstance(agent, ExternalUciAgent):
            agent.prepare()
        setup_seconds = perf_counter() - setup_start
        phase = "decision"
        started = perf_counter()
        try:
            decision = agent.select_action(state, budget, random.Random(seed))
        finally:
            elapsed = perf_counter() - started
        if decision.action not in state.legal_actions():
            raise ValueError("agent returned an illegal action")
        action = decision.action.uci()
        agreement = action in position.expected_moves
        if isinstance(decision, SearchResult):
            diagnostics = {
                "nodes": decision.nodes,
                "depth": decision.depth,
                "cutoffs": decision.cutoffs,
                "transposition_hits": decision.transposition_hits,
                "quiescence_nodes": decision.quiescence_nodes,
            }
        phase = "completed"
    except (Exception, KeyboardInterrupt) as error:
        error_text = f"{type(error).__name__}: {error}"
        if phase == "setup":
            setup_seconds = perf_counter() - setup_start
        if isinstance(error, KeyboardInterrupt):
            phase = "interrupted"
    finally:
        if isinstance(agent, ExternalUciAgent):
            agent.close()
            engine = agent.metadata
    return TacticalCase(
        index,
        root_seed,
        seed,
        position.name,
        config.name,
        action,
        agreement,
        elapsed,
        setup_seconds,
        error_text,
        phase,
        diagnostics,
        engine,
    )


def summarize_comparison(
    spec: TacticalComparisonSpec, cases: Sequence[TacticalCase]
) -> dict[str, object]:
    """Keep planned denominators, missing pairs and cleanup failures visible."""
    schedule = spec.schedule()
    seen = set()
    paired: dict[tuple[int, str, str], TacticalCase] = {}
    for case in cases:
        if case.index in seen or not 0 <= case.index < len(schedule):
            raise ValueError("duplicate or unexpected case index")
        root_seed, seed, position, agent = schedule[case.index]
        if (case.root_seed, case.seed, case.position, case.agent) != (
            root_seed,
            seed,
            position.name,
            agent.name,
        ):
            raise ValueError("case inputs differ from schedule")
        if agent.external is not None:
            if case.engine.get("config") != agent.external.to_dict():
                raise ValueError("case engine configuration differs from manifest")
            if (
                "executable_sha256" in case.engine
                and (case.engine["executable_sha256"] != agent.external.sha256)
                and case.error is None
            ):
                raise ValueError("completed case executable hash differs from manifest")
            if case.error is None and (
                not case.engine.get("closed")
                or not case.engine.get("identity")
                or case.engine.get("executable_sha256") != agent.external.sha256
            ):
                raise ValueError("completed external case lacks engine provenance")
        if (
            not math.isfinite(case.setup_seconds)
            or case.setup_seconds < 0
            or (
                case.elapsed_seconds is not None
                and (
                    not math.isfinite(case.elapsed_seconds) or case.elapsed_seconds < 0
                )
            )
        ):
            raise ValueError("invalid case timing")
        if case.error is None:
            if (
                case.phase != "completed"
                or case.elapsed_seconds is None
                or case.action is None
                or chess.Move.from_uci(case.action)
                not in ChessState.from_fen(position.fen).legal_actions()
                or case.agreement is not (case.action in position.expected_moves)
            ):
                raise ValueError("inconsistent completed case")
        elif case.action is not None or case.agreement is not None:
            raise ValueError("failed case cannot contain a successful action")
        seen.add(case.index)
        paired[(root_seed, position.name, agent.name)] = case
    planned = len(spec.seeds) * len(spec.positions)
    rows = []
    for agent in spec.agents:
        attempted = [c for c in cases if c.agent == agent.name]
        completed = [c for c in attempted if c.error is None]
        times = [c.elapsed_seconds for c in completed if c.elapsed_seconds is not None]
        matches = sum(c.agreement is True for c in completed)
        rows.append(
            {
                "agent": agent.name,
                "planned": planned,
                "completed": len(completed),
                "failed": sum(
                    c.error is not None and c.phase != "interrupted" for c in attempted
                ),
                "interrupted": sum(c.phase == "interrupted" for c in attempted),
                "missing": planned - len(attempted),
                "accepted_first_moves": matches,
                "agreement_fraction_planned": matches / planned,
                "agreement_fraction_completed": matches / len(completed)
                if completed
                else None,
                "decision_seconds_median": median(times) if times else None,
                "decision_seconds_total": sum(times),
                "setup_seconds_total": sum(c.setup_seconds for c in attempted),
            }
        )
    contrasts = []
    reference = spec.agents[0].name
    for agent in spec.agents[1:]:
        both = []
        for root_seed in spec.seeds:
            for position in spec.positions:
                a = paired.get((root_seed, position.name, reference))
                b = paired.get((root_seed, position.name, agent.name))
                if (
                    a is not None
                    and b is not None
                    and a.error is None
                    and b.error is None
                ):
                    both.append((a.agreement, b.agreement))
        contrasts.append(
            {
                "reference": reference,
                "candidate": agent.name,
                "complete_pairs": len(both),
                "incomplete_pairs": planned - len(both),
                "candidate_only_agreement": sum(
                    b is True and a is False for a, b in both
                ),
                "reference_only_agreement": sum(
                    a is True and b is False for a, b in both
                ),
            }
        )
    return {
        "manifest_digest": spec.digest,
        "planned": len(schedule),
        "recorded": len(cases),
        "failed": sum(c.error is not None and c.phase != "interrupted" for c in cases),
        "interrupted": sum(c.phase == "interrupted" for c in cases),
        "missing": len(schedule) - len(cases),
        "cleanup_failures": sum(
            c.engine.get("cleanup_error") is not None for c in cases
        ),
        "agents": rows,
        "paired_with_first_agent": contrasts,
    }


def run_comparison(
    spec: TacticalComparisonSpec, output: Path, repository: Path
) -> dict[str, object]:
    """Write incremental raw attempts, snapshots and partial summaries; never retry."""
    output.mkdir(parents=True, exist_ok=False)
    metadata = capture_run_metadata(
        repository, output.name, spec.digest, len(spec.schedule())
    )
    write_artifact_json(output / "manifest.json", spec.to_dict())
    write_artifact_json(output / "metadata.json", metadata)
    (output / "cases").mkdir()
    cases: list[TacticalCase] = []
    try:
        paths = sorted((repository / "src").rglob("*.py"))
        paths += [repository / "pyproject.toml", repository / "uv.lock"]
        hashes = {}
        for path in paths:
            relative = path.relative_to(repository)
            target = output / "source" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            hashes[relative.as_posix()] = file_sha256(target)
        metadata["source_sha256"] = hashes
        for index, (root_seed, seed, position, agent) in enumerate(spec.schedule()):
            metadata["active_case"] = {
                "index": index,
                "root_seed": root_seed,
                "position": position.name,
                "agent": agent.name,
            }
            write_artifact_json(output / "metadata.json", metadata, replace=True)
            case = run_case(index, root_seed, seed, position, agent, spec.budget)
            write_artifact_json(output / "cases" / f"{index:04d}.json", case.to_dict())
            cases.append(case)
            metadata.update(runs_written=len(cases), active_case=None)
            if case.phase == "interrupted":
                raise KeyboardInterrupt("tactical case interrupted; attempt preserved")
        summary = summarize_comparison(spec, cases)
        metadata["status"] = (
            "failed"
            if summary["failed"] or summary["cleanup_failures"]
            else "completed"
        )
    except BaseException as error:
        metadata.update(
            status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
            error=f"{type(error).__name__}: {error}",
        )
        raise
    finally:
        write_artifact_json(output / "summary.json", summarize_comparison(spec, cases))
        write_artifact_json(output / "metadata.json", metadata, replace=True)
    return metadata


def main(argv: Sequence[str] | None = None) -> int:
    """Execute only explicitly supplied positions; never select a held-out split."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        spec = comparison_spec_from_dict(
            json.loads(args.manifest.read_text(encoding="utf-8"))
        )
        metadata = run_comparison(spec, args.output, args.repository)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0 if metadata["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
