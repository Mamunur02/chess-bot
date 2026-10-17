"""Plain alpha-beta with our fitted linear evaluator and pinned JSON weights."""

import random
from dataclasses import dataclass
from pathlib import Path

import chess

from chesslab.config import json_object, nonempty_string, reject_unknown_fields
from chesslab.engine.evaluation.linear import LinearEvaluator
from chesslab.games import GameState, Player
from chesslab.games.chess import ChessState
from chesslab.search import SearchBudget
from chesslab.search.classical import iterative_deepening_search
from chesslab.search.results import SearchResult


@dataclass(frozen=True, slots=True)
class LinearAlphaBetaAgent:
    """Use identical plain search and terminal utility with a learned heuristic."""

    model: LinearEvaluator

    def _evaluate(self, state: GameState[chess.Move], perspective: Player) -> int:
        if not isinstance(state, ChessState):
            raise TypeError("LinearAlphaBetaAgent requires ChessState")
        return self.model.evaluate(state, perspective)

    def select_action(
        self, state: GameState[chess.Move], budget: SearchBudget, rng: random.Random
    ) -> SearchResult[chess.Move]:
        del rng
        if not isinstance(state, ChessState):
            raise TypeError("LinearAlphaBetaAgent requires ChessState")
        return iterative_deepening_search(state, budget, self._evaluate)


@dataclass(frozen=True, slots=True)
class LinearAgentConfig:
    """A model path/hash; plain search has no hidden tuning switches."""

    path: str
    sha256: str

    @classmethod
    def from_dict(cls, value: object) -> "LinearAgentConfig":
        data = json_object(value, "linear agent")
        reject_unknown_fields(data, {"kind", "path", "sha256"}, "linear agent")
        path = nonempty_string(data.get("path"), "model path")
        digest = nonempty_string(data.get("sha256"), "model sha256").lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("model sha256 must contain 64 hexadecimal characters")
        return cls(path, digest)

    def to_dict(self) -> dict[str, object]:
        return {"kind": "linear_alpha_beta", "path": self.path, "sha256": self.sha256}

    def build(self) -> LinearAlphaBetaAgent:
        return LinearAlphaBetaAgent(LinearEvaluator.load(Path(self.path), self.sha256))
