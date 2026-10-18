"""Hand-checked chess-tree tests for protocol-v1 target construction."""

import math

import chess
import pytest

from chesslab.endgames.replay import ReplayTransition
from chesslab.endgames.targets import Predictor, build_targets


class BranchPredictor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(
        self, boards: list[chess.Board] | tuple[chess.Board, ...], learner: chess.Color
    ) -> list[float]:
        assert learner == chess.WHITE
        replies = [board.move_stack[-2].uci() for board in boards]
        self.calls.extend(replies)
        value_by_reply = {"h8g8": -0.8, "h8h7": 0.4, "h8g7": -0.2}
        return [value_by_reply[reply] for reply in replies]


class MoveValuePredictor:
    def __init__(self) -> None:
        self.moves: list[str] = []

    def __call__(
        self, boards: list[chess.Board] | tuple[chess.Board, ...], learner: chess.Color
    ) -> list[float]:
        moves = [board.move_stack[-1].uci() for board in boards]
        self.moves.extend(moves)
        value_by_move = {"g2g8": -0.9, "g2g7": 0.8, "g2g6": -0.3}
        return [value_by_move.get(move, -0.5) for move in moves]


def _transition(
    fen: str, reply: str | None, learner: chess.Color = chess.WHITE
) -> ReplayTransition:
    return ReplayTransition(
        chess.Board(fen),
        learner,
        chess.Move.from_uci(reply) if reply is not None else None,
    )


def test_observed_defensive_and_mixed_targets_on_small_real_tree() -> None:
    afterstate = _transition("7k/8/8/8/8/8/5R2/K7 b - - 0 1", "h8h7")
    predictor = BranchPredictor()
    observed = build_targets([afterstate], 0.0, predictor)
    assert observed.targets == (0.4,)
    assert set(predictor.calls) == {"h8h7"}
    assert observed.forward_leaf_count == 17

    predictor = BranchPredictor()
    defensive = build_targets([afterstate], 1.0, predictor)
    assert defensive.targets == (-0.8,)
    assert set(predictor.calls) == {"h8g8", "h8h7", "h8g7"}
    assert defensive.forward_leaf_count == 51

    mixed = build_targets([afterstate], 0.5, BranchPredictor())
    assert mixed.targets == pytest.approx((-0.2,))
    assert mixed.forward_leaf_count == defensive.forward_leaf_count


def test_learner_response_uses_maximum_over_nonconstant_leaf_values() -> None:
    transition = _transition("7k/8/8/8/8/8/6R1/K7 b - - 0 1", "h8h7")
    predictor = MoveValuePredictor()
    result = build_targets([transition], 0.0, predictor)
    assert result.targets == (0.8,)
    assert "g2g7" in predictor.moves
    assert predictor.moves[0] == "g2g8"


def test_black_learner_and_mixed_color_batch_use_fixed_perspective() -> None:
    white_learner = _transition("7k/8/8/8/8/8/5R2/K7 b - - 0 1", "h8h7")
    black_learner = _transition(
        "k7/8/8/8/8/8/5r2/7K w - - 0 1", "h1g1", chess.BLACK
    )
    calls: list[chess.Color] = []

    def predictor(
        boards: list[chess.Board] | tuple[chess.Board, ...], learner: chess.Color
    ) -> list[float]:
        calls.append(learner)
        return [0.25 if learner == chess.WHITE else -0.35] * len(boards)

    result = build_targets([white_learner, black_learner], 0.0, predictor)
    assert result.targets == (0.25, -0.35)
    assert set(calls) == {chess.WHITE, chess.BLACK}
    assert len(calls) == 2


def test_opponent_mate_returns_loss_from_fixed_learner_view() -> None:
    transition = _transition("8/8/8/8/8/8/8/K1kq4 b - - 0 1", "d1a4")

    def optimistic_predictor(
        boards: list[chess.Board] | tuple[chess.Board, ...], learner: chess.Color
    ) -> list[float]:
        return [1.0] * len(boards)

    result = build_targets([transition], 1.0, optimistic_predictor)
    assert result.targets == (-1.0,)
    assert result.forward_leaf_count > 0


def test_stored_observed_reply_is_used_without_resampling() -> None:
    transition = _transition("7k/8/8/8/8/8/5R2/K7 b - - 0 1", "h8g7")
    predictor = BranchPredictor()
    result = build_targets([transition], 0.0, predictor)
    assert result.targets == (-0.2,)
    assert set(predictor.calls) == {"h8g7"}


def test_terminal_afterstate_uses_reward_once_without_predictor() -> None:
    checkmate = _transition("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", None)

    def unexpected_predictor(
        boards: list[chess.Board] | tuple[chess.Board, ...], learner: chess.Color
    ) -> list[float]:
        raise AssertionError("terminal target must not call predictor")

    result = build_targets([checkmate], 0.5, unexpected_predictor)
    assert result.targets == (1.0,)
    assert result.forward_leaf_count == 0


def test_terminal_opponent_reply_claim_draw_is_direct_reward() -> None:
    transition = _transition("7k/8/8/8/8/8/8/KR6 b - - 98 1", "h8g8")
    result = build_targets(
        [transition],
        0.0,
        lambda boards, learner: (_ for _ in ()).throw(
            AssertionError("terminal reply must not call predictor")
        ),
    )
    assert result.targets == (0.0,)
    assert result.forward_leaf_count == 0


def test_terminal_learner_reply_is_included_without_bootstrapping() -> None:
    # Black is in check and has two evasions; after g8-h8, Qg7 is mate.
    transition = _transition("6k1/8/5KQ1/8/8/8/8/8 b - - 0 1", "g8h8")
    result = build_targets(
        [transition],
        0.0,
        lambda boards, learner: [-1.0] * len(boards),
    )
    assert result.targets == (1.0,)
    assert 0 < result.forward_leaf_count


def test_claimable_repetition_afterstate_is_draw_and_history_is_unchanged() -> None:
    board = chess.Board()
    for uci in ("g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1"):
        board.push_uci(uci)
    assert board.can_claim_threefold_repetition()
    original_stack = tuple(board.move_stack)
    transition = ReplayTransition(board, chess.WHITE, None)

    def unexpected_predictor(
        boards: list[chess.Board], learner: chess.Color
    ) -> list[float]:
        raise AssertionError("claimable afterstate must not call predictor")

    result = build_targets([transition], 1.0, unexpected_predictor)
    assert result.targets == (0.0,)
    assert result.forward_leaf_count == 0
    assert tuple(board.move_stack) == original_stack


@pytest.mark.parametrize("beta", [-0.01, 1.01, math.nan, math.inf, -math.inf])
def test_beta_must_be_finite_and_in_unit_interval(beta: float) -> None:
    with pytest.raises(ValueError, match="beta"):
        build_targets([], beta, lambda boards, learner: [])


@pytest.mark.parametrize(
    "predictor",
    [
        lambda boards, learner: [],
        lambda boards, learner: [1.1] * len(boards),
        lambda boards, learner: [math.nan] * len(boards),
    ],
)
def test_predictor_outputs_are_validated(predictor: Predictor) -> None:
    transition = _transition("7k/8/8/8/8/8/5R2/K7 b - - 0 1", "h8h7")
    with pytest.raises(ValueError, match="predictor"):
        build_targets([transition], 0.0, predictor)
