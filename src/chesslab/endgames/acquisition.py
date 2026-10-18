"""Serial, auditable acquisition of the protocol's Syzygy table files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import cast

TABLE_MATERIALS = ("KRvKR", "KQvKR", "KRvK", "KQvK")
TABLE_TYPES = ("rtbw", "rtbz")
LICHESS_ROOT = "https://tablebase.lichess.ovh/tables/standard"
LICHESS_SHA256_URL = f"{LICHESS_ROOT}/sha256"
SYZYGY_REVISION = "0bb8aeee525f364bb750f96df312a1a7c9b54398"
SYZYGY_ROOT = (
    "https://raw.githubusercontent.com/syzygy1/tb/"
    f"{SYZYGY_REVISION}"
)
SYZYGY_README_URL = f"{SYZYGY_ROOT}/README.md"
SYZYGY_RESOURCES = {
    "wdl345_checksums": f"{SYZYGY_ROOT}/checksums/wdl345.txt",
    "dtz345_checksums": f"{SYZYGY_ROOT}/checksums/dtz345.txt",
    "checksum_readme": SYZYGY_README_URL,
    "checksum_source": f"{SYZYGY_ROOT}/src/checksum.c",
}
PublisherFetch = Callable[[str, Path], None]
_SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def fetch_url(url: str, destination: Path) -> None:
    """Stream one publisher resource to a new local file."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "chess-ai-lab/0.1 table acquisition"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        with destination.open("xb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)


def _file_facts(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _parse_sha256_list(payload: bytes, names: set[str]) -> dict[str, str]:
    """Read common checksum-list layouts, requiring one digest per requested name."""
    text = payload.decode("utf-8-sig")
    found: dict[str, str] = {}
    for line in text.splitlines():
        digest_match = _SHA256_RE.search(line)
        if digest_match is None:
            continue
        digest = digest_match.group(1).lower()
        for name in names:
            pattern = rf"(?<![A-Za-z0-9_.-]){re.escape(name)}(?![A-Za-z0-9_.-])"
            if re.search(pattern, line):
                if name in found and found[name] != digest:
                    raise ValueError(
                        f"conflicting publisher SHA-256 entries for {name}"
                    )
                found[name] = digest
    missing = names - found.keys()
    if missing:
        raise ValueError(
            f"publisher SHA-256 list is missing: {', '.join(sorted(missing))}"
        )
    return found


def _write_manifest(path: Path, value: dict[str, object], *, replace: bool) -> None:
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if not replace:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        return
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(encoded)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _save_resource(
    name: str,
    url: str,
    destination: Path,
    fetcher: PublisherFetch,
) -> dict[str, object]:
    with NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
    temporary.unlink()
    try:
        fetcher(url, temporary)
        size, digest = _file_facts(temporary)
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite {destination}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "source_url": url,
        "retrieved_at_utc": _utc_now(),
        "bytes": size,
        "local_sha256": digest,
        "status": "retrieved",
        "name": name,
    }


def acquire(
    output_directory: Path,
    manifest_path: Path,
    fetcher: PublisherFetch = fetch_url,
) -> dict[str, object]:
    """Download and verify all eight approved files, recording failures too.

    Existing output files or manifests are never replaced. Partial validated
    files remain accompanied by a failed manifest if a later step fails.
    """
    output_directory = output_directory.resolve()
    manifest_path = manifest_path.resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "protocol": "opponent-dependence-protocol-v1",
        "status": "running",
        "started_at_utc": _utc_now(),
        "completed_at_utc": None,
        "publisher_notices": [
            {
                "source_url": SYZYGY_README_URL,
                "notice": (
                    "The pinned Syzygy README states that tablebase files may "
                    "be freely redistributed. This records the publisher's "
                    "statement and does not independently determine legal status."
                ),
            },
            {
                "source_url": SYZYGY_RESOURCES["checksum_readme"],
                "notice": (
                    "The checksum documentation says embedded table hashes "
                    "are not ordinary MD5 digests."
                ),
            },
        ],
        "verification_policy": {
            "whole_file_sha256": "compare each file against Lichess /sha256 list",
            "syzygy_embedded_checksum": "not_performed",
            "syzygy_embedded_checksum_reason": (
                "The pinned README/source are recorded for audit, but the "
                "generator-specific checksum algorithm is not reimplemented."
            ),
        },
        "resources": {},
        "tables": {},
        "error": None,
        "failed_source_url": None,
    }
    resources = cast(dict[str, object], manifest["resources"])
    tables = cast(dict[str, object], manifest["tables"])
    if manifest_path.exists():
        raise FileExistsError(f"manifest already exists: {manifest_path}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if output_directory.exists() and any(output_directory.iterdir()):
        manifest["status"] = "failed"
        manifest["error"] = "output directory is non-empty; refusing overwrite"
        manifest["completed_at_utc"] = _utc_now()
        _write_manifest(manifest_path, manifest, replace=False)
        raise FileExistsError(str(manifest["error"]))
    output_directory.mkdir(parents=True, exist_ok=True)
    _write_manifest(manifest_path, manifest, replace=False)

    current_source_url: str | None = None
    try:
        names = {
            f"{material}.{suffix}"
            for material in TABLE_MATERIALS
            for suffix in TABLE_TYPES
        }
        checksum_path = output_directory / "lichess_sha256_list.txt"
        current_source_url = LICHESS_SHA256_URL
        checksum_record = _save_resource(
            "lichess_sha256_list", LICHESS_SHA256_URL, checksum_path, fetcher
        )
        resources["lichess_sha256_list"] = checksum_record
        _write_manifest(manifest_path, manifest, replace=True)
        checksum_bytes = checksum_path.read_bytes()
        checksums = _parse_sha256_list(checksum_bytes, names)

        for name, url in SYZYGY_RESOURCES.items():
            current_source_url = url
            target = output_directory / name
            record = _save_resource(name, url, target, fetcher)
            resources[name] = record
            _write_manifest(manifest_path, manifest, replace=True)

        for material in TABLE_MATERIALS:
            for suffix in TABLE_TYPES:
                filename = f"{material}.{suffix}"
                tier = "wdl" if suffix == "rtbw" else "dtz"
                url = f"{LICHESS_ROOT}/3-4-5-{tier}/{filename}"
                current_source_url = url
                with NamedTemporaryFile(
                    dir=output_directory, delete=False
                ) as temporary:
                    temporary_path = Path(temporary.name)
                temporary_path.unlink()
                table_record = _save_resource(filename, url, temporary_path, fetcher)
                actual_size = table_record["bytes"]
                assert isinstance(actual_size, int)
                actual_digest = str(table_record["local_sha256"])
                expected_digest = checksums[filename]
                table_record["publisher_sha256"] = expected_digest
                table_record["whole_file_sha256_match"] = (
                    actual_digest == expected_digest
                )
                table_record["verification"] = (
                    "passed" if actual_digest == expected_digest else "failed"
                )
                if actual_digest != expected_digest:
                    temporary_path.unlink(missing_ok=True)
                    tables[filename] = table_record
                    raise ValueError(f"whole-file SHA-256 mismatch for {filename}")
                final_path = output_directory / filename
                if final_path.exists():
                    temporary_path.unlink(missing_ok=True)
                    raise FileExistsError(f"refusing to overwrite {final_path}")
                temporary_path.replace(final_path)
                table_record["bytes"] = actual_size
                tables[filename] = table_record
                _write_manifest(manifest_path, manifest, replace=True)
        manifest["status"] = "complete"
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(error).__name__}: {error}"
        manifest["failed_source_url"] = current_source_url
        manifest["completed_at_utc"] = _utc_now()
        _write_manifest(manifest_path, manifest, replace=True)
        raise
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        manifest["error"] = "KeyboardInterrupt during serial acquisition"
        manifest["failed_source_url"] = current_source_url
        manifest["completed_at_utc"] = _utc_now()
        _write_manifest(manifest_path, manifest, replace=True)
        raise
    manifest["completed_at_utc"] = _utc_now()
    _write_manifest(manifest_path, manifest, replace=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("manifest_path", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = acquire(args.output_directory, args.manifest_path)
    except Exception as error:
        print(f"acquisition failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
