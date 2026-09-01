"""Transparent material-only chess evaluation."""

from collections.abc import Mapping
from types import MappingProxyType

import chess

from chesslab.games import Player
from chesslab.games.chess import ChessState

PIECE_VALUES: Mapping[chess.PieceType, int] = MappingProxyType(
    {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }
)


def material_score(state: ChessState, perspective: Player) -> int:
    """Return material balance in centipawns for a stable player identity."""
    white_minus_black = sum(
        PIECE_VALUES[piece.piece_type]
        * (1 if piece.color == chess.WHITE else -1)
        for piece in state.piece_map().values()
    )
    return white_minus_black if perspective == 0 else -white_minus_black
