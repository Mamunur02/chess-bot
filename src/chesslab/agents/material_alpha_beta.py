"""A deterministic iterative-deepening agent using material evaluation."""

import random
from collections.abc import Sequence
from dataclasses import dataclass

import chess

from chesslab.engine.evaluation import material_score
from chesslab.games import GameState, Player
from chesslab.games.chess import ChessState
from chesslab.search import SearchBudget
from chesslab.search.classical import iterative_deepening_search
from chesslab.search.results import SearchResult


def _evaluate_chess_state(state: GameState[chess.Move], perspective: Player) -> int:
    if not isinstance(state, ChessState):
        raise TypeError("MaterialAlphaBetaAgent requires ChessState")
    return material_score(state, perspective)


def _capture_first(
    state: GameState[chess.Move], actions: Sequence[chess.Move]
) -> tuple[chess.Move, ...]:
    if not isinstance(state, ChessState):
        raise TypeError("capture ordering requires ChessState")
    return tuple(sorted(actions, key=state.is_capture, reverse=True))


@dataclass(frozen=True, slots=True)
class MaterialAlphaBetaAgent:
    """Select chess moves with iterative material alpha-beta search."""

    capture_ordering: bool = False

    def select_action(
        self,
        state: GameState[chess.Move],
        budget: SearchBudget,
        rng: random.Random,
    ) -> SearchResult[chess.Move]:
        """Search deterministically using a depth or node budget."""
        del rng
        if not isinstance(state, ChessState):
            raise TypeError("MaterialAlphaBetaAgent requires ChessState")
        return iterative_deepening_search(
            state,
            budget,
            _evaluate_chess_state,
            action_orderer=_capture_first if self.capture_ordering else None,
        )
