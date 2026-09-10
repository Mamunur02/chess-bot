"""A deterministic iterative-deepening agent using material evaluation."""

import random
from collections.abc import Sequence
from dataclasses import dataclass

import chess

from chesslab.engine.evaluation import material_score
from chesslab.games import GameState, Player
from chesslab.games.chess import ChessState, ChessTranspositionKey
from chesslab.search import SearchBudget
from chesslab.search.classical import QuiescenceExpansion, iterative_deepening_search
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


def _transposition_key(state: GameState[chess.Move]) -> ChessTranspositionKey:
    if not isinstance(state, ChessState):
        raise TypeError("chess transposition key requires ChessState")
    return state.transposition_key()


def _quiescence_expansion(
    state: GameState[chess.Move],
) -> QuiescenceExpansion[chess.Move]:
    if not isinstance(state, ChessState):
        raise TypeError("chess quiescence search requires ChessState")
    legal_actions = state.legal_actions()
    if state.is_in_check():
        return QuiescenceExpansion(legal_actions, allow_stand_pat=False)
    tactical_actions = tuple(
        action
        for action in legal_actions
        if state.is_capture(action) or action.promotion is not None
    )
    return QuiescenceExpansion(tactical_actions, allow_stand_pat=True)


@dataclass(frozen=True, slots=True)
class MaterialAlphaBetaAgent:
    """Select chess moves with iterative material alpha-beta search."""

    capture_ordering: bool = False
    transposition_table: bool = False
    quiescence_depth: int = 0

    def __post_init__(self) -> None:
        """Validate the optional bounded quiescence depth."""
        if isinstance(self.quiescence_depth, bool) or self.quiescence_depth < 0:
            raise ValueError("quiescence depth must be a non-negative integer")

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
            transposition_key=(
                _transposition_key if self.transposition_table else None
            ),
            quiescence_selector=(
                _quiescence_expansion if self.quiescence_depth > 0 else None
            ),
            quiescence_depth=self.quiescence_depth,
        )
