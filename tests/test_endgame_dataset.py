"""Focused tests for opponent-dependence v1 board generation."""

import hashlib
import json
import random
from pathlib import Path

import chess
import pytest

import chesslab.endgames.dataset as dataset
from chesslab.endgames.identity import canonical_position, ownership_split


class PositionTablebase:
    """Deterministic in-memory Syzygy substitute for generator unit tests."""

    def probe_wdl(self, board: chess.Board) -> int:
        encoded = sum(
            (square + 1) * piece.piece_type * (1 if piece.color else 3)
            for square, piece in board.piece_map().items()
        ) + (17 if board.turn else 31)
        return encoded % 5 - 2

    def probe_dtz(self, board: chess.Board) -> int:
        return sum(board.piece_map()) % 37


def _board_for_split(family: str, split: str, seed: int = 1) -> chess.Board:
    rng = random.Random(seed)
    for _ in range(100_000):
        board = dataset._sample_primary(family, rng)  # type: ignore[arg-type]
        if board.is_valid() and board.outcome(claim_draw=True) is None:
            if ownership_split(family, canonical_position(board)) == split:
                return board
    raise AssertionError("could not find test position for requested split")


def test_protocol_targets_and_seeds_match_v1() -> None:
    assert dataset.protocol_seed("KRvKR", "development") == 1101
    assert dataset.protocol_seed("KQvKR", "final_diagnostic") == 1206
    assert dataset.default_targets("KRvKR", "pretraining") == dataset.PartitionTargets(
        16_000, (("KRvK", 4_000),)
    )
    assert dataset.default_targets("KQvKR", "pretraining") == dataset.PartitionTargets(
        16_000, (("KQvK", 2_000), ("KRvK", 2_000))
    )
    assert dataset.default_targets("KQvKR", "validation") == dataset.PartitionTargets(
        2_000, (("KQvK", 250), ("KRvK", 250))
    )
    assert dataset.default_targets("KQvKR", "final_diagnostic").primary == 1_000


def test_uniform_assignments_include_both_color_orientations() -> None:
    rng = random.Random(41)
    orientations: set[tuple[bool, bool]] = set()
    for _ in range(100):
        board = dataset._sample_primary("KQvKR", rng)
        queen_is_white = bool(board.pieces(chess.QUEEN, chess.WHITE))
        rook_is_white = bool(board.pieces(chess.ROOK, chess.WHITE))
        assert queen_is_white != rook_is_white
        orientations.add((queen_is_white, rook_is_white))
        assert board.halfmove_clock == 0
        assert board.fullmove_number == 1
        assert not board.move_stack
        assert len(board.piece_map()) == 4
    assert orientations == {(True, False), (False, True)}


def test_seeded_generation_repeats_exact_rows() -> None:
    target = dataset.PartitionTargets(primary=8)
    first = dataset.generate_partition(
        "KRvKR", "rl_starts", PositionTablebase(), targets=target, seed=7001
    )
    second = dataset.generate_partition(
        "KRvKR", "rl_starts", PositionTablebase(), targets=target, seed=7001
    )
    assert first.rows == second.rows
    assert first.proposals == second.proposals
    assert first.rejections == second.rejections


def test_rows_are_canonical_unique_and_owned_by_requested_split() -> None:
    result = dataset.generate_partition(
        "KRvKR",
        "development",
        PositionTablebase(),
        targets=dataset.PartitionTargets(primary=5),
        seed=991,
        proposal_cap=10_000,
    )
    keys = [str(row["canonical_position"]) for row in result.rows]
    assert len(keys) == len(set(keys)) == 5
    for row in result.rows:
        board = chess.Board(str(row["fen"]))
        assert not board.move_stack
        assert board.halfmove_clock == 0
        assert board.fullmove_number == 1
        assert canonical_position(board) == row["canonical_position"]
        assert ownership_split("KRvKR", str(row["canonical_position"])) == "development"
        assert row["ownership_split"] == "development"


@pytest.mark.parametrize(
    ("family", "descendant"),
    [("KRvKR", "KRvK"), ("KQvKR", "KQvK"), ("KQvKR", "KRvK")],
)
def test_descendant_generation_assigns_legal_three_piece_material(
    family: str, descendant: str
) -> None:
    target = dataset.PartitionTargets(primary=0, descendants=((descendant, 3),))
    result = dataset.generate_partition(
        family,  # type: ignore[arg-type]
        "pretraining",
        PositionTablebase(),
        targets=target,
        seed=8001,
        proposal_cap=100_000,
    )
    assert len(result.rows) == 3
    for row in result.rows:
        board = chess.Board(str(row["fen"]))
        assert board.is_valid()
        assert board.outcome(claim_draw=True) is None
        assert len(board.piece_map()) == 3
        assert row["material"] == descendant
        assert row["ownership_split"] == "pretraining"


def test_training_rows_include_reference_and_negative_value_label() -> None:
    result = dataset.generate_partition(
        "KRvKR",
        "pretraining",
        PositionTablebase(),
        targets=dataset.PartitionTargets(primary=2),
        seed=8021,
        proposal_cap=10_000,
    )
    for row in result.rows:
        reference = row["reference"]
        assert isinstance(reference, dict)
        assert row["label"] == -reference["value"]
        assert set(reference) == {"value", "raw_wdl", "raw_dtz"}


def test_development_rows_do_not_expose_reference_labels(tmp_path: Path) -> None:
    result = dataset.generate_partition(
        "KRvKR",
        "development",
        PositionTablebase(),
        targets=dataset.PartitionTargets(primary=2),
        seed=8022,
        proposal_cap=10_000,
    )
    data_path, manifest_path = dataset.write_partition(result, tmp_path)
    rows = [
        json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines()
    ]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert all("label" not in row and "reference" not in row for row in rows)
    assert "family_screen" in manifest
    assert manifest["jsonl_sha256"]


def test_invalid_proposals_are_counted_and_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted = _board_for_split("KRvKR", "development", seed=33)
    invalid = chess.Board(None)
    proposals = iter((invalid, accepted))
    monkeypatch.setattr(dataset, "_sample_primary", lambda family, rng: next(proposals))
    result = dataset.generate_partition(
        "KRvKR",
        "development",
        PositionTablebase(),
        targets=dataset.PartitionTargets(primary=1),
        proposal_cap=2,
    )
    assert result.proposals == 2
    assert result.rejections["invalid"] == 1
    assert len(result.rows) == 1


def test_cap_failure_reports_unmet_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    board = _board_for_split("KRvKR", "validation", seed=44)
    monkeypatch.setattr(dataset, "_sample_primary", lambda family, rng: board)
    with pytest.raises(dataset.GenerationLimitError, match="primary=0/1"):
        dataset.generate_partition(
            "KRvKR",
            "development",
            PositionTablebase(),
            targets=dataset.PartitionTargets(primary=1),
            proposal_cap=3,
        )


@pytest.mark.parametrize(
    ("sensitive", "worsening", "expected"),
    [(99, 100, False), (100, 99, False), (100, 100, True)],
)
def test_development_screen_boundary(
    sensitive: int, worsening: int, expected: bool
) -> None:
    assert dataset.screen_family(sensitive, worsening).passes is expected


def test_diagnostic_requires_distinct_action_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = PositionTablebase()
    rng = random.Random(123)
    diverse: chess.Board | None = None
    for _ in range(5_000):
        candidate = dataset._sample_primary("KRvKR", rng)
        if (
            candidate.is_valid()
            and candidate.outcome(claim_draw=True) is None
            and ownership_split("KRvKR", canonical_position(candidate))
            == "final_diagnostic"
            and len(set(dataset._q_values(candidate, probe))) > 1
        ):
            diverse = candidate
            break
    assert diverse is not None
    monkeypatch.setattr(dataset, "_sample_primary", lambda family, generator: diverse)
    result = dataset.generate_partition(
        "KRvKR",
        "final_diagnostic",
        probe,
        targets=dataset.PartitionTargets(primary=1, require_action_diversity=True),
        proposal_cap=1,
    )
    assert len(result.rows) == 1
    assert result.rows[0]["ownership_split"] == "final_diagnostic"


def test_acquisition_manifest_requires_all_verified_local_hashes(
    tmp_path: Path,
) -> None:
    tablebase_dir = tmp_path / "tables"
    tablebase_dir.mkdir()
    table_records: dict[str, dict[str, object]] = {}
    for name in sorted(dataset._expected_table_names()):
        payload = f"fixture:{name}".encode()
        (tablebase_dir / name).write_bytes(payload)
        table_records[name] = {
            "verification": "passed",
            "local_sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
    manifest_path = tmp_path / "acquisition.json"
    manifest_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "protocol": "opponent-dependence-protocol-v1",
                "completed_at_utc": "2026-10-18T00:00:00Z",
                "tables": table_records,
            }
        ),
        encoding="utf-8",
    )
    provenance = dataset.verify_acquisition_manifest(manifest_path, tablebase_dir)
    assert set(provenance["table_sha256"]) == dataset._expected_table_names()
    assert len(str(provenance["acquisition_manifest_sha256"])) == 64

    (tablebase_dir / "KRvKR.rtbw").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        dataset.verify_acquisition_manifest(manifest_path, tablebase_dir)


def test_cli_fails_closed_without_completed_acquisition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = tmp_path / "failed.json"
    manifest.write_text(json.dumps({"status": "failed"}), encoding="utf-8")
    tablebase_dir = tmp_path / "tables"
    tablebase_dir.mkdir()
    output = tmp_path / "out"
    monkeypatch.setattr(
        dataset.chess.syzygy,
        "open_tablebase",
        lambda path: pytest.fail("tablebase was opened before manifest verification"),
    )
    exit_code = dataset.main(
        [
            "--tablebase-dir",
            str(tablebase_dir),
            "--acquisition-manifest",
            str(manifest),
            "--output-dir",
            str(output),
        ]
    )
    assert exit_code == 2
    assert "status 'complete'" in capsys.readouterr().err
    failures = list(output.glob("failed-*.manifest.json"))
    assert len(failures) == 1
    assert json.loads(failures[0].read_text(encoding="utf-8"))["status"] == "failed"


def test_writer_refuses_to_overwrite_existing_outputs(tmp_path: Path) -> None:
    result = dataset.generate_partition(
        "KRvKR",
        "rl_starts",
        PositionTablebase(),
        targets=dataset.PartitionTargets(primary=1),
        seed=9101,
    )
    data_path, manifest_path = dataset.write_partition(result, tmp_path)
    original_data = data_path.read_bytes()
    original_manifest = manifest_path.read_bytes()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        dataset.write_partition(result, tmp_path)
    assert data_path.read_bytes() == original_data
    assert manifest_path.read_bytes() == original_manifest


def test_diagnostic_cap_freezes_attained_set_at_two_hundred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    board = _board_for_split("KRvKR", "final_diagnostic", seed=91)
    key_number = 0

    def unique_key(_: chess.Board) -> str:
        nonlocal key_number
        key_number += 1
        return f"synthetic-position-{key_number:03d}"

    monkeypatch.setattr(dataset, "_sample_primary", lambda family, rng: board)
    monkeypatch.setattr(dataset, "canonical_position", unique_key)
    monkeypatch.setattr(dataset, "ownership_bucket", lambda family, key: 90)
    monkeypatch.setattr(
        dataset, "ownership_split", lambda family, key: "final_diagnostic"
    )
    monkeypatch.setattr(dataset, "_q_values", lambda candidate, tablebase: (0, 1))
    result = dataset.generate_partition(
        "KRvKR",
        "final_diagnostic",
        PositionTablebase(),
        targets=dataset.PartitionTargets(primary=205, require_action_diversity=True),
        proposal_cap=200,
    )
    assert not result.complete
    assert result.targets.primary == 205
    assert result.frozen_attained_count == len(result.rows) == 200


def test_cli_returns_failure_when_neither_family_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TablebaseContext:
        def __enter__(self) -> PositionTablebase:
            return PositionTablebase()

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        dataset,
        "verify_acquisition_manifest",
        lambda manifest_path, tablebase_dir: {
            "acquisition_manifest_sha256": "a" * 64,
            "table_sha256": {},
        },
    )
    monkeypatch.setattr(
        dataset.chess.syzygy,
        "open_tablebase",
        lambda path: TablebaseContext(),
    )

    def failed_screen(family, partition, tablebase, **kwargs):
        return dataset.GenerationResult(
            family=family,
            partition=partition,
            seed=dataset.protocol_seed(family, partition),
            rows=[],
            targets=dataset.PartitionTargets(primary=2_000),
            proposals=20,
            proposal_cap=100,
            sensitive_positions=0,
            positions_with_worsening_move=0,
        )

    monkeypatch.setattr(dataset, "generate_partition", failed_screen)
    output = tmp_path / "data"
    result = dataset.main(
        [
            "--tablebase-dir",
            str(tmp_path / "tables"),
            "--acquisition-manifest",
            str(tmp_path / "acquisition.json"),
            "--output-dir",
            str(output),
        ]
    )
    assert result == 1
    failures = list(output.glob("infeasible_screen-*.manifest.json"))
    assert len(failures) == 1
    assert json.loads(failures[0].read_text(encoding="utf-8"))["status"] == (
        "infeasible_screen"
    )
