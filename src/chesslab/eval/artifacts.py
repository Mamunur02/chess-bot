"""Shared configuration identity, provenance, and artifact storage helpers."""

import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile

from chesslab.eval.benchmarks import capture_provenance


def configuration_digest(value: object) -> str:
    """Hash normalized JSON using the benchmark configuration convention."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def write_artifact_json(path: Path, value: object, *, replace: bool = False) -> None:
    """Write a new JSON artifact or atomically replace existing metadata.

    New artifacts use exclusive creation. Replacement uses a temporary file in
    the destination directory and cleans it up on handled write failures.
    """
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if replace:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(encoded)
            except BaseException:
                stream.close()
                temporary.unlink(missing_ok=True)
                raise
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(encoded)


def capture_run_metadata(
    repository: Path,
    run_id: str,
    config_digest: str,
    runs_planned: int,
) -> dict[str, object]:
    """Capture the common initial record for benchmark and match grids."""
    metadata: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "manifest_digest": config_digest,
        "status": "running",
        "provenance": capture_provenance(repository, config_digest).to_dict(),
        "dependency_versions": {
            package: version(package)
            for package in ("chess-ai-lab", "python-chess", "chess")
        },
        "runs_planned": runs_planned,
        "runs_written": 0,
        "error": None,
    }
    try:
        metadata["dependency_lock_sha256"] = hashlib.sha256(
            (repository / "uv.lock").read_bytes()
        ).hexdigest()
        metadata["dependency_lock_error"] = None
    except OSError as error:
        metadata["dependency_lock_sha256"] = None
        metadata["dependency_lock_error"] = f"{type(error).__name__}: {error}"
    return metadata
