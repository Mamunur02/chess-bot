"""Reproducible board generation for opponent-dependence protocol v1.

Generation is explicit and local: callers provide a Syzygy probe, and every
partition is generated from its protocol seed with a private ``random.Random``.
The default command-line run creates development data for both study families
and reports the prespecified family screen; it does not generate final data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from platform import platform
from typing import Literal

import chess
import chess.syzygy

from chesslab.endgames.identity import (
    canonical_position,
    ownership_bucket,
    ownership_split,
)
from chesslab.endgames.reference import (
    ReferenceValue,
    SyzygyProbe,
    action_value,
    evaluate,
)

Family = Literal["KRvKR", "KQvKR"]
Partition = Literal[
    "development",
    "pretraining",
    "rl_starts",
    "validation",
    "final_broad",
    "final_diagnostic",
]

PROTOCOL_VERSION = "opponent-dependence-v1"
MAX_PROPOSALS_PER_PARTITION = 2_000_000
_FAMILIES: tuple[Family, ...] = ("KRvKR", "KQvKR")
_PARTITIONS: tuple[Partition, ...] = (
    "development",
    "pretraining",
    "rl_starts",
    "validation",
    "final_broad",
    "final_diagnostic",
)
_PARTITION_SEEDS: dict[Family, dict[Partition, int]] = {
    "KRvKR": {
        "development": 1101,
        "pretraining": 1102,
        "rl_starts": 1103,
        "validation": 1104,
        "final_broad": 1105,
        "final_diagnostic": 1106,
    },
    "KQvKR": {
        "development": 1201,
        "pretraining": 1202,
        "rl_starts": 1203,
        "validation": 1204,
        "final_broad": 1205,
        "final_diagnostic": 1206,
    },
}


@dataclass(frozen=True, slots=True)
class PartitionTargets:
    """Requested primary and descendant counts for one family partition."""

    primary: int
    descendants: tuple[tuple[str, int], ...] = ()
    require_action_diversity: bool = False

    def __post_init__(self) -> None:
        if self.primary < 0 or any(count < 0 for _, count in self.descendants):
            raise ValueError("partition targets must be non-negative")
        names = [name for name, _ in self.descendants]
        if len(names) != len(set(names)):
            raise ValueError("descendant material targets must be unique")


@dataclass(frozen=True, slots=True)
class ScreenResult:
    """Development-only family feasibility counts and pass decision."""

    sensitive_positions: int
    positions_with_worsening_move: int
    minimum_each: int

    @property
    def passes(self) -> bool:
        return (
            self.sensitive_positions >= self.minimum_each
            and self.positions_with_worsening_move >= self.minimum_each
        )


@dataclass(slots=True)
class GenerationResult:
    """Generated rows and auditable proposal/rejection metadata."""

    family: Family
    partition: Partition
    seed: int
    rows: list[dict[str, object]]
    targets: PartitionTargets
    proposals: int
    proposal_cap: int
    rejections: Counter[str] = field(default_factory=Counter)
    complete: bool = True
    frozen_attained_count: int | None = None
    sensitive_positions: int = 0
    positions_with_worsening_move: int = 0

    @property
    def screen(self) -> ScreenResult:
        return ScreenResult(
            self.sensitive_positions,
            self.positions_with_worsening_move,
            100,
        )


class GenerationLimitError(RuntimeError):
    """Raised when a required partition quota is not reached before its cap."""


def protocol_seed(family: Family, partition: Partition) -> int:
    """Return the fixed v1 proposal seed for a family and partition."""

    return _PARTITION_SEEDS[family][partition]


def default_targets(family: Family, partition: Partition) -> PartitionTargets:
    """Return the exact v1 quota for one family and partition."""

    if partition == "development":
        return PartitionTargets(primary=2_000)
    if partition == "pretraining":
        descendants = (
            (("KRvK", 4_000),)
            if family == "KRvKR"
            else (("KQvK", 2_000), ("KRvK", 2_000))
        )
        return PartitionTargets(primary=16_000, descendants=descendants)
    if partition == "rl_starts":
        return PartitionTargets(primary=2_000)
    if partition == "validation":
        descendants = (
            (("KRvK", 500),) if family == "KRvKR" else (("KQvK", 250), ("KRvK", 250))
        )
        return PartitionTargets(primary=2_000, descendants=descendants)
    if partition == "final_broad":
        return PartitionTargets(primary=2_000)
    if partition == "final_diagnostic":
        return PartitionTargets(primary=1_000, require_action_diversity=True)
    raise ValueError(f"unsupported partition: {partition}")


def _primary_piece_list(
    family: Family, queen_orientation: bool
) -> list[tuple[chess.Color, int]]:
    pieces = [(chess.WHITE, chess.KING), (chess.BLACK, chess.KING)]
    if family == "KRvKR":
        pieces.extend(((chess.WHITE, chess.ROOK), (chess.BLACK, chess.ROOK)))
    elif queen_orientation:
        pieces.extend(((chess.WHITE, chess.QUEEN), (chess.BLACK, chess.ROOK)))
    else:
        pieces.extend(((chess.WHITE, chess.ROOK), (chess.BLACK, chess.QUEEN)))
    return pieces


def _sample_primary(family: Family, rng: random.Random) -> chess.Board:
    """Uniformly assign each labelled primary piece to a distinct square."""

    queen_orientation = bool(rng.getrandbits(1))
    pieces = _primary_piece_list(family, queen_orientation)
    squares = rng.sample(list(chess.SQUARES), len(pieces))
    board = chess.Board(None)
    for (color, piece_type), square in zip(pieces, squares, strict=True):
        board.set_piece_at(square, chess.Piece(piece_type, color))
    board.turn = rng.choice((chess.WHITE, chess.BLACK))
    board.halfmove_clock = 0
    board.fullmove_number = 1
    return board


def _sample_descendant(
    family: Family,
    material: str,
    rng: random.Random,
) -> chess.Board:
    """Uniformly assign the labelled three-piece descendant material."""

    if material not in ("KRvK", "KQvK"):
        raise ValueError(f"unsupported descendant material: {material}")
    major_piece = chess.ROOK if material == "KRvK" else chess.QUEEN
    major_color = rng.choice((chess.WHITE, chess.BLACK))
    pieces = [
        (chess.WHITE, chess.KING),
        (chess.BLACK, chess.KING),
        (major_color, major_piece),
    ]
    squares = rng.sample(list(chess.SQUARES), len(pieces))
    board = chess.Board(None)
    for (color, piece_type), square in zip(pieces, squares, strict=True):
        board.set_piece_at(square, chess.Piece(piece_type, color))
    board.turn = rng.choice((chess.WHITE, chess.BLACK))
    board.halfmove_clock = 0
    board.fullmove_number = 1
    return board


def _is_valid_nonterminal(board: chess.Board) -> tuple[bool, str | None]:
    if not board.is_valid():
        return False, "invalid"
    if board.outcome(claim_draw=True) is not None:
        return False, "terminal"
    return True, None


def _q_values(board: chess.Board, tablebase: SyzygyProbe) -> tuple[int, ...]:
    return tuple(action_value(board, move, tablebase) for move in board.legal_moves)


def generate_partition(
    family: Family,
    partition: Partition,
    tablebase: SyzygyProbe,
    *,
    targets: PartitionTargets | None = None,
    seed: int | None = None,
    proposal_cap: int = MAX_PROPOSALS_PER_PARTITION,
) -> GenerationResult:
    """Generate one ownership partition with deterministic local randomness.

    Descendants are independently sampled by uniformly assigning their
    labelled kings and surviving major piece to distinct squares. Ownership is
    always hashed with the study family (``KRvKR`` or ``KQvKR``), including
    for three-piece descendants.
    """

    if family not in _FAMILIES or partition not in _PARTITIONS:
        raise ValueError("unsupported family or partition")
    if proposal_cap <= 0:
        raise ValueError("proposal_cap must be positive")
    target = targets if targets is not None else default_targets(family, partition)
    allowed_descendants = {"KRvK"} if family == "KRvKR" else {"KRvK", "KQvK"}
    if any(name not in allowed_descendants for name, _ in target.descendants):
        raise ValueError(f"descendant material is unsupported for {family}")
    generation_seed = protocol_seed(family, partition) if seed is None else seed
    rng = random.Random(generation_seed)
    result = GenerationResult(
        family=family,
        partition=partition,
        seed=generation_seed,
        rows=[],
        targets=target,
        proposals=0,
        proposal_cap=proposal_cap,
    )
    seen: set[str] = set()
    requests = [("primary", target.primary), *target.descendants]
    counts: Counter[str] = Counter()

    for material, requested in requests:
        while counts[material] < requested and result.proposals < proposal_cap:
            result.proposals += 1
            if material == "primary":
                board = _sample_primary(family, rng)
            else:
                board = _sample_descendant(family, material, rng)

            valid, reason = _is_valid_nonterminal(board)
            if not valid:
                result.rejections[reason or "invalid"] += 1
                continue
            key = canonical_position(board)
            bucket = ownership_bucket(family, key)
            if ownership_split(family, key) != partition:
                result.rejections["wrong_partition"] += 1
                continue
            if key in seen:
                result.rejections["duplicate"] += 1
                continue

            reference: ReferenceValue | None = None
            q_values: tuple[int, ...] | None = None
            if partition == "development" or partition in (
                "pretraining",
                "validation",
                "final_broad",
                "final_diagnostic",
            ):
                reference = evaluate(board, tablebase)
            if target.require_action_diversity or partition == "development":
                q_values = _q_values(board, tablebase)
                if len(set(q_values)) > 1:
                    if partition == "development":
                        result.sensitive_positions += 1
                else:
                    if target.require_action_diversity:
                        result.rejections["insufficient_action_diversity"] += 1
                        continue
            if (
                partition == "development"
                and reference is not None
                and q_values is not None
            ):
                best_q = max(q_values)
                if any(q_value < best_q for q_value in q_values):
                    result.positions_with_worsening_move += 1

            row: dict[str, object] = {
                "family": family,
                "material": family if material == "primary" else material,
                "fen": board.fen(en_passant="fen"),
                "canonical_position": key,
                "ownership_bucket": bucket,
                "ownership_split": partition,
            }
            if reference is not None and partition in (
                "pretraining",
                "validation",
                "final_broad",
                "final_diagnostic",
            ):
                row["reference"] = {
                    "value": reference.value,
                    "raw_wdl": reference.raw_wdl,
                    "raw_dtz": reference.raw_dtz,
                }
            if reference is not None and partition in ("pretraining", "validation"):
                row["label"] = -reference.value
            result.rows.append(row)
            counts[material] += 1
            seen.add(key)

    result.complete = all(counts[name] >= requested for name, requested in requests)
    if not result.complete:
        if partition == "final_diagnostic" and len(result.rows) >= 200:
            # The protocol freezes the attained diagnostic set at 200 or more.
            result.frozen_attained_count = len(result.rows)
        else:
            summary = ", ".join(
                f"{name}={counts[name]}/{requested}" for name, requested in requests
            )
            raise GenerationLimitError(
                f"proposal cap {proposal_cap} reached for {family}/{partition}: "
                f"{summary}; proposals={result.proposals}"
            )
    return result


def screen_family(
    sensitive_positions: int,
    positions_with_worsening_move: int,
    *,
    minimum_each: int = 100,
) -> ScreenResult:
    """Apply the prespecified development-only feasibility threshold."""

    if min(sensitive_positions, positions_with_worsening_move, minimum_each) < 0:
        raise ValueError("screen counts and threshold must be non-negative")
    return ScreenResult(
        sensitive_positions,
        positions_with_worsening_move,
        minimum_each,
    )


def write_partition(
    result: GenerationResult,
    output_dir: Path,
    *,
    run_metadata: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    """Write canonical JSONL rows and a manifest with hashes and run settings."""

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{result.family.lower()}-{result.partition}"
    data_path = output_dir / f"{stem}.jsonl"
    manifest_path = output_dir / f"{stem}.manifest.json"
    if data_path.exists() or manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite dataset output for {stem}")
    encoded_rows = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
        for row in result.rows
    ).encode("utf-8")
    with data_path.open("xb") as stream:
        stream.write(encoded_rows)
    manifest: dict[str, object] = {
        "protocol": PROTOCOL_VERSION,
        "family": result.family,
        "partition": result.partition,
        "seed": result.seed,
        "targets": asdict(result.targets),
        "row_count": len(result.rows),
        "complete": result.complete,
        "status": "complete" if result.complete else "frozen_attained",
        "frozen_attained_count": result.frozen_attained_count,
        "proposals": result.proposals,
        "proposal_cap": result.proposal_cap,
        "rejections": dict(sorted(result.rejections.items())),
        "sensitive_positions": result.sensitive_positions,
        "positions_with_worsening_move": result.positions_with_worsening_move,
        "jsonl_sha256": hashlib.sha256(encoded_rows).hexdigest(),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "run_metadata": run_metadata or {},
    }
    if result.partition == "development":
        manifest["family_screen"] = asdict(result.screen)
        manifest["family_screen_passes"] = result.screen.passes
    with manifest_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return data_path, manifest_path


def _expected_table_names() -> set[str]:
    return {
        f"{family}.{extension}"
        for family in ("KRvKR", "KQvKR", "KRvK", "KQvK")
        for extension in ("rtbw", "rtbz")
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_acquisition_manifest(
    manifest_path: Path,
    tablebase_dir: Path,
) -> dict[str, object]:
    """Require a complete acquisition manifest and verify all eight local files."""

    payload = manifest_path.read_bytes()
    try:
        manifest = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("acquisition manifest is not valid JSON") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("status") != "complete"
        or manifest.get("protocol") != "opponent-dependence-protocol-v1"
        or not manifest.get("completed_at_utc")
    ):
        raise ValueError("acquisition manifest must have status 'complete'")
    tables = manifest.get("tables")
    if not isinstance(tables, dict) or set(tables) != _expected_table_names():
        raise ValueError(
            "acquisition manifest must list exactly the eight protocol tables"
        )
    table_hashes: dict[str, str] = {}
    for name in sorted(_expected_table_names()):
        record = tables[name]
        if not isinstance(record, dict) or record.get("verification") != "passed":
            raise ValueError(f"acquisition table is not verified: {name}")
        expected_hash = record.get("local_sha256")
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(
                character not in "0123456789abcdefABCDEF" for character in expected_hash
            )
        ):
            raise ValueError(f"acquisition table lacks a SHA-256: {name}")
        table_path = tablebase_dir / name
        if not table_path.is_file():
            raise ValueError(f"required table is missing: {table_path}")
        actual_hash = _sha256_file(table_path)
        if actual_hash.lower() != expected_hash.lower():
            raise ValueError(f"local table SHA-256 mismatch: {name}")
        byte_count = record.get("bytes")
        if isinstance(byte_count, int) and table_path.stat().st_size != byte_count:
            raise ValueError(f"local table byte count mismatch: {name}")
        table_hashes[name] = actual_hash
    return {
        "acquisition_manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "table_sha256": table_hashes,
    }


def _git_provenance() -> dict[str, object]:
    """Capture local Git commit and tracked/untracked worktree state when available."""

    root = Path.cwd().resolve()
    safe_directory = f"safe.directory={root.as_posix()}"
    try:
        commit = subprocess.run(
            ["git", "-c", safe_directory, "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            [
                "git",
                "-c",
                safe_directory,
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "git_worktree_clean": None}
    return {"git_commit": commit, "git_worktree_clean": not bool(status.strip())}


def _run_provenance(
    acquisition: dict[str, object],
    proposal_cap: int,
    tablebase_dir: Path,
) -> dict[str, object]:
    source_paths = {
        "dataset.py": Path(__file__),
        "identity.py": Path(__file__).with_name("identity.py"),
        "reference.py": Path(__file__).with_name("reference.py"),
    }
    return {
        **acquisition,
        **_git_provenance(),
        "proposal_cap": proposal_cap,
        "tablebase_directory": str(tablebase_dir.resolve()),
        "python_version": sys.version.split()[0],
        "python_chess_version": chess.__version__,
        "platform": platform(),
        "dataset_module_version": PROTOCOL_VERSION,
        "source_sha256": {
            name: _sha256_file(path) for name, path in source_paths.items()
        },
    }


def _write_failure_record(
    output_dir: Path,
    *,
    families: tuple[Family, ...],
    partition: Partition,
    proposal_cap: int,
    status: str,
    error: str,
    run_metadata: dict[str, object] | None,
) -> Path:
    """Persist a fresh failure/interruption record without replacing prior runs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    path = output_dir / f"{status}-{run_id}.manifest.json"
    value: dict[str, object] = {
        "protocol": PROTOCOL_VERSION,
        "status": status,
        "families": list(families),
        "partition": partition,
        "seeds": {family: protocol_seed(family, partition) for family in families},
        "proposal_cap": proposal_cap,
        "error": error,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "run_metadata": run_metadata
        or {
            **_git_provenance(),
            "python_version": sys.version.split()[0],
            "python_chess_version": chess.__version__,
            "platform": platform(),
            "source_sha256": {
                name: _sha256_file(Path(__file__).with_name(name))
                for name in ("dataset.py", "identity.py", "reference.py")
            },
        },
    }
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tablebase-dir",
        type=Path,
        required=True,
        help="directory containing the required local Syzygy WDL/DTZ tables",
    )
    parser.add_argument(
        "--acquisition-manifest",
        type=Path,
        required=True,
        help="completed manifest produced by chesslab.endgames.acquisition",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/opponent-dependence-v1/datasets"),
    )
    parser.add_argument(
        "--family",
        choices=("both", *_FAMILIES),
        default="both",
        help="default: generate and screen both families",
    )
    parser.add_argument(
        "--partition",
        choices=_PARTITIONS,
        default="development",
        help="default is development; final partitions require explicit selection",
    )
    parser.add_argument("--proposal-cap", type=int, default=MAX_PROPOSALS_PER_PARTITION)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Generate selected datasets through the local Syzygy tablebase."""

    args = _parse_args(argv)
    families: tuple[Family, ...] = (
        _FAMILIES if args.family == "both" else (args.family,)
    )
    generated: dict[Family, GenerationResult] = {}
    provenance: dict[str, object] | None = None
    try:
        acquisition = verify_acquisition_manifest(
            args.acquisition_manifest,
            args.tablebase_dir,
        )
        provenance = _run_provenance(
            acquisition,
            args.proposal_cap,
            args.tablebase_dir,
        )
        with chess.syzygy.open_tablebase(str(args.tablebase_dir)) as tablebase:
            for family in families:
                result = generate_partition(
                    family,
                    args.partition,
                    tablebase,
                    proposal_cap=args.proposal_cap,
                )
                write_partition(result, args.output_dir, run_metadata=provenance)
                generated[family] = result
    except KeyboardInterrupt:
        record = _write_failure_record(
            args.output_dir,
            families=families,
            partition=args.partition,
            proposal_cap=args.proposal_cap,
            status="interrupted",
            error="KeyboardInterrupt",
            run_metadata=provenance,
        )
        print(f"dataset generation interrupted; record: {record}", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, ValueError) as exc:
        record = _write_failure_record(
            args.output_dir,
            families=families,
            partition=args.partition,
            proposal_cap=args.proposal_cap,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
            run_metadata=provenance,
        )
        print(f"dataset generation failed: {exc}; record: {record}", file=sys.stderr)
        return 2

    for family, result in generated.items():
        if not result.complete:
            print(
                f"{family}/{result.partition}: diagnostic target not reached; "
                f"froze protocol-permitted attained size {len(result.rows)}"
            )

    if args.partition == "development" and len(generated) == 2:
        for family, result in generated.items():
            print(
                f"{family}: sensitive={result.sensitive_positions}, "
                f"worsening={result.positions_with_worsening_move}, "
                f"passes={result.screen.passes}"
            )
        preferred = (
            "KRvKR"
            if generated["KRvKR"].screen.passes
            else ("KQvKR" if generated["KQvKR"].screen.passes else None)
        )
        print(f"prespecified family preference: {preferred or 'neither passes'}")
        if preferred is None:
            _write_failure_record(
                args.output_dir,
                families=families,
                partition=args.partition,
                proposal_cap=args.proposal_cap,
                status="infeasible_screen",
                error=(
                    "neither KRvKR nor KQvKR met both prespecified "
                    "development thresholds"
                ),
                run_metadata=provenance,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
