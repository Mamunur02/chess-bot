"""Deterministic one-ply material-greedy chess baseline."""

import random
from dataclasses import dataclass

import chess

from chesslab.engine.evaluation import material_score
from chesslab.games import GameState, Player
from chesslab.games.chess import ChessState
from chesslab.search import SearchBudget
from chesslab.search.classical import alpha_beta_search
from chesslab.search.results import SearchResult


def _evaluate_chess_state(state: GameState[chess.Move], perspective: Player) -> int:
    if not isinstance(state, ChessState):
        raise TypeError("MaterialGreedyAgent requires ChessState")
    return material_score(state, perspective)


@dataclass(frozen=True, slots=True)
class MaterialGreedyAgent:
    """Choose the best immediate material or terminal outcome."""

    def select_action(
        self,
        state: GameState[chess.Move],
        budget: SearchBudget,
        rng: random.Random,
    ) -> SearchResult[chess.Move]:
        """Evaluate every legal child once in stable legal-action order."""
        del budget, rng
        if not isinstance(state, ChessState):
            raise TypeError("MaterialGreedyAgent requires ChessState")
        return alpha_beta_search(
            state,
            1,
            _evaluate_chess_state,
        )
