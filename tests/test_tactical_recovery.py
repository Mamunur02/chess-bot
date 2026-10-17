import runpy
from pathlib import Path

RECOVERY = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "resume_tactical_study.py")
)


def test_only_progress_file_access_failures_are_retryable() -> None:
    retryable = RECOVERY["retryable_metadata_failure"]
    assert retryable({"error": "PermissionError: [WinError 5] metadata.json"}, "")
    assert retryable({}, "[WinError 5] replacing metadata.json")
    assert not retryable({"error": "ValueError: resume source changed"}, "")
    assert not retryable({"error": "PermissionError: [WinError 5] case.json"}, "")
    assert not retryable({"error": "RuntimeError: search failed"}, "")
