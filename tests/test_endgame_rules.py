"""History-aware endgame rule adapter tests."""

import chess
import pytest

from chesslab.endgames.rules import child_board, terminal_reward


def test_rewards_are_from_fixed_learner_perspective() -> None:
    board = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    assert terminal_reward(board, chess.WHITE) == 1.0
    assert terminal_reward(board, chess.BLACK) == -1.0


def test_draw_and_nonterminal_rewards() -> None:
    draw = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert terminal_reward(draw, chess.WHITE) == 0.0
    assert terminal_reward(chess.Board(), chess.WHITE) is None


def test_fifty_move_and_prospective_repetition_claims_are_terminal() -> None:
    fifty_move = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 100 1")
    assert terminal_reward(fifty_move, chess.WHITE) == 0.0

    board = chess.Board()
    for san in ("Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1"):
        board.push_san(san)
    assert board.can_claim_threefold_repetition()
    assert terminal_reward(board, chess.WHITE) == 0.0
    with pytest.raises(ValueError, match="terminal"):
        child_board(board, chess.Move.from_uci("f6g8"))


def test_child_keeps_history_and_does_not_mutate_parent() -> None:
    board = chess.Board()
    board.push_san("Nf3")
    move = chess.Move.from_uci("g8f6")
    child = child_board(board, move)
    assert len(child.move_stack) == 2
    assert len(board.move_stack) == 1


def test_child_rejects_terminal_and_illegal_moves() -> None:
    terminal = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    with pytest.raises(ValueError, match="terminal"):
        child_board(terminal, chess.Move.from_uci("h8h7"))
    with pytest.raises(ValueError, match="illegal"):
        child_board(chess.Board(), chess.Move.from_uci("e2e5"))


def test_capture_descendant_preserves_captured_material_and_history() -> None:
    board = chess.Board("7k/8/8/8/8/8/1r6/KR6 w - - 0 1")
    child = child_board(board, chess.Move.from_uci("b1b2"))
    assert child.piece_at(chess.B2) == chess.Piece(chess.ROOK, chess.WHITE)
    assert len(child.move_stack) == 1
