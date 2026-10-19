"""Tests for afterstate action selection and bounded game simulation."""

import random

import chess
import pytest

import chesslab.endgames.interaction as interaction
from chesslab.endgames.opponent import OpponentDecision


class DrawTablebase:
    def probe_wdl(self, board: chess.Board) -> int:
        return 0

    def probe_dtz(self, board: chess.Board) -> int:
        return 0


def _rook_start() -> str:
    return "7k/8/8/8/8/8/8/KR6 w - - 0 1"


def _predict_zero(boards: list[chess.Board], learner: chess.Color) -> list[float]:
    return [0.0] * len(boards)


def _first_legal_opponent(
    board: chess.Board,
    tablebase: DrawTablebase,
    rng: random.Random,
    p: float,
) -> OpponentDecision:
    action = min(board.legal_moves, key=lambda move: move.uci())
    return OpponentDecision(action, 0, (), 0, False, False, p)


def _run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    starts: list[str] | None = None,
    decisions: int = 1,
    initial_color: chess.Color = chess.WHITE,
    predictor: interaction.Predictor = _predict_zero,
) -> tuple[interaction.InteractionResult, list[object]]:
    monkeypatch.setattr(interaction, "choose_action", _first_legal_opponent)
    transitions: list[object] = []
    result = interaction.run_interaction(
        starts or [_rook_start()],
        decisions,
        predictor,
        DrawTablebase(),
        random.Random(11),
        random.Random(12),
        random.Random(13),
        initial_color,
        0.0,
        0.0,
        transitions.append,  # type: ignore[arg-type]
    )
    return result, transitions


def test_greedy_selector_uses_predictor_and_uci_ties_without_mutation() -> None:
    board = chess.Board(_rook_start())
    before_fen = board.fen()
    before_stack = list(board.move_stack)
    seen: list[chess.Board] = []

    def predictor(boards: list[chess.Board], learner: chess.Color) -> list[float]:
        seen.extend(boards)
        assert learner == chess.WHITE
        return [0.25] * len(boards)

    decision = interaction.select_learner_move(
        board, chess.WHITE, predictor, random.Random(1), 0.0
    )

    assert decision.action == min(board.legal_moves, key=lambda move: move.uci())
    assert decision.forward_evaluations == len(seen) > 0
    assert decision.predictor_calls == 1
    assert all(position.move_stack for position in seen)
    assert board.fen() == before_fen
    assert board.move_stack == before_stack


def test_epsilon_one_samples_uniform_legal_move_without_predictor_call() -> None:
    board = chess.Board(_rook_start())
    rng = random.Random(92)
    first = interaction.select_learner_move(
        board,
        chess.WHITE,
        lambda boards, learner: pytest.fail("epsilon branch must not evaluate"),
        rng,
        1.0,
    )
    repeated = interaction.select_learner_move(
        board, chess.WHITE, _predict_zero, random.Random(92), 1.0
    )

    assert first.action == repeated.action
    assert first.action in board.legal_moves
    assert first.forward_evaluations == first.predictor_calls == 0


def test_terminal_learner_afterstate_uses_actual_reward() -> None:
    mate_start = "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1"
    transitions: list[object] = []
    result = interaction.run_interaction(
        [mate_start],
        1,
        lambda boards, learner: [-1.0] * len(boards),
        DrawTablebase(),
        random.Random(1),
        random.Random(2),
        random.Random(3),
        chess.WHITE,
        0.0,
        0.0,
        transitions.append,  # type: ignore[arg-type]
    )

    assert result.decisions == 1
    assert result.transitions == 1
    assert result.episodes[0].reward == 1.0
    assert not result.episodes[0].truncated
    assert result.learner_wins == 1
    assert result.truncated_episodes == 0
    transition = transitions[0]
    assert transition.observed_reply is None  # type: ignore[attr-defined]
    assert transition.afterstate.is_checkmate()  # type: ignore[attr-defined]


def test_global_budget_records_last_reply_then_truncates_without_reward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, transitions = _run(monkeypatch)

    assert result.decisions == 1
    assert result.transitions == 1
    assert len(transitions) == 1
    transition = transitions[0]
    assert transition.observed_reply in transition.afterstate.legal_moves  # type: ignore[attr-defined]
    assert result.episodes[0].truncated
    assert result.episodes[0].truncation_reason == "decision_budget"
    assert result.episodes[0].reward is None
    assert result.truncated_episodes == 1


def test_black_learner_receives_opponent_move_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_turns: list[chess.Color] = []

    def opponent(board, tablebase, rng, p):
        seen_turns.append(board.turn)
        return _first_legal_opponent(board, tablebase, rng, p)

    monkeypatch.setattr(interaction, "choose_action", opponent)
    result = interaction.run_interaction(
        [_rook_start()],
        1,
        _predict_zero,
        DrawTablebase(),
        random.Random(3),
        random.Random(4),
        random.Random(5),
        chess.BLACK,
        0.0,
        0.0,
    )

    assert seen_turns[0] == chess.WHITE
    assert result.decisions == 1
    assert result.transitions == 1
    assert result.episodes[0].learner == chess.BLACK


def test_opponent_opportunities_mistakes_and_severity_are_aggregated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def worsening_opponent(board, tablebase, rng, p):
        action = min(board.legal_moves, key=lambda move: move.uci())
        return OpponentDecision(action, -1, (), 2, True, True, p)

    monkeypatch.setattr(interaction, "choose_action", worsening_opponent)
    result = interaction.run_interaction(
        [_rook_start()],
        1,
        _predict_zero,
        DrawTablebase(),
        random.Random(3),
        random.Random(4),
        random.Random(5),
        chess.WHITE,
        0.0,
        0.5,
    )

    assert result.opponent_opportunities == 1
    assert result.opponent_worsenings == 1
    assert result.opponent_category_loss == 2


def test_decision_budget_is_exact_and_episode_colors_alternate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run(
        monkeypatch,
        starts=["7k/5Q2/6K1/8/8/8/8/8 w - - 0 1"],
        decisions=2,
        predictor=lambda boards, learner: [-1.0] * len(boards),
    )

    assert result.decisions == 2
    colors = [episode.learner for episode in result.episodes]
    assert colors[:2] == [chess.WHITE, chess.BLACK]
    assert all(left != right for left, right in zip(colors, colors[1:]))
    assert sum(episode.learner_decisions for episode in result.episodes) == 2
    assert all(
        episode.reward is None for episode in result.episodes if episode.truncated
    )
    assert result.encountered_keys


def test_ply_cap_after_unanswered_learner_afterstate_is_unrecorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(interaction, "MAX_GAME_PLIES", 1)
    result, transitions = _run(monkeypatch)

    assert result.decisions == 1
    assert result.transitions == 0
    assert result.unrecorded_decisions == 1
    assert transitions == []
    assert result.episodes[0].truncated
    assert result.episodes[0].truncation_reason == "ply_cap"
    assert result.episodes[0].reward is None


@pytest.mark.parametrize(
    "fen",
    [
        "7k/8/8/8/8/8/8/KR6 w - - 1 1",
        "7k/8/8/8/8/8/8/KR6 w - - 0 2",
        "7k/8/8/8/8/8/8/KR6 w K - 0 1",
    ],
)
def test_start_fens_must_be_zero_clock_historyless_protocol_positions(
    fen: str,
) -> None:
    with pytest.raises(ValueError):
        interaction.run_interaction(
            [fen], 1, _predict_zero, DrawTablebase(), random.Random(1),
            random.Random(2), random.Random(3), chess.WHITE, 0.0, 0.0
        )
