"""Audit generated KRvKR partitions without examining held-out labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chess

from chesslab.endgames.identity import (
    canonical_position,
    ownership_bucket,
    ownership_split,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = {
    name: ROOT / "src" / "chesslab" / "endgames" / name
    for name in ("dataset.py", "identity.py", "reference.py")
}
ACQUISITION_DEFAULT = (
    ROOT / "experiments" / "manifests" / "syzygy-protocol-v1-acquisition.json"
)


@dataclass(frozen=True, slots=True)
class PartitionSpec:
    """Frozen v1 counts and manifest settings for one KRvKR partition."""

    name: str
    seed: int
    primary: int
    descendants: tuple[tuple[str, int], ...] = ()
    require_action_diversity: bool = False
    frozen_attained_allowed: bool = False

    @property
    def row_count(self) -> int:
        return self.primary + sum(count for _, count in self.descendants)

    @property
    def material_counts(self) -> dict[str, int]:
        return {"KRvKR": self.primary, **dict(self.descendants)}

    @property
    def targets_json(self) -> dict[str, object]:
        return {
            "primary": self.primary,
            "descendants": [[name, count] for name, count in self.descendants],
            "require_action_diversity": self.require_action_diversity,
        }


EXPECTED_PARTITIONS: tuple[PartitionSpec, ...] = (
    PartitionSpec("development", 1101, 2000),
    PartitionSpec("pretraining", 1102, 16000, (("KRvK", 4000),)),
    PartitionSpec("rl_starts", 1103, 2000),
    PartitionSpec("validation", 1104, 2000, (("KRvK", 500),)),
    PartitionSpec("final_broad", 1105, 2000),
    PartitionSpec("final_diagnostic", 1106, 1000, (), True, True),
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _source_hashes() -> dict[str, str]:
    return {name: _sha256_file(path) for name, path in SOURCE_FILES.items()}


def _material(board: chess.Board) -> str | None:
    if (
        len(board.pieces(chess.KING, chess.WHITE)) != 1
        or len(board.pieces(chess.KING, chess.BLACK)) != 1
        or board.pawns
        or board.queens
        or board.bishops
        or board.knights
    ):
        return None
    white_rooks = len(board.pieces(chess.ROOK, chess.WHITE))
    black_rooks = len(board.pieces(chess.ROOK, chess.BLACK))
    if white_rooks == black_rooks == 1:
        return "KRvKR"
    if white_rooks + black_rooks == 1:
        return "KRvK"
    return None


def _load_rows(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    payload = path.read_bytes()
    rows: list[dict[str, Any]] = []
    try:
        for line in payload.splitlines():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("row is not a JSON object")
            rows.append(row)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("partition JSONL is malformed") from exc
    return rows, payload


def _check_training_label(row: dict[str, Any]) -> None:
    """Check only train/validation label consistency; final data never enters."""

    reference = row.get("reference")
    label = row.get("label")
    if not isinstance(reference, dict):
        raise ValueError("training row lacks a reference object")
    value = reference.get("value")
    raw_wdl = reference.get("raw_wdl")
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value not in (-1, 0, 1)
        or not isinstance(raw_wdl, int)
        or isinstance(raw_wdl, bool)
        or raw_wdl not in (-2, -1, 0, 1, 2)
    ):
        raise ValueError("training reference label has an invalid value")
    if value != (raw_wdl > 0) - (raw_wdl < 0):
        raise ValueError("training reference value disagrees with raw WDL sign")
    if not isinstance(label, int) or isinstance(label, bool) or label != -value:
        raise ValueError("training label does not equal negative side-to-move value")


def audit_partitions(
    development_dir: Path,
    partitions_dir: Path,
    acquisition_manifest: Path,
    *,
    specifications: tuple[PartitionSpec, ...] = EXPECTED_PARTITIONS,
) -> dict[str, object]:
    """Audit manifests, source/data hashes, ownership and unique board keys.

    The JSON report intentionally contains no FENs, reference values, labels,
    or outcome distributions. It reports only structural counts and hashes.
    """

    failures: list[str] = []
    partition_reports: dict[str, object] = {}
    seen_keys: dict[str, str] = {}
    current_sources: dict[str, str] = {}
    common_acquisition_hashes: set[str] = set()
    actual_acquisition_hash: str | None = None
    try:
        current_sources = _source_hashes()
    except OSError:
        failures.append("current source files could not be hashed")
    try:
        actual_acquisition_hash = _sha256_file(acquisition_manifest)
    except OSError:
        failures.append("acquisition manifest could not be hashed")

    for spec in specifications:
        directory = development_dir if spec.name == "development" else partitions_dir
        stem = f"krvkr-{spec.name}"
        jsonl_path = directory / f"{stem}.jsonl"
        manifest_path = directory / f"{stem}.manifest.json"
        row_count = 0
        material_counts: Counter[str] = Counter()
        data_hash: str | None = None
        manifest_hash: str | None = None
        local_failures: list[str] = []
        try:
            manifest_bytes = manifest_path.read_bytes()
            manifest_hash = _sha256(manifest_bytes)
            manifest = json.loads(manifest_bytes)
            if not isinstance(manifest, dict):
                raise ValueError("partition manifest is not an object")
            if manifest.get("protocol") != "opponent-dependence-v1":
                local_failures.append("protocol mismatch")
            if (
                manifest.get("family") != "KRvKR"
                or manifest.get("partition") != spec.name
            ):
                local_failures.append("family or partition mismatch")

            status = manifest.get("status")
            frozen_count = manifest.get("frozen_attained_count")
            expected_status = status == "complete" and manifest.get("complete") is True
            frozen_status = (
                spec.frozen_attained_allowed
                and status == "frozen_attained"
                and manifest.get("complete") is False
                and isinstance(frozen_count, int)
                and not isinstance(frozen_count, bool)
                and frozen_count >= 200
                and manifest.get("row_count") == frozen_count
            )
            if not (expected_status or frozen_status):
                local_failures.append(
                    "status is neither complete nor permitted frozen-attained"
                )
            if manifest.get("seed") != spec.seed:
                local_failures.append("seed mismatch")
            if manifest.get("targets") != spec.targets_json:
                local_failures.append("targets mismatch")

            run_metadata = manifest.get("run_metadata")
            if not isinstance(run_metadata, dict):
                local_failures.append("run metadata missing")
            else:
                source_hashes = run_metadata.get("source_sha256")
                if not isinstance(source_hashes, dict):
                    local_failures.append("captured source hashes missing")
                else:
                    if current_sources and source_hashes != current_sources:
                        local_failures.append(
                            "captured source hashes differ from current sources"
                        )
                acquisition_hash = run_metadata.get("acquisition_manifest_sha256")
                if not isinstance(acquisition_hash, str):
                    local_failures.append("acquisition manifest hash missing")
                else:
                    common_acquisition_hashes.add(acquisition_hash)
                    if (
                        actual_acquisition_hash is not None
                        and acquisition_hash != actual_acquisition_hash
                    ):
                        local_failures.append("acquisition manifest hash mismatch")

            rows, data = _load_rows(jsonl_path)
            data_hash = _sha256(data)
            if manifest.get("jsonl_sha256") != data_hash:
                local_failures.append("JSONL SHA-256 mismatch")
            row_count = len(rows)
            if manifest.get("row_count") != row_count:
                local_failures.append("manifest row count mismatch")
            expected_count = frozen_count if frozen_status else spec.row_count
            if row_count != expected_count:
                local_failures.append("actual row count differs from protocol target")

            local_keys: set[str] = set()
            for row_index, row in enumerate(rows):
                try:
                    if row.get("family") != "KRvKR":
                        raise ValueError("family field mismatch")
                    fen = row.get("fen")
                    if not isinstance(fen, str):
                        raise ValueError("FEN missing")
                    try:
                        board = chess.Board(fen)
                    except ValueError as exc:
                        raise ValueError("invalid FEN") from exc
                    if (
                        not board.is_valid()
                        or board.chess960
                        or board.halfmove_clock != 0
                        or board.fullmove_number != 1
                        or board.move_stack
                        or board.castling_rights
                        or board.ep_square is not None
                        or board.outcome(claim_draw=True) is not None
                    ):
                        raise ValueError(
                            "position is invalid, terminal, or has nonzero "
                            "history/clocks"
                        )
                    material = _material(board)
                    if material is None or row.get("material") != material:
                        raise ValueError("material category mismatch")
                    material_counts[material] += 1
                    if material not in spec.material_counts:
                        raise ValueError("material category is not requested")

                    key = canonical_position(board)
                    if row.get("canonical_position") != key:
                        raise ValueError("canonical-position key mismatch")
                    if key in local_keys:
                        local_failures.append(
                            f"row {row_index}: duplicate canonical key within partition"
                        )
                    else:
                        local_keys.add(key)
                    previous = seen_keys.get(key)
                    if previous is not None:
                        if previous != spec.name:
                            local_failures.append(
                                f"row {row_index}: duplicate canonical key "
                                "across partitions"
                            )
                    else:
                        seen_keys[key] = spec.name

                    bucket = ownership_bucket("KRvKR", key)
                    if row.get("ownership_bucket") != bucket:
                        raise ValueError("ownership bucket mismatch")
                    if row.get("ownership_split") != spec.name:
                        raise ValueError("row ownership-split field mismatch")
                    if ownership_split("KRvKR", key) != spec.name:
                        raise ValueError("canonical key belongs to another partition")

                    if spec.name in ("pretraining", "validation"):
                        _check_training_label(row)
                except (ValueError, TypeError) as exc:
                    local_failures.append(f"row {row_index}: {exc}")
                except chess.InvalidMoveError:
                    local_failures.append(f"row {row_index}: invalid move encoding")

            expected_material_counts = (
                {"KRvKR": frozen_count} if frozen_status else spec.material_counts
            )
            if dict(material_counts) != expected_material_counts:
                local_failures.append("material-category counts differ from targets")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            local_failures.append(
                f"partition input unavailable or malformed: {type(exc).__name__}"
            )

        failures.extend(f"{spec.name}: {failure}" for failure in local_failures)
        partition_reports[spec.name] = {
            "status": "fail" if local_failures else "pass",
            "rows": row_count,
            "material_counts": dict(sorted(material_counts.items())),
            "manifest_sha256": manifest_hash,
            "jsonl_sha256": data_hash,
            "failures": local_failures,
        }

    if len(common_acquisition_hashes) != 1:
        failures.append(
            "partition manifests do not share one acquisition manifest hash"
        )
    common_hash = (
        next(iter(common_acquisition_hashes))
        if len(common_acquisition_hashes) == 1
        else None
    )
    report: dict[str, object] = {
        "status": "pass" if not failures else "fail",
        "family": "KRvKR",
        "partitions": partition_reports,
        "canonical_positions": len(seen_keys),
        "acquisition_manifest_sha256": common_hash,
        "current_source_sha256": current_sources,
        "failures": failures,
        "limitations": [
            "This audit checks start-board structure only; it does not establish "
            "disjointness of later game trajectories."
        ],
    }
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-dir", type=Path, required=True)
    parser.add_argument("--partitions-dir", type=Path, required=True)
    parser.add_argument(
        "--acquisition-manifest", type=Path, default=ACQUISITION_DEFAULT
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = audit_partitions(
        args.development_dir,
        args.partitions_dir,
        args.acquisition_manifest,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
