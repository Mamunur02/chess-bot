"""Fixed-budget chess benchmark execution and reproducibility metadata."""

import hashlib
import json
import platform
import random
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal

import chess

from chesslab.agents.material_alpha_beta import MaterialAlphaBetaAgent
from chesslab.games.chess import ChessState
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget
from chesslab.search.results import SearchResult

type CaseStatus = Literal["completed", "failed"]


@dataclass(frozen=True, slots=True)
class BenchmarkPosition:
    """One immutable benchmark input with optional accepted root moves."""

    name: str
    fen: str
    expected_moves: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("benchmark position name must not be empty")
        state = ChessState.from_fen(self.fen)
        legal_actions = set(state.legal_actions())
        for move_text in self.expected_moves:
            try:
                move = chess.Move.from_uci(move_text)
            except ValueError as error:
                raise ValueError(f"invalid expected UCI move: {move_text}") from error
            if move not in legal_actions:
                raise ValueError(f"expected move is not legal: {move_text}")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "fen": self.fen,
            "expected_moves": list(self.expected_moves),
        }


@dataclass(frozen=True, slots=True)
class BenchmarkAgentConfig:
    """Explicit switches for the material alpha-beta baseline."""

    capture_ordering: bool = False
    transposition_table: bool = False
    quiescence_depth: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.capture_ordering, bool):
            raise ValueError("capture_ordering must be a boolean")
        if not isinstance(self.transposition_table, bool):
            raise ValueError("transposition_table must be a boolean")
        MaterialAlphaBetaAgent(
            capture_ordering=self.capture_ordering,
            transposition_table=self.transposition_table,
            quiescence_depth=self.quiescence_depth,
        )

    def build(self) -> MaterialAlphaBetaAgent:
        return MaterialAlphaBetaAgent(
            capture_ordering=self.capture_ordering,
            transposition_table=self.transposition_table,
            quiescence_depth=self.quiescence_depth,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "capture_ordering": self.capture_ordering,
            "transposition_table": self.transposition_table,
            "quiescence_depth": self.quiescence_depth,
        }


def _budget_dict(budget: SearchBudget) -> dict[str, object]:
    if isinstance(budget, DepthBudget):
        return {"kind": "depth", "value": budget.depth}
    if isinstance(budget, NodeBudget):
        return {"kind": "nodes", "value": budget.nodes}
    if isinstance(budget, TimeBudget):
        return {"kind": "milliseconds", "value": budget.milliseconds}
    raise ValueError(f"unsupported search budget: {type(budget).__name__}")


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    """Complete caller-selected inputs for one benchmark run."""

    name: str
    seed: int
    budget: SearchBudget
    agent: BenchmarkAgentConfig
    positions: tuple[BenchmarkPosition, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("benchmark name must not be empty")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("benchmark seed must be an integer")
        if not self.positions:
            raise ValueError("benchmark requires at least one position")
        names = [position.name for position in self.positions]
        if len(names) != len(set(names)):
            raise ValueError("benchmark position names must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "seed": self.seed,
            "budget": _budget_dict(self.budget),
            "agent": self.agent.to_dict(),
            "positions": [position.to_dict() for position in self.positions],
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class BenchmarkProvenance:
    """Environment and repository state captured before a run."""

    started_at: str
    git_commit: str | None
    git_dirty: bool | None
    git_error: str | None
    python_version: str
    platform: str
    machine: str
    processor: str
    config_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "started_at": self.started_at,
            "git_commit": self.git_commit,
            "git_dirty": self.git_dirty,
            "git_error": self.git_error,
            "python_version": self.python_version,
            "platform": self.platform,
            "machine": self.machine,
            "processor": self.processor,
            "config_digest": self.config_digest,
        }


def capture_provenance(
    repository: Path,
    config_digest: str,
    *,
    now: Callable[[], datetime] | None = None,
) -> BenchmarkProvenance:
    """Capture Git and runtime metadata without failing outside a repository."""
    resolved_repository = repository.resolve()
    git_prefix = [
        "git",
        "-c",
        f"safe.directory={resolved_repository.as_posix()}",
    ]
    git_commit: str | None = None
    git_dirty: bool | None = None
    git_error: str | None = None
    try:
        commit_result = subprocess.run(
            [*git_prefix, "rev-parse", "HEAD"],
            cwd=resolved_repository,
            check=True,
            capture_output=True,
            text=True,
        )
        status_result = subprocess.run(
            [*git_prefix, "status", "--porcelain"],
            cwd=resolved_repository,
            check=True,
            capture_output=True,
            text=True,
        )
        git_commit = commit_result.stdout.strip()
        git_dirty = bool(status_result.stdout)
    except (OSError, subprocess.CalledProcessError) as error:
        git_error = f"{type(error).__name__}: {error}"

    current_time = now() if now is not None else datetime.now(UTC)
    return BenchmarkProvenance(
        started_at=current_time.astimezone(UTC).isoformat(),
        git_commit=git_commit,
        git_dirty=git_dirty,
        git_error=git_error,
        python_version=platform.python_version(),
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        config_digest=config_digest,
    )


@dataclass(frozen=True, slots=True)
class BenchmarkCaseResult:
    """One completed or failed position evaluation."""

    name: str
    fen: str
    seed: int
    status: CaseStatus
    elapsed_seconds: float
    decision: SearchResult[chess.Move] | None
    expected_move_match: bool | None
    error: str | None

    def to_dict(self) -> dict[str, object]:
        decision: dict[str, object] | None = None
        if self.decision is not None:
            decision = {
                "action": self.decision.action.uci(),
                "value": self.decision.value,
                "nodes": self.decision.nodes,
                "depth": self.decision.depth,
                "principal_variation": [
                    move.uci() for move in self.decision.principal_variation
                ],
                "cutoffs": self.decision.cutoffs,
                "iterations": self.decision.iterations,
                "transposition_hits": self.decision.transposition_hits,
                "quiescence_nodes": self.decision.quiescence_nodes,
                "search_elapsed_seconds": self.decision.elapsed_seconds,
            }
        return {
            "name": self.name,
            "fen": self.fen,
            "seed": self.seed,
            "status": self.status,
            "elapsed_seconds": self.elapsed_seconds,
            "decision": decision,
            "expected_move_match": self.expected_move_match,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """A benchmark run containing raw cases and exact aggregate counts."""

    spec: BenchmarkSpec
    provenance: BenchmarkProvenance
    cases: tuple[BenchmarkCaseResult, ...]
    elapsed_seconds: float

    def to_dict(self) -> dict[str, object]:
        completed = sum(case.status == "completed" for case in self.cases)
        expected_cases = [
            case for case in self.cases if case.expected_move_match is not None
        ]
        return {
            "spec": self.spec.to_dict(),
            "provenance": self.provenance.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
            "summary": {
                "positions": len(self.cases),
                "completed": completed,
                "failed": len(self.cases) - completed,
                "expected_move_cases": len(expected_cases),
                "expected_move_matches": sum(
                    case.expected_move_match is True for case in expected_cases
                ),
                "total_nodes": sum(
                    case.decision.nodes
                    for case in self.cases
                    if case.decision is not None
                ),
                "elapsed_seconds": self.elapsed_seconds,
            },
        }


def run_benchmark(
    spec: BenchmarkSpec,
    provenance: BenchmarkProvenance,
    *,
    clock: Callable[[], float] = perf_counter,
) -> BenchmarkResult:
    """Run each position once with derived seeds and structured failures."""
    if provenance.config_digest != spec.digest:
        raise ValueError("provenance config digest does not match benchmark spec")
    seed_source = random.Random(spec.seed)
    agent = spec.agent.build()
    run_started = clock()
    cases: list[BenchmarkCaseResult] = []
    for position in spec.positions:
        case_seed = seed_source.getrandbits(128)
        case_started = clock()
        try:
            state = ChessState.from_fen(position.fen)
            decision = agent.select_action(state, spec.budget, random.Random(case_seed))
            match = (
                decision.action.uci() in position.expected_moves
                if position.expected_moves
                else None
            )
            error = None
            status: CaseStatus = "completed"
        except Exception as caught:
            decision = None
            match = None
            error = f"{type(caught).__name__}: {caught}"
            status = "failed"
        cases.append(
            BenchmarkCaseResult(
                name=position.name,
                fen=position.fen,
                seed=case_seed,
                status=status,
                elapsed_seconds=max(0.0, clock() - case_started),
                decision=decision,
                expected_move_match=match,
                error=error,
            )
        )
    return BenchmarkResult(
        spec=spec,
        provenance=provenance,
        cases=tuple(cases),
        elapsed_seconds=max(0.0, clock() - run_started),
    )
