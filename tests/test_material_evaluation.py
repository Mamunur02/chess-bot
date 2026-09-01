from types import MappingProxyType

import chess
import pytest

from chesslab.engine.evaluation import material_score
from chesslab.games.chess import ChessState

QUEEN_ADVANTAGE_FEN = "7k/8/8/8/8/8/8/KQ6 w - - 0 1"


def test_initial_position_has_equal_material() -> None:
    state = ChessState()

    assert material_score(state, 0) == 0
    assert material_score(state, 1) == 0


def test_material_score_uses_stable_player_perspective() -> None:
    state = ChessState.from_fen(QUEEN_ADVANTAGE_FEN)

    assert material_score(state, 0) == 900
    assert material_score(state, 1) == -900


def test_piece_map_is_an_immutable_snapshot() -> None:
    state = ChessState()
    pieces = state.piece_map()

    assert isinstance(pieces, MappingProxyType)
    with pytest.raises(TypeError):
        pieces[chess.E4] = chess.Piece(chess.QUEEN, chess.WHITE)  # type: ignore[index]

    child = state.apply(chess.Move.from_uci("e2e4"))
    assert pieces[chess.E2] == chess.Piece(chess.PAWN, chess.WHITE)
    assert chess.E4 not in pieces
    assert child.piece_map()[chess.E4] == chess.Piece(chess.PAWN, chess.WHITE)
