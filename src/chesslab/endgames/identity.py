"""Canonical position identity and deterministic split/RNG helpers.

This module implements the identity rules for opponent-dependence protocol v1.
Inputs are standard, pawnless chess boards without castling or en-passant
rights. Clocks and move history do not contribute to identity.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable

import chess

_PROTOCOL_PREFIX = "protocol-v1"
_PARTITION_NAMES: tuple[tuple[int, int, str], ...] = (
    (0, 9, "development"),
    (10, 54, "pretraining"),
    (55, 69, "rl_starts"),
    (70, 79, "validation"),
    (80, 89, "final_broad"),
    (90, 99, "final_diagnostic"),
)


def _symmetries() -> tuple[Callable[[chess.Square], chess.Square], ...]:
    """Return the eight square-board D4 mappings in a fixed order."""

    mappings: list[Callable[[chess.Square], chess.Square]] = []
    for reflected in (False, True):
        for quarter_turns in range(4):

            def mapping(
                square: chess.Square,
                *,
                reflected: bool = reflected,
                quarter_turns: int = quarter_turns,
            ) -> chess.Square:
                file_index = chess.square_file(square)
                rank_index = chess.square_rank(square)
                if reflected:
                    file_index = 7 - file_index
                for _ in range(quarter_turns):
                    file_index, rank_index = 7 - rank_index, file_index
                return chess.square(file_index, rank_index)

            mappings.append(mapping)
    return tuple(mappings)


_D4_SYMMETRIES = _symmetries()


def _color_exchanged(board: chess.Board) -> chess.Board:
    """Copy a board while swapping every piece colour and the side to move."""

    exchanged = chess.Board(None)
    for square, piece in board.piece_map().items():
        exchanged.set_piece_at(
            square,
            chess.Piece(piece.piece_type, not piece.color),
        )
    exchanged.turn = not board.turn
    return exchanged


def _transformed_board(
    board: chess.Board,
    transform: Callable[[chess.Square], chess.Square],
) -> chess.Board:
    """Transform piece squares while preserving colours and side to move."""

    transformed = chess.Board(None)
    for square, piece in board.piece_map().items():
        transformed.set_piece_at(transform(square), piece)
    transformed.turn = board.turn
    return transformed


def _validate_board(board: chess.Board) -> None:
    if board.chess960:
        raise ValueError("identity supports standard chess boards only")
    if board.pieces(chess.PAWN, chess.WHITE) or board.pieces(chess.PAWN, chess.BLACK):
        raise ValueError("identity supports pawnless boards only")
    if board.castling_rights:
        raise ValueError("identity requires no castling rights")
    if board.ep_square is not None:
        raise ValueError("identity requires no en-passant square")


def canonical_position(board: chess.Board) -> str:
    """Return the lexicographically smallest D4-and-colour canonical key.

    Each candidate is serialized as ``"<board_fen> <w|b>"``. The board FEN
    placement includes all piece types and colours, so material is part of the
    key. For every square symmetry, both the original and colour-exchanged
    position are considered. Colour exchange flips side to move as well.
    Halfmove/fullmove clocks and move-stack history are ignored.
    """

    _validate_board(board)
    candidates: list[str] = []
    for transform in _D4_SYMMETRIES:
        transformed = _transformed_board(board, transform)
        for candidate_board in (transformed, _color_exchanged(transformed)):
            turn = "w" if candidate_board.turn == chess.WHITE else "b"
            candidates.append(f"{candidate_board.board_fen()} {turn}")
    return min(candidates)


def ownership_digest(family: str, canonical_position_key: str) -> bytes:
    """Return SHA-256 of the protocol-v1 ownership serialization as bytes."""

    if not family:
        raise ValueError("family must be a non-empty string")
    payload = f"{_PROTOCOL_PREFIX}|{family}|{canonical_position_key}"
    return hashlib.sha256(payload.encode("utf-8")).digest()


def ownership_bucket(family: str, canonical_position_key: str) -> int:
    """Return the ownership bucket: big-endian digest integer modulo 100."""

    return int.from_bytes(ownership_digest(family, canonical_position_key), "big") % 100


def split_for_bucket(bucket: int) -> str:
    """Map an ownership bucket in ``0..99`` to its protocol partition name."""

    if not 0 <= bucket < 100:
        raise ValueError("bucket must be between 0 and 99 inclusive")
    for lower, upper, name in _PARTITION_NAMES:
        if lower <= bucket <= upper:
            return name
    raise AssertionError("protocol partition ranges must cover all buckets")


def ownership_split(family: str, canonical_position_key: str) -> str:
    """Return the protocol partition assigned to this family and position."""

    return split_for_bucket(ownership_bucket(family, canonical_position_key))


def derive_seed(root_seed: int, stream_name: str) -> int:
    """Derive a stable named seed using the full big-endian SHA-256 digest.

    The exact UTF-8 input is ``protocol-v1|seed|<root_seed>|<stream_name>``.
    The resulting Python integer is suitable for ``random.Random`` and does
    not depend on Python's process-randomized ``hash()`` implementation.
    """

    if not isinstance(root_seed, int) or isinstance(root_seed, bool):
        raise TypeError("root_seed must be an integer")
    if not stream_name:
        raise ValueError("stream_name must be a non-empty string")
    payload = f"{_PROTOCOL_PREFIX}|seed|{root_seed}|{stream_name}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest, "big")


def make_rng(root_seed: int, stream_name: str) -> random.Random:
    """Create an independent ``random.Random`` for a named deterministic stream."""

    return random.Random(derive_seed(root_seed, stream_name))
