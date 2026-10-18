"""Tests for protocol-v1 canonical identities and deterministic streams."""

import hashlib
import random

import chess
import pytest

from chesslab.endgames.identity import (
    canonical_position,
    derive_seed,
    make_rng,
    ownership_bucket,
    ownership_digest,
    ownership_split,
    split_for_bucket,
)


def _map_square(square: chess.Square, reflected: bool, turns: int) -> chess.Square:
    file_index = chess.square_file(square)
    rank_index = chess.square_rank(square)
    if reflected:
        file_index = 7 - file_index
    for _ in range(turns):
        file_index, rank_index = 7 - rank_index, file_index
    return chess.square(file_index, rank_index)


def _exchange_colors(board: chess.Board) -> chess.Board:
    result = chess.Board(None)
    for square, piece in board.piece_map().items():
        result.set_piece_at(square, chess.Piece(piece.piece_type, not piece.color))
    result.turn = not board.turn
    return result


@pytest.fixture
def position() -> chess.Board:
    return chess.Board("4k2r/8/8/8/8/8/8/R3K3 w - - 0 1")


def test_canonical_key_is_invariant_under_each_square_symmetry(
    position: chess.Board,
) -> None:
    expected = canonical_position(position)
    for reflected in (False, True):
        for turns in range(4):
            transformed = position.transform(
                lambda bitboard, reflected=reflected, turns=turns: chess.SquareSet(
                    _map_square(square, reflected, turns)
                    for square in chess.SquareSet(bitboard)
                ).mask
            )
            assert canonical_position(transformed) == expected


def test_color_exchange_swaps_pieces_and_side_to_move(position: chess.Board) -> None:
    exchanged = _exchange_colors(position)
    assert exchanged.turn != position.turn
    assert canonical_position(exchanged) == canonical_position(position)


def test_canonical_key_includes_turn_but_color_exchange_is_joint() -> None:
    white_to_move = chess.Board("4k2r/8/8/8/8/8/8/R3K3 w - - 0 1")
    black_to_move = white_to_move.copy()
    black_to_move.turn = chess.BLACK
    assert canonical_position(white_to_move) != canonical_position(black_to_move)
    assert canonical_position(_exchange_colors(white_to_move)) == canonical_position(
        white_to_move
    )


def test_clocks_and_move_history_do_not_change_identity() -> None:
    fresh = chess.Board("4k2r/8/8/8/8/8/8/R3K3 w - - 0 1")
    with_history = fresh.copy()
    for uci in ("e1d1", "e8d8", "d1e1", "d8e8"):
        with_history.push_uci(uci)
    assert with_history.board_fen() == fresh.board_fen()
    assert with_history.turn == fresh.turn
    assert len(with_history.move_stack) == 4
    assert canonical_position(with_history) == canonical_position(fresh)

    changed_clocks = fresh.copy()
    changed_clocks.halfmove_clock = 57
    changed_clocks.fullmove_number = 36
    assert canonical_position(changed_clocks) == canonical_position(fresh)


def test_material_is_part_of_identity() -> None:
    kings_only = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    with_rook = chess.Board("4k3/8/8/8/8/8/8/4K2R w - - 0 1")
    assert canonical_position(kings_only) != canonical_position(with_rook)


def test_rejects_positions_outside_protocol_domain() -> None:
    with_pawn = chess.Board()
    with_castling = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    with_ep = chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    chess960 = chess.Board.from_chess960_pos(0)
    for board in (with_pawn, with_castling, with_ep, chess960):
        with pytest.raises(ValueError):
            canonical_position(board)


def test_ownership_hash_serialization_known_vector() -> None:
    family = "KRvKR"
    key = "4k3/8/8/8/8/8/8/4K2R w"
    digest = bytes.fromhex(
        "4e69e8d11a9b8b5baa1a618de19058b5555ea0e43e5cbc50f1f72124fe3024da"
    )
    assert ownership_digest(family, key) == digest
    assert ownership_bucket(family, key) == 34
    assert ownership_bucket(family, key) == int.from_bytes(digest, "big") % 100
    assert ownership_split(family, key) == "pretraining"


@pytest.mark.parametrize(
    ("bucket", "expected"),
    [
        (0, "development"),
        (9, "development"),
        (10, "pretraining"),
        (54, "pretraining"),
        (55, "rl_starts"),
        (69, "rl_starts"),
        (70, "validation"),
        (79, "validation"),
        (80, "final_broad"),
        (89, "final_broad"),
        (90, "final_diagnostic"),
        (99, "final_diagnostic"),
    ],
)
def test_partition_boundaries(bucket: int, expected: str) -> None:
    assert split_for_bucket(bucket) == expected


@pytest.mark.parametrize("bucket", [-1, 100])
def test_partition_rejects_out_of_range_bucket(bucket: int) -> None:
    with pytest.raises(ValueError):
        split_for_bucket(bucket)


def test_named_seed_derivation_known_vector_and_validation() -> None:
    payload = b"protocol-v1|seed|101|initialization"
    expected = int.from_bytes(hashlib.sha256(payload).digest(), "big")
    assert derive_seed(101, "initialization") == expected
    assert derive_seed(101, "initialization") == int(
        "17296398f64d9fb51bf309270196e662ab0399517de394fc176d27daf640911a",
        16,
    )
    with pytest.raises(TypeError):
        derive_seed(True, "initialization")
    with pytest.raises(ValueError):
        derive_seed(101, "")


def test_named_rng_streams_are_reproducible_and_independent() -> None:
    first = make_rng(101, "starts")
    repeated = make_rng(101, "starts")
    independent = make_rng(101, "exploration")
    assert [first.getrandbits(64) for _ in range(8)] == [
        repeated.getrandbits(64) for _ in range(8)
    ]
    assert [make_rng(101, "starts").getrandbits(64) for _ in range(4)] != [
        independent.getrandbits(64) for _ in range(4)
    ]


def test_rng_helpers_do_not_mutate_global_random_state() -> None:
    original = random.getstate()
    random.seed(9182)
    expected = random.getstate()
    make_rng(101, "starts").random()
    derive_seed(202, "replay")
    actual = random.getstate()
    random.setstate(original)
    assert actual == expected
