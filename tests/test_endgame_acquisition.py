"""Offline tests for the fail-closed Syzygy acquisition CLI."""

import hashlib
import json
from pathlib import Path

import pytest

from chesslab.endgames.acquisition import (
    LICHESS_SHA256_URL,
    SYZYGY_README_URL,
    SYZYGY_RESOURCES,
    SYZYGY_REVISION,
    TABLE_MATERIALS,
    TABLE_TYPES,
    acquire,
)


def fixture_resources() -> dict[str, bytes]:
    tables = {
        f"{material}.{suffix}": f"fixture:{material}:{suffix}".encode()
        for material in TABLE_MATERIALS
        for suffix in TABLE_TYPES
    }
    checksums = "".join(
        f"{hashlib.sha256(payload).hexdigest()}  {name}\n"
        for name, payload in tables.items()
    ).encode()
    resources = {
        url: f"pinned resource: {name}".encode()
        for name, url in SYZYGY_RESOURCES.items()
    }
    resources[LICHESS_SHA256_URL] = checksums
    resources.update(
        {
            f"https://tablebase.lichess.ovh/tables/standard/3-4-5-"
            f"{'wdl' if suffix == 'rtbw' else 'dtz'}/{name}": payload
            for name, payload in tables.items()
            for suffix in (name.rsplit(".", 1)[1],)
        }
    )
    return resources


def fake_fetcher(resources: dict[str, bytes], calls: list[str]):
    def fetch(url: str, destination: Path) -> None:
        calls.append(url)
        payload = resources[url]
        with destination.open("xb") as stream:
            stream.write(payload)

    return fetch


def test_downloads_only_allowlisted_tables_serially_and_records_hashes(
    tmp_path: Path,
) -> None:
    output = tmp_path / "tables"
    manifest_path = tmp_path / "acquisition.json"
    resources = fixture_resources()
    calls: list[str] = []

    manifest = acquire(output, manifest_path, fake_fetcher(resources, calls))

    assert manifest["status"] == "complete"
    assert len(calls) == len(resources)
    assert calls.index(LICHESS_SHA256_URL) == 0
    assert all(
        SYZYGY_REVISION in url
        for url in calls
        if "raw.githubusercontent.com" in url
    )
    assert SYZYGY_README_URL == (
        "https://raw.githubusercontent.com/syzygy1/tb/"
        f"{SYZYGY_REVISION}/README.md"
    )
    tables = manifest["tables"]
    assert isinstance(tables, dict)
    assert set(tables) == {
        f"{material}.{suffix}"
        for material in TABLE_MATERIALS
        for suffix in TABLE_TYPES
    }
    for name, record in tables.items():
        assert isinstance(record, dict)
        assert record["verification"] == "passed"
        assert record["local_sha256"] == record["publisher_sha256"]
        assert (output / name).is_file()
        assert record["retrieved_at_utc"].endswith("Z")
        assert record["bytes"] > 0
    policy = manifest["verification_policy"]
    assert isinstance(policy, dict)
    assert policy["syzygy_embedded_checksum"] == "not_performed"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "complete"


def test_digest_parser_rejects_missing_expected_entry(tmp_path: Path) -> None:
    resources = fixture_resources()
    resources[LICHESS_SHA256_URL] = b"0" * 64 + b"  KRvKR.rtbw\n"
    manifest_path = tmp_path / "acquisition.json"
    with pytest.raises(ValueError, match="missing"):
        acquire(tmp_path / "tables", manifest_path, fake_fetcher(resources, []))
    failed = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert "missing" in failed["error"]


def test_mismatched_digest_fails_and_keeps_failure_manifest(tmp_path: Path) -> None:
    resources = fixture_resources()
    url = next(url for url in resources if url.endswith("/KRvKR.rtbw"))
    resources[url] = b"corrupt payload"
    manifest_path = tmp_path / "acquisition.json"
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        acquire(tmp_path / "tables", manifest_path, fake_fetcher(resources, []))
    failed = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    record = failed["tables"]["KRvKR.rtbw"]
    assert record["verification"] == "failed"
    assert not (tmp_path / "tables" / "KRvKR.rtbw").exists()


def test_missing_resource_is_recorded_as_incomplete(tmp_path: Path) -> None:
    resources = fixture_resources()
    del resources[SYZYGY_RESOURCES["checksum_source"]]
    manifest_path = tmp_path / "acquisition.json"
    with pytest.raises(KeyError):
        acquire(tmp_path / "tables", manifest_path, fake_fetcher(resources, []))
    failed = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert "KeyError" in failed["error"]
    assert failed["failed_source_url"] == SYZYGY_RESOURCES["checksum_source"]


def test_keyboard_interrupt_writes_interrupted_manifest_with_source_url(
    tmp_path: Path,
) -> None:
    resources = fixture_resources()
    manifest_path = tmp_path / "acquisition.json"

    def interrupt(url: str, destination: Path) -> None:
        if url == SYZYGY_README_URL:
            raise KeyboardInterrupt
        fake_fetcher(resources, [])(url, destination)

    with pytest.raises(KeyboardInterrupt):
        acquire(tmp_path / "tables", manifest_path, interrupt)
    interrupted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert interrupted["status"] == "interrupted"
    assert interrupted["failed_source_url"] == SYZYGY_README_URL


def test_refuses_existing_manifest_and_nonempty_output(tmp_path: Path) -> None:
    resources = fixture_resources()
    manifest_path = tmp_path / "acquisition.json"
    manifest_path.write_text("previous", encoding="utf-8")
    with pytest.raises(FileExistsError, match="manifest already exists"):
        acquire(tmp_path / "tables", manifest_path, fake_fetcher(resources, []))
    assert manifest_path.read_text(encoding="utf-8") == "previous"

    output = tmp_path / "occupied"
    output.mkdir()
    (output / "keep.bin").write_bytes(b"prior")
    fresh_manifest = tmp_path / "failed.json"
    with pytest.raises(FileExistsError, match="non-empty"):
        acquire(output, fresh_manifest, fake_fetcher(resources, []))
    assert (output / "keep.bin").read_bytes() == b"prior"
    assert json.loads(fresh_manifest.read_text(encoding="utf-8"))["status"] == "failed"
