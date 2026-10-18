"""Protocol tests for the explicit-RNG fallible endgame opponent."""

import math
import random

import chess
import pytest

from chesslab.endgames.opponent import choose_action


def _key(board: chess.Board) -> tuple[str, chess.Color]:
    return board.board_fen(), board.turn


class ScriptedTablebase:
    def __init__(self, values: dict[tuple[str, chess.Color], tuple[int, int]]) -> None:
        self.values = values

    def probe_wdl(self, board: chess.Board) -> int:
        return self.values.get(_key(board), (0, 0))[0]

    def probe_dtz(self, board: chess.Board) -> int:
        return self.values.get(_key(board), (0, 0))[1]


def _table_for_moves(
    board: chess.Board,
    values: dict[str, tuple[int, int]],
) -> ScriptedTablebase:
    mapped: dict[tuple[str, chess.Color], tuple[int, int]] = {}
    for move in board.legal_moves:
        child = board.copy(stack=True)
        child.push(move)
        if not child.is_checkmate() and not child.is_stalemate():
            mapped[_key(child)] = values.get(move.uci(), (0, 0))
    return ScriptedTablebase(mapped)


def _basic_board() -> chess.Board:
    return chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")


def test_p_zero_uses_deterministic_best_and_preserves_input() -> None:
    board = _basic_board()
    before_fen = board.fen()
    before_stack = list(board.move_stack)
    values = {"b1b2": (-2, 5), "b1b3": (-1, -100)}

    decision = choose_action(
        board,
        _table_for_moves(board, values),
        random.Random(19),
        0,
    )

    assert decision.action == chess.Move.from_uci("b1b2")
    assert decision.selected_q == 1
    assert decision.category_loss == 0
    assert not decision.realized_worsening
    assert decision.opportunity
    assert decision.requested_p == 0
    assert board.fen() == before_fen
    assert board.move_stack == before_stack
    assert {audit.move.uci(): audit.raw_wdl for audit in decision.actions}["b1b2"] == -2
    assert {audit.move.uci(): audit.raw_dtz for audit in decision.actions}["b1b2"] == 5


def test_p_one_samples_uniform_worsening_moves_reproducibly() -> None:
    board = _basic_board()
    values = {"b1b2": (-2, 0), "b1b3": (-1, 0)}
    table = _table_for_moves(board, values)

    first = choose_action(board, table, random.Random(991), 1)
    repeated = choose_action(board, table, random.Random(991), 1)

    assert first.action == repeated.action
    assert first.selected_q == 0
    assert first.category_loss == 1
    assert first.opportunity and first.realized_worsening
    assert first.action != chess.Move.from_uci("b1b2")


def test_no_worsening_action_falls_back_to_best_without_rng_use() -> None:
    board = _basic_board()
    rng = random.Random(32)
    state = rng.getstate()

    decision = choose_action(board, _table_for_moves(board, {}), rng, 1)

    assert not decision.opportunity
    assert not decision.realized_worsening
    assert decision.category_loss == 0
    assert rng.getstate() == state


def test_best_category_precedes_worse_move_dtz() -> None:
    board = _basic_board()
    values = {"b1b2": (-1, 100), "b1b3": (0, 0)}
    decision = choose_action(
        board,
        _table_for_moves(board, values),
        random.Random(1),
        0,
    )
    assert decision.action == chess.Move.from_uci("b1b2")
    assert decision.selected_q == 1


def test_best_tie_uses_win_loss_and_draw_dtz_rules() -> None:
    board = _basic_board()

    win_values = {
        move.uci(): (-1, 30 + index)
        for index, move in enumerate(board.legal_moves)
    }
    win_values["b1b2"] = (-1, 50)
    win_values["b1b3"] = (-1, -2)
    win = choose_action(
        board, _table_for_moves(board, win_values), random.Random(1), 0
    )
    assert win.action == chess.Move.from_uci("b1b3")

    loss_values = {
        move.uci(): (1, 1)
        for move in board.legal_moves
    }
    loss_values["b1b2"] = (1, 4)
    loss_values["b1b3"] = (1, -40)
    loss = choose_action(
        board, _table_for_moves(board, loss_values), random.Random(1), 0
    )
    assert loss.action == chess.Move.from_uci("b1b3")

    draw_values = {
        move.uci(): (0, 50 - index)
        for index, move in enumerate(board.legal_moves)
    }
    draw = choose_action(
        board, _table_for_moves(board, draw_values), random.Random(1), 0
    )
    expected = min(board.legal_moves, key=lambda move: move.uci())
    assert draw.action == expected


def test_best_tie_prefers_fewer_successor_occurrences_in_real_history() -> None:
    board = _basic_board()
    for uci in ("b1b2", "h8h7", "b2b1", "h7h8"):
        board.push_uci(uci)
    assert board.outcome(claim_draw=True) is None

    decision = choose_action(
        board,
        _table_for_moves(board, {}),
        random.Random(2),
        0,
    )
    audits = {audit.move.uci(): audit for audit in decision.actions}
    assert audits["b1b2"].history_occurrences == 1
    assert decision.action != chess.Move.from_uci("b1b2")
    assert audits[decision.action.uci()].history_occurrences == 0


def test_immediate_mate_precedes_history_dtz_and_uci_ties() -> None:
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")
    mate_moves = []
    values: dict[str, tuple[int, int]] = {}
    for move in board.legal_moves:
        child = board.copy(stack=True)
        child.push(move)
        if child.is_checkmate():
            mate_moves.append(move)
        values[move.uci()] = (-1, 0)
    assert mate_moves

    decision = choose_action(
        board,
        _table_for_moves(board, values),
        random.Random(3),
        0,
    )

    assert decision.action in mate_moves
    assert next(a for a in decision.actions if a.move == decision.action).immediate_mate


@pytest.mark.parametrize("p", [-0.01, 1.01, math.inf, -math.inf, math.nan, True, "0.5"])
def test_probability_must_be_finite_numeric_and_in_range(p: object) -> None:
    with pytest.raises(ValueError, match="p must be finite"):
        choose_action(_basic_board(), ScriptedTablebase({}), random.Random(0), p)  # type: ignore[arg-type]


def test_terminal_board_is_rejected_even_when_legal_claim_is_available() -> None:
    board = _basic_board()
    for uci in (
        "b1b2", "h8h7", "b2b1", "h7h8",
        "b1b2", "h8h7", "b2b1", "h7h8",
    ):
        board.push_uci(uci)
    assert board.can_claim_threefold_repetition()

    with pytest.raises(ValueError, match="terminal board"):
        choose_action(board, ScriptedTablebase({}), random.Random(0), 0)
