"""Opt-in checks against the acquired reference, never required by default."""

import hashlib
import json
import os
from pathlib import Path

import chess
import chess.syzygy
import pytest

from chesslab.endgames.reference import action_value, evaluate

pytestmark = pytest.mark.integration


def test_verified_tables_and_bellman_consistency() -> None:
    location = os.environ.get("CHESSLAB_SYZYGY_DIRECTORY")
    if location is None:
        pytest.skip("set CHESSLAB_SYZYGY_DIRECTORY to verified local tables")
    directory = Path(location)
    manifest = json.loads(
        Path("experiments/manifests/syzygy-protocol-v1-acquisition.json").read_text()
    )
    assert manifest["status"] == "complete"
    for name, facts in manifest["tables"].items():
        payload = (directory / name).read_bytes()
        assert len(payload) == facts["bytes"]
        assert hashlib.sha256(payload).hexdigest() == facts["publisher_sha256"]
        # Generator print_checksum serializes the final 16 bytes in byte order.
        source = "wdl345_checksums" if name.endswith("rtbw") else "dtz345_checksums"
        published = dict(
            line.split(": ")
            for line in (directory / source).read_text().splitlines()
        )
        assert len(payload) % 64 == 16
        assert payload[-16:].hex() == published[name]

    fens = (
        "7k/8/8/8/8/8/8/KR6 w - - 0 1",
        "7k/8/8/8/8/8/8/KQ6 w - - 0 1",
        "1r5k/8/8/8/8/8/8/KQ6 w - - 0 1",
        "1r5k/8/8/8/8/8/8/KR6 w - - 0 1",
        "7k/8/8/8/8/8/1r6/KR6 w - - 0 1",
    )
    with chess.syzygy.open_tablebase(str(directory)) as tables:
        for fen in fens:
            board = chess.Board(fen)
            for position in (board, board.mirror()):
                assert position.is_valid()
                value = evaluate(position, tables).value
                assert value == max(
                    action_value(position, move, tables)
                    for move in position.legal_moves
                )
                clock_claim = position.copy()
                clock_claim.halfmove_clock = 150
                assert evaluate(clock_claim, tables).value == value
        assert evaluate(chess.Board(fens[0]), tables).value == 1
        assert evaluate(chess.Board(fens[1]), tables).value == 1
