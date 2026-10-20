"""Tests for fixed-start evaluation helpers."""

import random

import chess
import pytest

import chesslab.endgames.evaluation as evaluation


class DrawTablebase:
    def probe_wdl(self, board: chess.Board) -> int:
        return 0

    def probe_dtz(self, board: chess.Board) -> int:
        return 0


@pytest.mark.parametrize("learner", [chess.WHITE, chess.BLACK])
def test_reference_failure_is_not_a_policy_mistake(learner: chess.Color) -> None:
    class MissingTablebase(DrawTablebase):
        def probe_wdl(self, board: chess.Board) -> int:
            raise KeyError("missing table")

    result = evaluation.play_fixed_game(
        chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1"),
        learner, zero, MissingTablebase(), random.Random(1), random.Random(2), 0.0,
    )
    assert result.failure is not None
    assert result.reference_failures == 1
    assert result.learner_reference_errors == 0
    assert result.reference_evaluated_decisions == 0
    assert result.reward is None
    assert result.plies == 0


def zero(boards: list[chess.Board], learner: chess.Color) -> list[float]:
    return [0.0] * len(boards)


@pytest.mark.parametrize("turn", [chess.WHITE, chess.BLACK])
def test_prediction_target_uses_opposite_of_side_to_move(turn: chess.Color) -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    board.turn = turn
    seen: list[chess.Color] = []

    def predictor(boards: list[chess.Board], learner: chess.Color) -> list[float]:
        seen.append(learner)
        return [0.25]

    result = evaluation.evaluate_predictions([board], predictor, DrawTablebase())
    assert seen == [not turn]
    assert result.targets == (0.0,)
    assert result.mse == pytest.approx(0.0625)


def test_choice_uses_uci_tie_break_and_reports_draw_stratum() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    result = evaluation.evaluate_choices([board], zero, DrawTablebase())
    assert result.records[0].selected_move == min(
        move.uci() for move in board.legal_moves
    )
    assert result.records[0].selected_q == result.records[0].best_q == 0
    assert result.records[0].categorical_loss == 0
    assert result.loss_rate_by_best_q == ((0, 0.0),)


def test_choice_reports_nonzero_theoretical_loss() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    selected = min(board.legal_moves, key=lambda move: move.uci())
    bad_child = board.copy()
    bad_child.push(selected)

    class OneBadMoveTablebase(DrawTablebase):
        def probe_wdl(self, position: chess.Board) -> int:
            return 2 if position.board_fen() == bad_child.board_fen() else -2

    result = evaluation.evaluate_choices([board], zero, OneBadMoveTablebase())
    assert result.records[0].loss
    assert result.records[0].categorical_loss == 1.0
    assert result.loss_rate == 1.0


def test_prediction_sign_is_learner_relative() -> None:
    class WinTablebase(DrawTablebase):
        def probe_wdl(self, board: chess.Board) -> int:
            return 2

    board = chess.Board("7k/8/8/8/8/8/8/KR6 b - - 0 1")
    result = evaluation.evaluate_predictions(
        [board], lambda boards, learner: [0.0], WinTablebase()
    )
    assert result.targets == (-1.0,)
    assert result.mse == 1.0


def test_game_keeps_history_and_claim_draw_precedes_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 99 1")
    # This is a prospective fifty-move claim before any move is made.
    monkeypatch.setattr(evaluation, "MAX_GAME_PLIES", 0)
    result = evaluation.play_fixed_game(
        board,
        chess.WHITE,
        zero,
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        0.25,
    )
    assert result.reward == 0.0
    assert not result.truncated
    assert result.plies == 0


def test_game_recognizes_threefold_claim_from_supplied_history() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    cycle = ("b1b2", "h8h7", "b2b1", "h7h8")
    for _ in range(2):
        for uci in cycle:
            board.push_uci(uci)
    result = evaluation.play_fixed_game(
        board,
        chess.WHITE,
        zero,
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        0.0,
    )
    assert result.reward == 0.0
    assert result.plies == 0


def test_game_cap_records_partial_game(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluation, "MAX_GAME_PLIES", 1)
    result = evaluation.play_fixed_game(
        chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1"),
        chess.WHITE,
        zero,
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        0.5,
    )
    assert result.truncated and result.truncation_reason == "ply_cap"
    assert result.reward is None
    assert result.plies == 1
    assert result.moves
    assert len(result.encountered_keys) == 2


def test_game_failure_retains_partial_counters() -> None:
    def broken(boards: list[chess.Board], learner: chess.Color) -> list[float]:
        raise RuntimeError("predictor offline")

    result = evaluation.play_fixed_game(
        chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1"),
        chess.WHITE,
        broken,
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        0.0,
    )
    assert result.failure == "RuntimeError: predictor offline"
    assert result.learner_decisions == 0
    assert result.learner_reference_errors == 0
    assert result.reference_failures == 0
    assert result.plies == 0
    assert result.encountered_keys


@pytest.mark.parametrize("learner", [chess.WHITE, chess.BLACK])
@pytest.mark.parametrize("p", [0.0, 0.25, 0.5])
def test_game_runs_for_either_learner_color_and_p(
    monkeypatch: pytest.MonkeyPatch, learner: chess.Color, p: float
) -> None:
    monkeypatch.setattr(evaluation, "MAX_GAME_PLIES", 1)
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    board.turn = learner
    snapshots: list[evaluation.GameEvaluation] = []
    result = evaluation.play_fixed_game(
        board,
        learner,
        zero,
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        p,
        progress_callback=snapshots.append,
    )
    assert result.truncated
    assert result.plies == 1
    assert snapshots
    assert snapshots[-1].plies == 1
    assert result.reference_evaluated_decisions == 1


def test_deadline_exception_is_returned_as_partial_failure() -> None:
    def broken_deadline() -> bool:
        raise TimeoutError("clock failed")

    result = evaluation.play_fixed_game(
        chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1"),
        chess.WHITE,
        zero,
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        0.0,
        deadline_check=broken_deadline,
    )
    assert result.failure == "TimeoutError: clock failed"
    assert result.plies == 0


def test_deadline_truncates_with_partial_record() -> None:
    checks = 0

    def deadline() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    result = evaluation.play_fixed_game(
        chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1"),
        chess.WHITE,
        zero,
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        0.0,
        deadline_check=deadline,
    )
    assert result.truncated and result.truncation_reason == "deadline"
    assert result.plies == 1


def test_terminal_result_on_cap_ply_precedes_truncation() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(evaluation, "MAX_GAME_PLIES", 1)
    try:
        board = chess.Board("8/8/8/8/8/8/8/k1KQ4 w - - 0 1")

        def mate_in_one(boards: list[chess.Board], learner: chess.Color) -> list[float]:
            return [0.0] * len(boards)

        result = evaluation.play_fixed_game(
            board,
            chess.WHITE,
            mate_in_one,
            DrawTablebase(),
            random.Random(1),
            random.Random(2),
            0.0,
        )
        assert result.reward == 1.0
        assert not result.truncated
        assert result.plies == 1
    finally:
        monkeypatch.undo()
