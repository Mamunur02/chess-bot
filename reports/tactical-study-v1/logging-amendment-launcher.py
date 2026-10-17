"""Resume frozen search with a disclosed, separately snapshotted logging fix.

The original plan/source snapshot is never rewritten. Frozen search is loaded
from its copied source tree; only its artifact-writer alias is replaced by the
tested amended writer. This operational amendment is recorded with both hashes.
"""

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    os.chdir(repository)
    output = repository / "artifacts" / "tactical-test-v1"
    source_root = output / "sources"
    writer_name = "src/chesslab/eval/artifacts.py"
    plan = json.loads((output / "plan.json").read_text())
    for name, expected in plan["code_sha256"].items():
        if digest(source_root / name) != expected:
            raise ValueError("frozen source snapshot changed")
        if name != writer_name and digest(repository / name) != expected:
            raise ValueError("unapproved source/lock change outside logging writer")
    protocol = repository / "docs/research/tactical-evaluation-protocol.md"
    if digest(protocol) != plan["protocol_sha256"]:
        raise ValueError("frozen protocol changed")
    initial = json.loads((output / "metadata.json").read_text())
    deadline = datetime.fromisoformat(initial["provenance"]["started_at"]) + timedelta(
        hours=4
    )
    writer_path = repository / writer_name
    if args.check_only:
        print(
            json.dumps(
                {
                    "frozen_sources_verified": True,
                    "old_writer_sha256": plan["code_sha256"][writer_name],
                    "new_writer_sha256": digest(writer_path),
                    "saved_cases": len(list((output / "cases").glob("*.json"))),
                    "deadline": deadline.isoformat(),
                },
                indent=2,
            )
        )
        return 0
    if datetime.now(UTC) >= deadline:
        raise RuntimeError("original quiet window has expired")
    recovery = output / "recovery-v2"
    recovery.mkdir(exist_ok=False)
    metadata_path = output / "metadata.json"
    session_path = repository / "artifacts/tactical-test-v1-session.json"
    (recovery / "original-metadata.json").write_bytes(metadata_path.read_bytes())
    (recovery / "original-session.json").write_bytes(session_path.read_bytes())
    amended_writer = recovery / "logging-writer.py"
    amended_writer.write_bytes(writer_path.read_bytes())
    (recovery / "launcher.py").write_bytes(Path(__file__).read_bytes())
    amendment = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "authorization": "User explicitly requested fixing the problem and resuming.",
        "reason": "Repeated Windows metadata atomic-replace access/sharing errors.",
        "scope": "Only run_tactical.write_artifact_json is rebound to a tested "
        "writer with bounded in-place Windows sharing retries. Search, labels, "
        "budgets, seeds and case files are unchanged. Original plan is retained.",
        "original_plan_digest": initial["manifest_digest"],
        "old_writer_sha256": plan["code_sha256"][writer_name],
        "new_writer_sha256": digest(amended_writer),
        "launcher_sha256": digest(recovery / "launcher.py"),
        "source_root": str(source_root),
        "initial_saved_cases": initial["runs_written"],
    }
    (recovery / "amendment.json").write_text(json.dumps(amendment, indent=2) + "\n")
    notes = {
        "status": "starting",
        "started_at": initial["provenance"]["started_at"],
        "recovery_started_at": datetime.now(UTC).isoformat(),
        "pid": os.getpid(),
        "original_deadline": deadline.isoformat(),
        "paid_compute": False,
        "amendment": "artifacts/tactical-test-v1/recovery-v2/amendment.json",
    }
    awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
    notes["temporary_sleep_inhibition_succeeded"] = awake
    try:
        session_path.write_text(json.dumps(notes, indent=2) + "\n")
        warmup = subprocess.run(
            [
                sys.executable,
                "scripts/run_tactical_pilot.py",
                "data/lichess/prepared-v1-verified",
                str(recovery / "warmup"),
                "--positions",
                "1",
                "--budgets",
                "1000",
                "--max-seconds",
                "60",
            ],
            check=False,
        )
        if warmup.returncode:
            raise RuntimeError("recovery warmup failed")
        # Load the original engine and runner, not the modified working tree.
        sys.path.insert(0, str(source_root / "src"))
        import chesslab.tactical as runner

        if Path(runner.__file__).resolve() != source_root / "src/chesslab/tactical.py":
            raise ValueError("runner was not loaded from frozen source")
        spec = importlib.util.spec_from_file_location(
            "logging_amendment", amended_writer
        )
        assert spec is not None and spec.loader is not None
        logging = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(logging)
        runner.write_artifact_json = logging.write_artifact_json
        notes["status"] = "running"
        logging.write_artifact_json(session_path, notes, replace=True)
        remaining = (deadline - datetime.now(UTC)).total_seconds()
        if remaining <= 0:
            raise RuntimeError("original quiet window expired during setup")
        metadata = runner.run_tactical(
            repository / "data/lichess/prepared-v1-verified",
            output,
            split="test",
            budgets=(1000, 5000, 20000),
            repeats=3,
            max_seconds=remaining,
            repository=source_root,
            resume=True,
            protocol=protocol,
        )
        notes["runner_status"] = metadata["status"]
        if metadata["status"] != "completed":
            notes["status"] = "needs_attention"
            return 1
        notes["status"] = "analysing"
        logging.write_artifact_json(session_path, notes, replace=True)
        analysis = subprocess.run(
            [
                sys.executable,
                "scripts/analyse_tactical.py",
                str(output),
                "--output",
                "reports/tactical-study-v1",
            ],
            check=False,
        )
        notes["analysis_returncode"] = analysis.returncode
        notes["status"] = "completed" if analysis.returncode == 0 else "analysis_failed"
        return analysis.returncode
    except BaseException as error:
        notes.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        notes["last_updated_at"] = datetime.now(UTC).isoformat()
        session_path.write_text(json.dumps(notes, indent=2) + "\n")
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    raise SystemExit(main())
