"""Deterministic match execution and evaluation infrastructure."""

from chesslab.eval.benchmarks import (
    BenchmarkAgentConfig,
    BenchmarkCaseResult,
    BenchmarkPosition,
    BenchmarkProvenance,
    BenchmarkResult,
    BenchmarkSpec,
    capture_provenance,
    run_benchmark,
)
from chesslab.eval.matches import (
    FailureKind,
    MatchFailure,
    MatchMetadata,
    MatchResult,
    MatchStatus,
    MoveRecord,
    run_match,
)

__all__ = [
    "BenchmarkAgentConfig",
    "BenchmarkCaseResult",
    "BenchmarkPosition",
    "BenchmarkProvenance",
    "BenchmarkResult",
    "BenchmarkSpec",
    "FailureKind",
    "MatchFailure",
    "MatchMetadata",
    "MatchResult",
    "MatchStatus",
    "MoveRecord",
    "capture_provenance",
    "run_benchmark",
    "run_match",
]
