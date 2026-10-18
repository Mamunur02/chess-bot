"""Theoretical Syzygy WDL/DTZ reference values for supported pawnless boards."""

from dataclasses import dataclass
from typing import Protocol

import chess


class SyzygyProbe(Protocol):
    """The minimal injected interface supplied by python-chess tablebases."""

    def probe_wdl(self, board: chess.Board) -> int:
        """Return Syzygy's five-valued WDL result."""

    def probe_dtz(self, board: chess.Board) -> int:
        """Return Syzygy distance-to-zeroing-move result."""


@dataclass(frozen=True, slots=True)
class ReferenceValue:
    """Auditable theoretical value and the unmodified tablebase probes."""

    value: int
    raw_wdl: int | None
    raw_dtz: int | None


def _supported_material(board: chess.Board) -> bool:
    if (
        board.chess960
        or board.pawns
        or board.castling_rights
        or board.ep_square is not None
    ):
        return False
    counts = {(piece_type, color): len(board.pieces(piece_type, color))
              for piece_type in (chess.KING, chess.QUEEN, chess.ROOK)
              for color in chess.COLORS}
    if sum(counts.values()) != len(board.piece_map()):
        return False
    if any(counts[chess.KING, color] != 1 for color in chess.COLORS):
        return False
    white = counts[chess.QUEEN, chess.WHITE], counts[chess.ROOK, chess.WHITE]
    black = counts[chess.QUEEN, chess.BLACK], counts[chess.ROOK, chess.BLACK]
    materials = {white, black}
    return materials in (
        {(0, 1)},
        {(1, 0), (0, 1)},
        {(0, 1), (0, 0)},
        {(1, 0), (0, 0)},
        {(0, 0)},
    )


def _history_free(board: chess.Board) -> chess.Board:
    probe_board = board.copy(stack=False)
    probe_board.halfmove_clock = 0
    probe_board.fullmove_number = 1
    return probe_board


def _validate_board(board: chess.Board) -> None:
    if not board.is_valid() or not _supported_material(board):
        raise ValueError("board is invalid or outside supported pawnless material")


def _terminal_value(board: chess.Board) -> int | None:
    if board.is_checkmate():
        return -1
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    return None


def evaluate(board: chess.Board, tablebase: SyzygyProbe) -> ReferenceValue:
    """Return theoretical side-to-move WDL and raw WDL/DTZ audit values.

    Historical repetition and move-count claims are ignored. Missing table files
    surface as a clear ``RuntimeError``; no approximate value is substituted.
    """
    _validate_board(board)
    probe_board = _history_free(board)
    terminal_value = _terminal_value(probe_board)
    if terminal_value is not None:
        return ReferenceValue(terminal_value, None, None)
    try:
        raw_wdl = tablebase.probe_wdl(probe_board)
        raw_dtz = tablebase.probe_dtz(probe_board)
    except (KeyError, OSError) as exc:
        raise RuntimeError("required Syzygy WDL/DTZ table is unavailable") from exc
    if raw_wdl not in (-2, -1, 0, 1, 2):
        raise ValueError(f"invalid Syzygy WDL result: {raw_wdl}")
    return ReferenceValue((raw_wdl > 0) - (raw_wdl < 0), raw_wdl, raw_dtz)


def action_value(board: chess.Board, move: chess.Move, tablebase: SyzygyProbe) -> int:
    """Return theoretical after-move value, ignoring claims and move clocks."""
    _validate_board(board)
    theoretical_board = _history_free(board)
    if _terminal_value(theoretical_board) is not None:
        raise ValueError("cannot act on a theoretically terminal board")
    if move not in theoretical_board.legal_moves:
        raise ValueError(f"illegal move: {move}")
    child = theoretical_board
    child.push(move)
    return -evaluate(child, tablebase).value
