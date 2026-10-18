"""History retention and explicit randomness tests for replay storage."""

import random

import chess
import pytest

from chesslab.endgames.replay import ReplayBuffer


def test_append_and_sample_copy_full_history_and_keep_observed_reply() -> None:
    afterstate = chess.Board()
    afterstate.push_uci("g1f3")
    reply = chess.Move.from_uci("g8f6")
    buffer = ReplayBuffer(capacity=3)
    buffer.append(afterstate, chess.WHITE, reply)

    afterstate.move_stack[0].from_square = chess.H2
    reply.to_square = chess.H7
    sample = buffer.sample(1, random.Random(11))[0]
    assert sample.observed_reply == chess.Move.from_uci("g8f6")
    assert len(sample.afterstate.move_stack) == 1
    assert sample.afterstate.move_stack[0] == chess.Move.from_uci("g1f3")
    assert sample.observed_reply is not None
    sample.observed_reply.from_square = chess.H7
    sample.afterstate.move_stack[0].to_square = chess.H3
    sample.afterstate.pop()
    again = buffer.sample(1, random.Random(11))[0]
    assert again.observed_reply == chess.Move.from_uci("g8f6")
    assert len(again.afterstate.move_stack) == 1
    assert again.afterstate.move_stack[0] == chess.Move.from_uci("g1f3")


def test_ring_capacity_keeps_only_newest_transitions() -> None:
    buffer = ReplayBuffer(capacity=2)
    states = []
    for uci in ("g1f3", "b1c3", "e2e4"):
        board = chess.Board()
        move = chess.Move.from_uci(uci)
        board.push(move)
        reply = next(iter(board.legal_moves))
        states.append((board.fen(), reply))
        buffer.append(board, chess.WHITE, reply)
    assert len(buffer) == 2
    sampled = buffer.sample(2, random.Random(3))
    assert {(entry.afterstate.fen(), entry.observed_reply) for entry in sampled} == set(
        states[1:]
    )


def test_sampling_uses_supplied_rng_without_replacement() -> None:
    buffer = ReplayBuffer(capacity=8)
    for uci in ("g1f3", "b1c3", "e2e4", "d2d4"):
        board = chess.Board()
        board.push_uci(uci)
        buffer.append(board, chess.WHITE, next(iter(board.legal_moves)))
    first = buffer.sample(4, random.Random(42))
    second = buffer.sample(4, random.Random(42))
    assert [item.afterstate.fen() for item in first] == [
        item.afterstate.fen() for item in second
    ]
    assert len({item.afterstate.fen() for item in first}) == 4


def test_terminal_afterstate_accepts_no_reply() -> None:
    board = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    buffer = ReplayBuffer()
    buffer.append(board, chess.WHITE, None)
    transition = buffer.sample(1, random.Random(1))[0]
    assert transition.observed_reply is None
    assert transition.afterstate.is_checkmate()


def test_rejects_inconsistent_transitions_and_invalid_sizes() -> None:
    with pytest.raises(ValueError, match="positive"):
        ReplayBuffer(0)
    board = chess.Board()
    buffer = ReplayBuffer()
    with pytest.raises(ValueError, match="opponent to move"):
        buffer.append(board, chess.WHITE, chess.Move.from_uci("e7e5"))
    board.push_uci("e2e4")
    with pytest.raises(ValueError, match="requires an observed reply"):
        buffer.append(board, chess.WHITE, None)
    with pytest.raises(ValueError, match="illegal"):
        buffer.append(board, chess.WHITE, chess.Move.from_uci("e2e4"))
    with pytest.raises(ValueError, match="nonnegative"):
        buffer.sample(-1, random.Random(2))
    with pytest.raises(ValueError, match="Sample larger"):
        buffer.sample(1, random.Random(2))
