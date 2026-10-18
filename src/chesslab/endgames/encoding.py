"""Protocol-v1 neural input encoding for history-aware chess positions."""

import chess

INPUT_SIZE = 775
PIECE_PLANE_COUNT = 12
SQUARES_PER_PLANE = 64


def encode_board(board: chess.Board, learner: chess.Color) -> tuple[float, ...]:
    """Encode pieces, perspective, clock and draw-history flags.

    Piece planes use white then black, each in pawn, knight, bishop, rook,
    queen, king order. Within a plane, square zero through 63 is a1 through h8.
    History-dependent features are evaluated on a stack-preserving copy so the
    supplied board and its move history remain unchanged.
    """
    features = [0.0] * INPUT_SIZE
    piece_types = (
        chess.PAWN,
        chess.KNIGHT,
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN,
        chess.KING,
    )
    for color_index, color in enumerate((chess.WHITE, chess.BLACK)):
        for piece_index, piece_type in enumerate(piece_types):
            plane_offset = (
                color_index * 6 + piece_index
            ) * SQUARES_PER_PLANE
            for square in board.pieces(piece_type, color):
                features[plane_offset + square] = 1.0

    features[768] = float(board.turn == chess.WHITE)
    features[769] = float(learner == chess.WHITE)
    features[770] = min(board.halfmove_clock, 100) / 100.0

    history = board.copy(stack=True)
    features[771] = float(history.is_repetition(2))
    features[772] = float(history.is_repetition(3))
    features[773] = float(history.can_claim_fifty_moves())
    features[774] = float(history.can_claim_threefold_repetition())
    return tuple(features)
