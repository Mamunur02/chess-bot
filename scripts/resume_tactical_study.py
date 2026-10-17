"""Resume the frozen study after a transient progress-file access failure.

Retries the unchanged runner, never patches frozen source or retries a recorded
failed search. Preserves failure records and the original four-hour deadline.
"""

import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path


def retryable_metadata_failure(metadata: dict, stderr: str) -> bool:
    """Retry only Windows access failures naming the progress metadata file."""
    text = str(metadata.get("error", "")) + stderr
    return "WinError 5" in text and "metadata.json" in text


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    os.chdir(repository)
    output = repository / "artifacts" / "tactical-test-v1"
    recovery = output / "recovery-v1"
    recovery.mkdir(exist_ok=False)
    metadata_path = output / "metadata.json"
    session_path = repository / "artifacts" / "tactical-test-v1-session.json"
    original = json.loads(metadata_path.read_text())
    (recovery / "original-metadata.json").write_bytes(metadata_path.read_bytes())
    (recovery / "original-session.json").write_bytes(session_path.read_bytes())
    deadline = datetime.fromisoformat(original["provenance"]["started_at"]) + timedelta(
        hours=4
    )
    notes = {
        "status": "resuming",
        "started_at": original["provenance"]["started_at"],
        "recovery_started_at": datetime.now(UTC).isoformat(),
        "pid": os.getpid(),
        "original_deadline": deadline.isoformat(),
        "paid_compute": False,
        "initial_saved_cases": original["runs_written"],
        "recovery_policy": "At most eight retries of metadata WinError 5; frozen "
        "code/protocol unchanged; recorded cases are not rerun.",
        "attempts": [],
    }
    awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
    notes["temporary_sleep_inhibition_succeeded"] = awake

    def save() -> None:
        session_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

    try:
        save()
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
        for attempt in range(9):
            remaining = int((deadline - datetime.now(UTC)).total_seconds())
            if remaining <= 0:
                notes["status"] = "window_expired"
                return 1
            before = metadata_path.read_bytes()
            (recovery / f"attempt-{attempt:02d}-before.json").write_bytes(before)
            notes["status"] = "running"
            save()
            with (recovery / f"attempt-{attempt:02d}.stdout.log").open("w") as stdout:
                with (recovery / f"attempt-{attempt:02d}.stderr.log").open(
                    "w"
                ) as stderr:
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "chesslab.tactical",
                            "data/lichess/prepared-v1-verified",
                            str(output),
                            "--split",
                            "test",
                            "--budgets",
                            "1000",
                            "5000",
                            "20000",
                            "--repeats",
                            "3",
                            "--max-seconds",
                            str(remaining),
                            "--protocol",
                            "docs/research/tactical-evaluation-protocol.md",
                            "--resume",
                        ],
                        stdout=stdout,
                        stderr=stderr,
                        check=False,
                    )
            metadata = json.loads(metadata_path.read_text())
            error_log = (recovery / f"attempt-{attempt:02d}.stderr.log").read_text()
            notes["attempts"].append(
                {
                    "attempt": attempt,
                    "returncode": result.returncode,
                    "status": metadata["status"],
                    "runs_written": metadata["runs_written"],
                    "finished_at": datetime.now(UTC).isoformat(),
                }
            )
            save()
            if result.returncode == 0 and metadata["status"] == "completed":
                notes["status"] = "analysing"
                save()
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
                notes["status"] = (
                    "completed" if analysis.returncode == 0 else "analysis_failed"
                )
                return analysis.returncode
            if not retryable_metadata_failure(metadata, error_log):
                notes["status"] = "needs_attention"
                return result.returncode or 1
            time.sleep(min(2**attempt, 10))
        notes["status"] = "retry_limit_reached"
        return 1
    except BaseException as error:
        notes.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        notes["last_updated_at"] = datetime.now(UTC).isoformat()
        save()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    raise SystemExit(main())
