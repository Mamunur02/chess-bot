"""A deterministic fixed-depth chess agent using material evaluation."""

import random

import chess

from chesslab.engine.evaluation import material_score
from chesslab.games import GameState, Player
from chesslab.games.chess import ChessState
from chesslab.search import DepthBudget, SearchBudget
from chesslab.search.classical import alpha_beta_search
from chesslab.search.results import SearchResult


def _evaluate_chess_state(
    state: GameState[chess.Move], perspective: Player
) -> int:
    if not isinstance(state, ChessState):
        raise TypeError("MaterialAlphaBetaAgent requires ChessState")
    return material_score(state, perspective)


class MaterialAlphaBetaAgent:
    """Select chess moves with fixed-depth material alpha-beta search."""

    def select_action(
        self,
        state: GameState[chess.Move],
        budget: SearchBudget,
        rng: random.Random,
    ) -> SearchResult[chess.Move]:
        """Search deterministically using the supplied depth budget."""
        del rng
        if not isinstance(state, ChessState):
            raise TypeError("MaterialAlphaBetaAgent requires ChessState")
        if not isinstance(budget, DepthBudget):
            raise ValueError("MaterialAlphaBetaAgent requires a DepthBudget")
        return alpha_beta_search(state, budget.depth, _evaluate_chess_state)
