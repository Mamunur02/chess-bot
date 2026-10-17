"""Execute the frozen local study and its automatic post-run analysis.

Run in a hidden background process with stdout/stderr redirected to local logs.
Keeps Windows awake temporarily without changing the user's power plan.
"""

import ctypes
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    os.chdir(repository)
    output = repository / "artifacts" / "tactical-test-v1"
    notes_path = repository / "artifacts" / "tactical-test-v1-session.json"
    notes: dict[str, object] = {
        "started_at": datetime.now(UTC).isoformat(),
        "status": "starting",
        "authorization": "User selected three passes and confirmed availability now.",
        "window_seconds": 14400,
        "power_load": "User confirmed quiet/awake window; no power plan change.",
        "paid_compute": False,
        "pid": os.getpid(),
    }
    awake = False
    if sys.platform == "win32":
        awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
    notes["temporary_sleep_inhibition_succeeded"] = awake

    def save() -> None:
        notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

    try:
        save()
        # Unscored small development warmup in a separate Python process.
        warmup = subprocess.run(
            [
                sys.executable,
                "scripts/run_tactical_pilot.py",
                "data/lichess/prepared-v1-verified",
                "artifacts/tactical-test-warmup-v1",
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
            raise RuntimeError(f"warmup exited {warmup.returncode}")
        notes["status"] = "running"
        save()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "chesslab.tactical",
                "data/lichess/prepared-v1-verified",
                "artifacts/tactical-test-v1",
                "--split",
                "test",
                "--budgets",
                "1000",
                "5000",
                "20000",
                "--repeats",
                "3",
                "--max-seconds",
                "14400",
                "--protocol",
                "docs/research/tactical-evaluation-protocol.md",
            ],
            check=False,
        )
        notes["runner_returncode"] = result.returncode
        metadata = json.loads((output / "metadata.json").read_text())
        notes["runner_status"] = metadata["status"]
        if metadata["status"] != "completed":
            notes["status"] = "needs_attention"
            return result.returncode or 1
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
        notes["status"] = "completed" if analysis.returncode == 0 else "analysis_failed"
        return analysis.returncode
    except BaseException as error:
        notes.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        notes["finished_at"] = datetime.now(UTC).isoformat()
        save()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    raise SystemExit(main())
