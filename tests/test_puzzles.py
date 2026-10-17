import csv
import json
import random
from dataclasses import replace
from pathlib import Path

import chess
import pytest

from chesslab.puzzles import (
    independent_puzzles,
    prepare_dataset,
    prepare_puzzle,
    sample_rows,
)


def source_row() -> dict[str, str]:
    return {
        "PuzzleId": "example",
        "FEN": "q3k1nr/1pp1nQpp/3p4/1P2p3/4P3/B1PP1b2/B5PP/5K2 b k - 0 17",
        "Moves": "e8d7 a2e6 d7d8 f7f8",
        "Rating": "1760",
        "Themes": "mate mateIn2 middlegame short",
        "GameUrl": "https://lichess.org/yyznGmXs/black#34",
    }


def test_setup_ply_and_entire_solution_are_validated() -> None:
    row = source_row()
    prepared = prepare_puzzle(row)
    board = chess.Board(row["FEN"])
    board.push_uci("e8d7")
    assert prepared.fen == board.fen(en_passant="fen")
    assert prepared.expected_moves == ("a2e6",)
    assert prepared.game_id == "yyznGmXs"
    assert prepared.source_row == row
    assert board.turn == chess.WHITE
    row["Moves"] += " a1a8"
    with pytest.raises(ValueError, match="illegal solution line"):
        prepare_puzzle(row)


def test_black_solver_and_game_url_normalization() -> None:
    row = source_row()
    row.update(
        {
            "FEN": "r3r1k1/p4ppp/2p2n2/1p6/3P1qb1/2NQR3/PPB2PP1/R1B3K1 w - - 5 18",
            "Moves": "e3g3 e8e1 g1h2 e1c1 a1c1 f4h6 h2g1 h6c1",
            "GameUrl": "https://lichess.org/gyFeQsOE#35",
        }
    )
    prepared = prepare_puzzle(row)
    assert chess.Board(prepared.fen).turn == chess.BLACK
    assert prepared.expected_moves == ("e8e1",)
    assert prepared.game_id == "gyFeQsOE"


def test_all_immediate_mates_are_accepted() -> None:
    row = source_row()
    row.update(
        {
            "FEN": "6k1/5Q2/6K1/8/8/8/8/8 b - - 0 1",
            "Moves": "g8h8 f7g7",
            "Themes": "mateIn1",
        }
    )
    prepared = prepare_puzzle(row)
    board = chess.Board(prepared.fen)
    mates = []
    for move in board.legal_moves:
        child = board.copy()
        child.push(move)
        if child.is_checkmate():
            mates.append(move.uci())
    assert set(prepared.expected_moves) == set(mates)
    assert len(mates) == 4
    assert "f7g7" in prepared.expected_moves


@pytest.mark.parametrize(
    "field,value",
    [
        ("Moves", "e8d7"),
        ("Moves", "e8e1 a2e6"),
        ("FEN", "8/8/8/8/8/8/8/8 w - - 0 1"),
        ("GameUrl", "https://example.org/yyznGmXs"),
        ("Themes", "mateIn1"),
        ("Rating", "not-a-rating"),
        ("PuzzleId", "../escape"),
    ],
)
def test_bad_rows_fail_explicitly(field: str, value: str) -> None:
    row = source_row()
    row[field] = value
    with pytest.raises(ValueError):
        prepare_puzzle(row)


def test_components_join_indirect_duplicate_chains() -> None:
    a = prepare_puzzle(source_row())
    b = replace(a, puzzle_id="b", position_key="other")
    c = replace(b, puzzle_id="c", game_id="othergame")
    d = replace(a, puzzle_id="d", game_id="distinct", position_key="distinct")
    assert len(independent_puzzles([a, b, c, d])) == 2
    assert independent_puzzles([d, c, b, a]) == independent_puzzles([a, b, c, d])


def test_reservoir_scans_all_rows_and_repeats_with_explicit_rng() -> None:
    rows = [{"id": str(n)} for n in range(100)]
    a, count = sample_rows(iter(rows), 10, random.Random(17))
    b, _ = sample_rows(iter(rows), 10, random.Random(17))
    assert count == 100
    assert a == b
    assert len(a) == 10
    assert any(int(row["id"]) > 9 for row in a)
    assert sample_rows(rows[:3], 10, random.Random(17))[0] == rows[:3]
    with pytest.raises(ValueError):
        sample_rows(rows, 0, random.Random(17))


def write_csv(path: Path) -> None:
    row = source_row()
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        for index, moves in enumerate(("e2e4 e7e5", "d2d4 d7d5", "c2c4 e7e5")):
            row.update(
                {
                    "PuzzleId": str(index),
                    "GameUrl": f"https://lichess.org/game000{index}",
                    "FEN": chess.STARTING_FEN,
                    "Moves": moves,
                    "Themes": "opening",
                }
            )
            writer.writerow(row)
        row["PuzzleId"] = "bad"
        row["Moves"] = "bad move"
        writer.writerow(row)


def test_dataset_splits_hashes_rejections_and_no_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    write_csv(source)
    first, second = tmp_path / "one", tmp_path / "two"
    manifest = prepare_dataset(source, first, pool_size=4, counts=(1, 1, 1))
    repeated = prepare_dataset(source, second, pool_size=4, counts=(1, 1, 1))
    assert manifest == repeated
    assert manifest["source_rows"] == 4
    assert manifest["valid_rows"] == 3
    assert len(manifest["rejected"]) == 1  # type: ignore[arg-type]
    games, positions = set(), set()
    for split in ("development", "validation", "test"):
        assert (first / f"{split}.json").read_bytes() == (
            second / f"{split}.json"
        ).read_bytes()
        puzzle = json.loads((first / f"{split}.json").read_text())[0]
        assert puzzle["game_id"] not in games
        assert puzzle["position_key"] not in positions
        games.add(puzzle["game_id"])
        positions.add(puzzle["position_key"])
    with pytest.raises(FileExistsError):
        prepare_dataset(source, first, pool_size=4, counts=(1, 1, 1))
    with pytest.raises(ValueError, match="insufficient independent"):
        prepare_dataset(source, tmp_path / "too-big", pool_size=6, counts=(2, 2, 2))


def test_missing_header_rejected_before_output(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("PuzzleId,FEN\na,b\n")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="header"):
        prepare_dataset(source, output)
    assert not output.exists()
