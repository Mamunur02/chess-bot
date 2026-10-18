"""Theoretical Syzygy reference adapter tests using tiny mocks."""

import chess
import pytest

from chesslab.endgames.reference import action_value, evaluate


class MockTablebase:
    def __init__(self, wdl: int = 0, dtz: int = 0) -> None:
        self.wdl = wdl
        self.dtz = dtz
        self.wdl_board: chess.Board | None = None
        self.dtz_board: chess.Board | None = None

    def probe_wdl(self, board: chess.Board) -> int:
        self.wdl_board = board
        return self.wdl

    def probe_dtz(self, board: chess.Board) -> int:
        self.dtz_board = board
        return self.dtz


@pytest.mark.parametrize(("wdl", "sign"), [(-2, -1), (-1, -1), (0, 0), (1, 1), (2, 1)])
def test_all_five_wdl_values_keep_raw_audit_result(wdl: int, sign: int) -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    result = evaluate(board, MockTablebase(wdl, 37))
    assert (result.value, result.raw_wdl, result.raw_dtz) == (sign, wdl, 37)


def test_probe_ignores_history_and_resets_clock() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    board.push_uci("b1b2")
    board.halfmove_clock = 99
    table = MockTablebase(1, 4)
    evaluate(board, table)
    assert table.wdl_board is not board
    assert table.wdl_board is not None
    assert table.wdl_board.halfmove_clock == 0
    assert table.wdl_board.move_stack == []
    assert table.dtz_board is not None
    assert table.dtz_board.halfmove_clock == 0


@pytest.mark.parametrize(
    ("fen", "value"),
    [
        ("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", -1),
        ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 0),
        ("7k/8/8/8/8/8/8/K7 w - - 0 1", 0),
    ],
)
def test_terminal_boards_are_resolved_without_probing(fen: str, value: int) -> None:
    table = MockTablebase()
    result = evaluate(chess.Board(fen), table)
    assert result.value == value
    assert result.raw_wdl is None
    assert table.wdl_board is None


def test_action_value_flips_child_side_to_move_value() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    move = chess.Move.from_uci("b1b2")
    assert action_value(board, move, MockTablebase(-2, -5)) == 1


def test_action_value_ignores_claimable_clock_and_repetition_history() -> None:
    fresh = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    table = MockTablebase(-2, 12)
    expected = action_value(fresh, chess.Move.from_uci("b1b2"), table)

    clock_claim = fresh.copy()
    clock_claim.halfmove_clock = 100
    assert clock_claim.can_claim_fifty_moves()
    assert action_value(clock_claim, chess.Move.from_uci("b1b2"), table) == expected

    repetition = fresh.copy()
    for uci in (
        "b1b2", "h8h7", "b2b1", "h7h8",
        "b1b2", "h8h7", "b2b1", "h7h8",
    ):
        repetition.push_uci(uci)
    assert repetition.can_claim_threefold_repetition()
    assert action_value(repetition, chess.Move.from_uci("b1b2"), table) == expected


def test_missing_table_fails_clearly() -> None:
    class MissingTable(MockTablebase):
        def probe_wdl(self, board: chess.Board) -> int:
            raise KeyError("missing rtbw")

    with pytest.raises(RuntimeError, match="Syzygy WDL/DTZ table is unavailable"):
        evaluate(chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1"), MissingTable())


@pytest.mark.parametrize(
    "fen",
    [
        "7k/8/8/8/8/8/8/KR6 w - - 0 1",  # KRvK
        "7k/8/8/8/8/8/8/KQ6 w - - 0 1",  # KQvK
        "1r5k/8/8/8/8/8/8/KQ6 w - - 0 1",  # KQvKR
        "1q5k/8/8/8/8/8/8/KR6 w - - 0 1",  # KRvKQ
        "7k/8/8/8/8/8/8/KRr5 w - - 0 1",  # KRvKR
        "7k/8/8/8/8/8/8/K7 w - - 0 1",  # KK
    ],
)
def test_supported_material_families_and_colour_assignments(fen: str) -> None:
    evaluate(chess.Board(fen), MockTablebase())


@pytest.mark.parametrize(
    "fen",
    [
        chess.STARTING_FEN,
        "7k/8/8/8/8/8/8/KR6 w K - 0 1",
        "7k/8/8/8/8/8/8/KR6 w - a6 0 1",
        "7k/8/8/8/8/8/P7/KR6 w - - 0 1",
        "7k/8/8/8/8/8/2B5/KR6 w - - 0 1",
    ],
)
def test_rejects_unsupported_boards(fen: str) -> None:
    with pytest.raises(ValueError, match="outside supported"):
        evaluate(chess.Board(fen), MockTablebase())


def test_rejects_chess960_board() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1", chess960=True)
    with pytest.raises(ValueError, match="outside supported"):
        evaluate(board, MockTablebase())
