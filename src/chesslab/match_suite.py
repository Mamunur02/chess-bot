"""Reproducible chess head-to-head suites with both colour assignments."""

import argparse
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import chess

from chesslab.agents import Agent, RandomAgent
from chesslab.benchmark import (
    benchmark_agent_config_from_dict,
    search_budget_from_dict,
)
from chesslab.config import json_object, nonempty_string, reject_unknown_fields
from chesslab.eval.artifacts import (
    capture_run_metadata,
    configuration_digest,
    write_artifact_json,
)
from chesslab.eval.benchmarks import (
    BenchmarkAgentConfig,
    BenchmarkPosition,
    budget_to_dict,
)
from chesslab.eval.matches import MatchResult, MatchStatus, run_match
from chesslab.games import GameState
from chesslab.games.chess import ChessState
from chesslab.search import SearchBudget


@dataclass(frozen=True, slots=True)
class MatchAgentConfig:
    """One named random or material agent, built fresh for each game.

    ``search=None`` selects the random agent. A material configuration selects
    greedy or alpha-beta using its existing validation and switches.
    """

    name: str
    search: BenchmarkAgentConfig | None = None

    def build(self) -> Agent[GameState[chess.Move], chess.Move]:
        return RandomAgent[chess.Move]() if self.search is None else self.search.build()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "agent": (
                {"kind": "random"} if self.search is None else self.search.to_dict()
            ),
        }


@dataclass(frozen=True, slots=True)
class MatchSuiteSpec:
    """Validated common inputs for exactly two agents and paired games.

    Construct using ``match_suite_spec_from_dict``. Position seeds are derived
    separately for each root seed. Both colour assignments share the derived
    match seed; the existing match runner assigns independent RNGs by colour.
    """

    name: str
    question: str
    dataset_id: str
    dataset_version: str
    dataset_source: str
    dataset_split: str
    positions: tuple[BenchmarkPosition, ...]
    agents: tuple[MatchAgentConfig, MatchAgentConfig]
    seeds: tuple[int, ...]
    budget: SearchBudget
    max_plies: int

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "name": self.name,
            "question": self.question,
            "dataset": {
                "id": self.dataset_id,
                "version": self.dataset_version,
                "source": self.dataset_source,
                "split": self.dataset_split,
                "positions": [{"name": p.name, "fen": p.fen} for p in self.positions],
            },
            "agents": [a.to_dict() for a in self.agents],
            "seeds": list(self.seeds),
            "budget": budget_to_dict(self.budget),
            "max_plies": self.max_plies,
        }

    @property
    def digest(self) -> str:
        """Hash the normalized suite, including all starting positions."""
        return configuration_digest(self.to_dict())

    @property
    def games_planned(self) -> int:
        return 2 * len(self.seeds) * len(self.positions)


def match_suite_spec_from_dict(value: object) -> MatchSuiteSpec:
    """Parse a strict shared-budget manifest without selecting research data."""
    data = json_object(value, "match suite")
    reject_unknown_fields(
        data,
        {
            "schema_version",
            "name",
            "question",
            "dataset",
            "agents",
            "seeds",
            "budget",
            "max_plies",
        },
        "suite",
    )
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    name = nonempty_string(data.get("name"), "name")
    question = nonempty_string(data.get("question"), "question")
    max_plies = data.get("max_plies")
    if type(max_plies) is not int or max_plies <= 0:
        raise ValueError("max_plies must be a positive integer")
    seeds = data.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(type(s) is not int for s in seeds)
    ):
        raise ValueError("seeds must be a non-empty array of integers")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    raw_budget = json_object(data.get("budget"), "budget")
    reject_unknown_fields(raw_budget, {"kind", "value"}, "budget")
    budget = search_budget_from_dict(raw_budget)
    dataset = json_object(data.get("dataset"), "dataset")
    reject_unknown_fields(
        dataset, {"id", "version", "source", "split", "positions"}, "dataset"
    )
    dataset_id = nonempty_string(dataset.get("id"), "dataset.id")
    dataset_version = nonempty_string(dataset.get("version"), "dataset.version")
    source = nonempty_string(dataset.get("source"), "dataset.source")
    split = nonempty_string(dataset.get("split"), "dataset.split")
    if split not in {"development", "validation", "test"}:
        raise ValueError("dataset.split must be development, validation, or test")
    raw_positions = dataset.get("positions")
    if not isinstance(raw_positions, list) or not raw_positions:
        raise ValueError("dataset.positions must be a non-empty array")
    positions: list[BenchmarkPosition] = []
    for item in raw_positions:
        position = json_object(item, "position")
        reject_unknown_fields(position, {"name", "fen"}, "position")
        p = BenchmarkPosition(
            nonempty_string(position.get("name"), "position.name"),
            nonempty_string(position.get("fen"), "position.fen"),
        )
        state = ChessState.from_fen(p.fen)
        if state.is_terminal():
            raise ValueError("match suite starting positions must be non-terminal")
        positions.append(p)
    names = [p.name for p in positions]
    identities = [
        " ".join(ChessState.from_fen(p.fen).to_fen().split()[:5]) for p in positions
    ]
    if len(set(names)) != len(names) or len(set(identities)) != len(identities):
        raise ValueError("position names and FEN positions must be unique")
    raw_agents = data.get("agents")
    if not isinstance(raw_agents, list) or len(raw_agents) != 2:
        raise ValueError("exactly two named agents are required")
    agents: list[MatchAgentConfig] = []
    for item in raw_agents:
        entry = json_object(item, "named agent")
        reject_unknown_fields(entry, {"name", "agent"}, "named agent")
        agent_name = nonempty_string(entry.get("name"), "agent.name")
        settings = json_object(entry.get("agent"), "agent")
        if settings.get("kind") == "random":
            reject_unknown_fields(settings, {"kind"}, "random agent")
            search = None
        else:
            reject_unknown_fields(
                settings,
                {"kind", "capture_ordering", "transposition_table", "quiescence_depth"},
                "material agent",
            )
            search = benchmark_agent_config_from_dict(settings)
        agents.append(MatchAgentConfig(agent_name, search))
    if agents[0].name == agents[1].name:
        raise ValueError("agent names must be unique")
    return MatchSuiteSpec(
        name,
        question,
        dataset_id,
        dataset_version,
        source,
        split,
        tuple(positions),
        (agents[0], agents[1]),
        tuple(seeds),
        budget,
        max_plies,
    )


@dataclass(frozen=True, slots=True)
class SuiteGame:
    """One raw match plus its pairing and agent-colour mapping."""

    pair_index: int
    root_seed: int
    position_name: str
    initial_fen: str
    white_agent: str
    black_agent: str
    result: MatchResult

    def to_dict(self) -> dict[str, object]:
        return {
            "pair_index": self.pair_index,
            "root_seed": self.root_seed,
            "position_name": self.position_name,
            "initial_fen": self.initial_fen,
            "white_agent": self.white_agent,
            "black_agent": self.black_agent,
            "result": self.result.to_dict(),
        }


def summarize_match_suite(
    spec: MatchSuiteSpec,
    games: Sequence[SuiteGame],
) -> dict[str, object]:
    """Report actual outcomes only; ply limits and errors are never draws.

    Score fraction is (wins + draws/2) / completed games for each agent. It is
    descriptive and conditioned on completion, so missing outcomes remain
    visible. This function does not infer Elo or independent sample size.
    """
    seen: set[tuple[int, str]] = set()
    expected_seeds: dict[int, int] = {}
    for root_index, root_seed in enumerate(spec.seeds):
        rng = random.Random(root_seed)
        for position_index in range(len(spec.positions)):
            expected_seeds[root_index * len(spec.positions) + position_index] = (
                rng.getrandbits(128)
            )
    agent_names = {agent.name for agent in spec.agents}
    budget = budget_to_dict(spec.budget)
    for game in games:
        key = (game.pair_index, game.white_agent)
        if key in seen or game.pair_index not in expected_seeds:
            raise ValueError("duplicate or unexpected suite game")
        root_index, position_index = divmod(game.pair_index, len(spec.positions))
        position = spec.positions[position_index]
        if (
            {game.white_agent, game.black_agent} != agent_names
            or game.root_seed != spec.seeds[root_index]
            or game.position_name != position.name
            or game.initial_fen != position.fen
            or game.result.metadata.root_seed != expected_seeds[game.pair_index]
            or game.result.metadata.max_plies != spec.max_plies
            or game.result.metadata.budget_kind != budget["kind"]
            or game.result.metadata.budget_value != budget["value"]
        ):
            raise ValueError("game inputs do not match suite manifest")
        seen.add(key)
    completed = [g for g in games if g.result.status is MatchStatus.COMPLETED]
    rows: list[dict[str, object]] = []
    for agent in spec.agents:
        wins = draws = losses = 0
        for game in completed:
            returns = game.result.terminal_returns
            assert returns is not None
            value = returns[0 if game.white_agent == agent.name else 1]
            wins += value > 0
            draws += value == 0
            losses += value < 0
        rows.append(
            {
                "agent": agent.name,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "score_fraction_completed": (wins + draws / 2) / len(completed)
                if completed
                else None,
            }
        )
    by_pair: dict[int, list[SuiteGame]] = {}
    for game in games:
        by_pair.setdefault(game.pair_index, []).append(game)
    complete_pairs = sum(
        len(pair) == 2 and all(g.result.status is MatchStatus.COMPLETED for g in pair)
        for pair in by_pair.values()
    )
    return {
        "manifest_digest": spec.digest,
        "games_planned": spec.games_planned,
        "games_recorded": len(games),
        "completed": len(completed),
        "interrupted": sum(g.result.status is MatchStatus.INTERRUPTED for g in games),
        "failed": sum(g.result.status is MatchStatus.FAILED for g in games),
        "unrecorded": spec.games_planned - len(games),
        "pairs_planned": spec.games_planned // 2,
        "pairs_completed": complete_pairs,
        "pairs_without_two_completed_games": spec.games_planned // 2 - complete_pairs,
        "total_plies": sum(g.result.plies for g in games),
        "agents": rows,
    }


def run_match_suite(
    spec: MatchSuiteSpec,
    output: Path,
    repository: Path,
) -> dict[str, object]:
    """Execute each seed-position pair in both colours and preserve raw games."""
    output.mkdir(parents=True, exist_ok=False)
    metadata = capture_run_metadata(
        repository, output.name, spec.digest, spec.games_planned
    )
    write_artifact_json(output / "manifest.json", spec.to_dict())
    write_artifact_json(output / "metadata.json", metadata)
    (output / "games").mkdir()
    games: list[SuiteGame] = []
    pair_index = 0
    try:
        for root_seed in spec.seeds:
            rng = random.Random(root_seed)
            for position in spec.positions:
                match_seed = rng.getrandbits(128)
                for white_index in (0, 1):
                    white = spec.agents[white_index]
                    black = spec.agents[1 - white_index]
                    metadata["active_game"] = {
                        "pair_index": pair_index,
                        "root_seed": root_seed,
                        "match_seed": match_seed,
                        "position_name": position.name,
                        "white_agent": white.name,
                        "black_agent": black.name,
                    }
                    write_artifact_json(
                        output / "metadata.json", metadata, replace=True
                    )
                    result = run_match(
                        ChessState.from_fen(position.fen),
                        (white.build(), black.build()),
                        spec.budget,
                        seed=match_seed,
                        max_plies=spec.max_plies,
                        encode_action=lambda move: move.uci(),
                    )
                    game = SuiteGame(
                        pair_index,
                        root_seed,
                        position.name,
                        position.fen,
                        white.name,
                        black.name,
                        result,
                    )
                    write_artifact_json(
                        output / "games" / f"{len(games):04d}.json", game.to_dict()
                    )
                    games.append(game)
                    metadata["active_game"] = None
                    metadata["runs_written"] = len(games)
                    write_artifact_json(
                        output / "metadata.json", metadata, replace=True
                    )
                pair_index += 1
        metadata["status"] = (
            "failed"
            if any(g.result.status is MatchStatus.FAILED for g in games)
            else "interrupted"
            if any(g.result.status is MatchStatus.INTERRUPTED for g in games)
            else "completed"
        )
    except KeyboardInterrupt:
        metadata["status"] = "interrupted"
        metadata["error"] = "KeyboardInterrupt: suite execution interrupted"
        raise
    except Exception as error:
        metadata["status"] = "failed"
        metadata["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        write_artifact_json(output / "summary.json", summarize_match_suite(spec, games))
        write_artifact_json(output / "metadata.json", metadata, replace=True)
    return metadata


def main(argv: Sequence[str] | None = None) -> int:
    """Run a match suite; incomplete games return 1, keyboard interruption 130."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path, help="fresh artifact directory")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        spec = match_suite_spec_from_dict(
            json.loads(args.manifest.read_text(encoding="utf-8"))
        )
        metadata = run_match_suite(spec, args.output, args.repository)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0 if metadata["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
