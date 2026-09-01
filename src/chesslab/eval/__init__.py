"""Deterministic match execution and evaluation infrastructure."""

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
    "FailureKind",
    "MatchFailure",
    "MatchMetadata",
    "MatchResult",
    "MatchStatus",
    "MoveRecord",
    "run_match",
]
