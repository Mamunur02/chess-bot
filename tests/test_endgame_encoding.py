"""Tests for protocol-v1 board feature encoding."""

import chess

from chesslab.endgames.encoding import INPUT_SIZE, encode_board


def test_piece_planes_follow_color_type_and_a1_to_h8_order() -> None:
    board = chess.Board("7k/8/8/8/8/8/P7/KR6 w - - 0 1")
    encoded = encode_board(board, chess.WHITE)
    assert len(encoded) == INPUT_SIZE
    assert encoded[0 * 64 + chess.A2] == 1.0  # white pawn
    assert encoded[3 * 64 + chess.B1] == 1.0  # white rook
    assert encoded[5 * 64 + chess.A1] == 1.0  # white king
    assert encoded[11 * 64 + chess.H8] == 1.0  # black king
    assert sum(encoded[:768]) == 4.0


def test_all_twelve_starting_position_planes_have_exact_indices() -> None:
    encoded = encode_board(chess.Board(), chess.WHITE)
    occupied_indices = (
        *range(8, 16), 65, 70, 130, 133, 192, 199, 259, 324,
        *range(432, 440), 505, 510, 570, 573, 632, 639, 699, 764,
    )
    assert all(encoded[index] == 1.0 for index in occupied_indices)
    assert sum(encoded[:768]) == 32.0


def test_perspective_clock_and_learner_features() -> None:
    board = chess.Board()
    encoded = encode_board(board, chess.WHITE)
    assert encoded[768:771] == (1.0, 1.0, 0.0)
    board.push_uci("e2e4")
    encoded_black_learner = encode_board(board, chess.BLACK)
    assert encoded_black_learner[768:771] == (0.0, 0.0, 0.0)
    encoded_white_learner = encode_board(board, chess.WHITE)
    assert encoded_white_learner[769] == 1.0


def test_halfmove_clock_is_normalized_and_clamped() -> None:
    board = chess.Board()
    board.halfmove_clock = 99
    assert encode_board(board, chess.WHITE)[770] == 0.99
    board.halfmove_clock = 150
    assert encode_board(board, chess.WHITE)[770] == 1.0


def test_repetition_count_and_prospective_claim_flags_are_distinct() -> None:
    board = chess.Board()
    for uci in ("g1f3", "g8f6", "f3g1", "f6g8"):
        board.push_uci(uci)
    twofold = encode_board(board, chess.WHITE)
    assert twofold[771:775] == (1.0, 0.0, 0.0, 0.0)

    prospective = chess.Board()
    for uci in (
        "g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1"
    ):
        prospective.push_uci(uci)
    claimable = encode_board(prospective, chess.WHITE)
    assert claimable[771:775] == (1.0, 0.0, 0.0, 1.0)

    threefold = chess.Board()
    for uci in (
        "g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"
    ):
        threefold.push_uci(uci)
    current_claim = encode_board(threefold, chess.WHITE)
    assert current_claim[771:775] == (1.0, 1.0, 0.0, 1.0)


def test_fifty_move_flag_includes_prospective_claim() -> None:
    board = chess.Board()
    board.halfmove_clock = 99
    encoded = encode_board(board, chess.WHITE)
    assert encoded[770] == 0.99
    assert encoded[773] == 1.0


def test_terminal_positions_are_encodable() -> None:
    checkmate = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    assert checkmate.is_checkmate()
    encoded = encode_board(checkmate, chess.WHITE)
    assert len(encoded) == INPUT_SIZE
    assert encoded[768] == 0.0


def test_encoding_does_not_mutate_board_or_history() -> None:
    board = chess.Board()
    board.push_uci("g1f3")
    fen = board.fen()
    stack = tuple(board.move_stack)
    encoded = encode_board(board, chess.BLACK)
    assert len(encoded) == INPUT_SIZE
    assert board.fen() == fen
    assert tuple(board.move_stack) == stack
