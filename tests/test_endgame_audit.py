"""Finite structural fixtures for the endgame partition audit."""

import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

import chess

from chesslab.endgames.identity import (
    canonical_position,
    ownership_bucket,
    ownership_split,
)

_AUDIT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "audit_endgame_partitions.py"
)
_SPEC = importlib.util.spec_from_file_location("audit_endgame_partitions", _AUDIT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)


def _board_for_split(split: str, seed: int = 17) -> chess.Board:
    rng = random.Random(seed)
    for _ in range(100_000):
        squares = rng.sample(list(chess.SQUARES), 4)
        board = chess.Board(None)
        for square, piece in zip(
            squares,
            (
                chess.Piece(chess.KING, chess.WHITE),
                chess.Piece(chess.KING, chess.BLACK),
                chess.Piece(chess.ROOK, chess.WHITE),
                chess.Piece(chess.ROOK, chess.BLACK),
            ),
            strict=True,
        ):
            board.set_piece_at(square, piece)
        board.turn = rng.choice((chess.WHITE, chess.BLACK))
        if board.is_valid() and board.outcome(claim_draw=True) is None:
            if ownership_split("KRvKR", canonical_position(board)) == split:
                return board
    raise AssertionError(f"could not find fixture for {split}")


def _source_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in audit.SOURCE_FILES.items()
    }


def _spec(name: str, count: int = 1) -> audit.PartitionSpec:
    seeds = {"development": 1101, "validation": 1104, "final_broad": 1105}
    return audit.PartitionSpec(name, seeds[name], count)


def _write_fixture(
    directory: Path,
    spec: audit.PartitionSpec,
    boards: list[chess.Board],
    acquisition_hash: str,
    *,
    final_poison: bool = False,
    training_labels: bool = False,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for board in boards:
        key = canonical_position(board)
        row: dict[str, object] = {
            "family": "KRvKR",
            "material": "KRvKR",
            "fen": board.fen(en_passant="fen"),
            "canonical_position": key,
            "ownership_bucket": ownership_bucket("KRvKR", key),
            "ownership_split": spec.name,
        }
        if training_labels:
            row["reference"] = {"value": 1, "raw_wdl": 2, "raw_dtz": 7}
            row["label"] = -1
        if final_poison:
            row["reference"] = {"value": "DO_NOT_READ_FINAL_VALUE"}
            row["label"] = "DO_NOT_READ_FINAL_LABEL"
        rows.append(row)
    stem = f"krvkr-{spec.name}"
    data = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in rows
    )
    (directory / f"{stem}.jsonl").write_bytes(data)
    manifest = {
        "protocol": "opponent-dependence-v1",
        "family": "KRvKR",
        "partition": spec.name,
        "seed": spec.seed,
        "targets": spec.targets_json,
        "row_count": len(rows),
        "complete": True,
        "status": "complete",
        "frozen_attained_count": None,
        "jsonl_sha256": hashlib.sha256(data).hexdigest(),
        "run_metadata": {
            "source_sha256": _source_hashes(),
            "acquisition_manifest_sha256": acquisition_hash,
        },
    }
    (directory / f"{stem}.manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def _audit(
    tmp_path: Path,
    specs: tuple[audit.PartitionSpec, ...],
) -> dict[str, object]:
    development = tmp_path / "development"
    partitions = tmp_path / "krvkr-partitions"
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_bytes(b"fixture acquisition manifest")
    acquisition_hash = hashlib.sha256(acquisition.read_bytes()).hexdigest()
    for spec in specs:
        directory = development if spec.name == "development" else partitions
        boards: list[chess.Board] = []
        keys: set[str] = set()
        attempt = 0
        while len(boards) < spec.primary:
            board = _board_for_split(spec.name, seed=100 + spec.seed + attempt)
            attempt += 1
            key = canonical_position(board)
            if key in keys:
                continue
            keys.add(key)
            boards.append(board)
        _write_fixture(
            directory,
            spec,
            boards,
            acquisition_hash,
            final_poison=spec.name.startswith("final_"),
            training_labels=spec.name in ("pretraining", "validation"),
        )
    return audit.audit_partitions(
        development,
        partitions,
        acquisition,
        specifications=specs,
    )


def test_audit_accepts_structural_fixtures_without_reading_final_labels(
    tmp_path: Path,
) -> None:
    specs = (_spec("development"), _spec("final_broad"))
    report = _audit(tmp_path, specs)

    assert report["status"] == "pass"
    assert "DO_NOT_READ_FINAL_LABEL" not in json.dumps(report)
    assert "DO_NOT_READ_FINAL_VALUE" not in json.dumps(report)
    assert "trajectories" in report["limitations"][0]  # type: ignore[index]


def test_audit_passes_unique_rows_and_checks_training_label_sign(
    tmp_path: Path,
) -> None:
    development_spec = _spec("development")
    validation_spec = _spec("validation")
    development = tmp_path / "development"
    partitions = tmp_path / "krvkr-partitions"
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_bytes(b"fixture")
    common_hash = hashlib.sha256(acquisition.read_bytes()).hexdigest()
    _write_fixture(
        development,
        development_spec,
        [_board_for_split("development", seed=1)],
        common_hash,
    )
    _write_fixture(
        partitions,
        validation_spec,
        [_board_for_split("validation", seed=2)],
        common_hash,
        training_labels=True,
    )

    report = audit.audit_partitions(
        development,
        partitions,
        acquisition,
        specifications=(development_spec, validation_spec),
    )

    assert report["status"] == "pass"
    assert report["canonical_positions"] == 2


def test_duplicate_is_detected_across_splits_and_ownership_mismatch(
    tmp_path: Path,
) -> None:
    development_spec = _spec("development")
    validation_spec = _spec("validation")
    development = tmp_path / "development"
    partitions = tmp_path / "krvkr-partitions"
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_bytes(b"fixture")
    common_hash = hashlib.sha256(acquisition.read_bytes()).hexdigest()
    board = _board_for_split("development", seed=91)
    _write_fixture(development, development_spec, [board], common_hash)
    _write_fixture(partitions, validation_spec, [board], common_hash)

    report = audit.audit_partitions(
        development,
        partitions,
        acquisition,
        specifications=(development_spec, validation_spec),
    )

    assert report["status"] == "fail"
    failures = json.dumps(report["failures"])
    assert "duplicate canonical key across partitions" in failures
    assert "canonical key belongs to another partition" in failures


def test_jsonl_tampering_and_source_hash_mismatch_fail(tmp_path: Path) -> None:
    spec = _spec("development")
    report = _audit(tmp_path, (spec,))
    assert report["status"] == "pass"

    manifest_path = tmp_path / "development" / "krvkr-development.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["run_metadata"]["source_sha256"]["dataset.py"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_report = audit.audit_partitions(
        tmp_path / "development",
        tmp_path / "krvkr-partitions",
        tmp_path / "acquisition.json",
        specifications=(spec,),
    )
    assert "captured source hashes differ from current sources" in json.dumps(
        source_report["failures"]
    )

    data_path = tmp_path / "development" / "krvkr-development.jsonl"
    data = data_path.read_bytes()
    data_path.write_bytes(data.replace(b'"family":"KRvKR"', b'"family" : "KRvKR"', 1))
    acquisition = tmp_path / "acquisition.json"
    second = audit.audit_partitions(
        tmp_path / "development",
        tmp_path / "krvkr-partitions",
        acquisition,
        specifications=(spec,),
    )
    assert "JSONL SHA-256 mismatch" in json.dumps(second["failures"])
