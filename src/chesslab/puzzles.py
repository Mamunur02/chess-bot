"""Prepare a bounded, reproducible Lichess puzzle sample from a local CSV.

Sampling scans the entire snapshot before validating the reservoir. Selection
is independent of engine performance. Keep generated data outside Git.
"""

import argparse
import csv
import hashlib
import json
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import chess

from chesslab.eval.artifacts import (
    capture_run_metadata,
    configuration_digest,
    write_artifact_json,
)

REQUIRED_FIELDS = {"PuzzleId", "FEN", "Moves", "GameUrl", "Rating", "Themes"}
SOURCE = "https://database.lichess.org/lichess_db_puzzle.csv.zst"


@dataclass(frozen=True)
class PreparedPuzzle:
    """Validated solver position, labels, source row and conservative group keys."""

    puzzle_id: str
    game_id: str
    fen: str
    position_key: str
    expected_moves: tuple[str, ...]
    source_row: Mapping[str, str]

    def to_dict(self) -> dict[str, object]:
        """Keep original metadata alongside the normalized benchmark position."""
        return {
            "name": self.puzzle_id,
            "game_id": self.game_id,
            "fen": self.fen,
            "position_key": self.position_key,
            "expected_moves": list(self.expected_moves),
            "source_row": dict(self.source_row),
        }


def prepare_puzzle(row: Mapping[str, str]) -> PreparedPuzzle:
    """Apply the setup ply, validate the full line, and accept all mate-in-ones.

    Earlier repetition history cannot be reconstructed from the source FEN.
    Equivalent-position keys deliberately omit clocks for conservative grouping.
    """
    if not REQUIRED_FIELDS <= row.keys():
        raise ValueError("missing required puzzle fields")
    puzzle_id = row["PuzzleId"]
    if not re.fullmatch(r"[A-Za-z0-9]+", puzzle_id):
        raise ValueError("invalid puzzle ID")
    url = urlparse(row["GameUrl"])
    game_id = url.path.strip("/").split("/")[0]
    if (
        url.scheme != "https"
        or url.netloc != "lichess.org"
        or not re.fullmatch(r"[A-Za-z0-9]{8}", game_id)
    ):
        raise ValueError("invalid source game URL")
    int(row["Rating"])
    if len(row["FEN"].split()) != 6:
        raise ValueError("source FEN must contain six fields")
    board = chess.Board(row["FEN"])
    if not board.is_valid():
        raise ValueError("invalid source board")
    moves = row["Moves"].split()
    if len(moves) < 2:
        raise ValueError("setup and solution moves are required")
    solver_board: chess.Board | None = None
    for index, uci in enumerate(moves):
        move = chess.Move.from_uci(uci)
        if board.is_game_over(claim_draw=False) or move not in board.legal_moves:
            raise ValueError(f"illegal solution line at ply {index}: {uci}")
        board.push(move)
        if index == 0:
            solver_board = board.copy(stack=False)
    assert solver_board is not None
    mates: list[str] = []
    for move in solver_board.legal_moves:
        child = solver_board.copy(stack=False)
        child.push(move)
        if child.is_checkmate():
            mates.append(move.uci())
    if mates and moves[1] not in mates:
        raise ValueError("listed solution misses an available immediate mate")
    if "mateIn1" in row["Themes"].split() and not mates:
        raise ValueError("mateIn1 label has no immediate mate")
    return PreparedPuzzle(
        puzzle_id=puzzle_id,
        game_id=game_id,
        fen=solver_board.fen(en_passant="fen"),
        position_key=" ".join(solver_board.fen().split()[:4]),
        expected_moves=tuple(sorted(mates)) if mates else (moves[1],),
        source_row=dict(row),
    )


def sample_rows(
    rows: Iterable[dict[str, str]], size: int, rng: random.Random
) -> tuple[list[dict[str, str]], int]:
    """Uniform reservoir of source rows using only caller-owned randomness."""
    if type(size) is not int or size <= 0:
        raise ValueError("reservoir size must be a positive integer")
    reservoir: list[dict[str, str]] = []
    count = 0
    for count, row in enumerate(rows, start=1):
        if count <= size:
            reservoir.append(row)
        else:
            index = rng.randrange(count)
            if index < size:
                reservoir[index] = row
    return reservoir, count


def independent_puzzles(puzzles: Sequence[PreparedPuzzle]) -> list[PreparedPuzzle]:
    """Choose one representative per connected game/position/ID component.

    Connecting both keys before selection prevents indirect duplicate chains
    crossing splits. Representatives and output order are stable by puzzle ID.
    """
    parents = list(range(len(puzzles)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    seen: dict[tuple[str, str], int] = {}
    for index, puzzle in enumerate(puzzles):
        for key in (
            ("game", puzzle.game_id),
            ("position", puzzle.position_key),
            ("id", puzzle.puzzle_id),
        ):
            if key in seen:
                parents[root(index)] = root(seen[key])
            seen[key] = index
    groups: dict[int, list[PreparedPuzzle]] = {}
    for index, puzzle in enumerate(puzzles):
        groups.setdefault(root(index), []).append(puzzle)
    return sorted(
        (min(group, key=lambda p: p.puzzle_id) for group in groups.values()),
        key=lambda p: p.puzzle_id,
    )


def prepare_dataset(
    source: Path,
    output: Path,
    *,
    seed: int = 20261017,
    pool_size: int = 1200,
    counts: tuple[int, int, int] = (50, 50, 200),
    repository: Path = Path.cwd(),
) -> dict[str, object]:
    """Write disjoint development/validation/test data to a fresh directory.

    Counts are exact because each retained position belongs to a different
    connected component. Validation failures and deduplication alter the source
    row distribution; this is not a uniform sample of all valid puzzles.
    """
    if any(type(n) is not int or n <= 0 for n in counts):
        raise ValueError("split counts must be positive integers")
    if pool_size < sum(counts):
        raise ValueError("reservoir must cover requested split counts")
    if output.exists():
        raise FileExistsError(output)
    with source.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    rng = random.Random(seed)
    with source.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if fields is None or not REQUIRED_FIELDS <= set(fields):
            raise ValueError("CSV header lacks required fields")
        rows, total = sample_rows(reader, pool_size, rng)
    valid: list[PreparedPuzzle] = []
    rejected: list[dict[str, str]] = []
    for row in rows:
        try:
            if any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in row.items()
            ):
                raise ValueError("malformed CSV row")
            valid.append(prepare_puzzle(row))
        except ValueError as error:
            rejected.append({"id": row.get("PuzzleId", ""), "error": str(error)})
    candidates = independent_puzzles(valid)
    if len(candidates) < sum(counts):
        raise ValueError("insufficient independent valid puzzles; enlarge reservoir")
    rng.shuffle(candidates)
    output.mkdir(parents=True, exist_ok=False)
    split_hashes: dict[str, str] = {}
    start = 0
    for split, count in zip(("development", "validation", "test"), counts, strict=True):
        data = [p.to_dict() for p in candidates[start : start + count]]
        destination = output / f"{split}.json"
        write_artifact_json(destination, data)
        split_hashes[split] = hashlib.sha256(destination.read_bytes()).hexdigest()
        start += count
    manifest: dict[str, object] = {
        "schema_version": 1,
        "preparation_version": "lichess-reservoir-components-v1",
        "source_url": SOURCE,
        "license": "CC0-1.0",
        "source_csv_sha256": source_hash,
        "source_fields": fields,
        "source_rows": total,
        "seed": seed,
        "reservoir_requested": pool_size,
        "reservoir_actual": len(rows),
        "valid_rows": len(valid),
        "rejected": rejected,
        "independent_components": len(candidates),
        "split_counts": dict(zip(("development", "validation", "test"), counts)),
        "split_sha256": split_hashes,
        "selection": "Uniform source-row reservoir, validate, one per connected "
        "game/position/ID group, shuffle, take disjoint splits; no rating filter.",
        "history": "Reconstructed from source FEN; pre-FEN repetition unavailable.",
    }
    write_artifact_json(output / "manifest.json", manifest)
    metadata = capture_run_metadata(
        repository, output.name, configuration_digest(manifest), 3
    )
    metadata.update(status="completed", runs_written=3)
    write_artifact_json(output / "provenance.json", metadata)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    """Prepare a local CSV without network or external-engine dependencies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--pool-size", type=int, default=1200)
    args = parser.parse_args(argv)
    try:
        manifest = prepare_dataset(
            args.source, args.output, seed=args.seed, pool_size=args.pool_size
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
