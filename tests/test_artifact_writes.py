import ctypes
import json
import sys
import threading
import time
from pathlib import Path

import pytest

from chesslab.eval.artifacts import write_artifact_json


def test_transient_windows_sharing_error_retries_same_atomic_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "metadata.json"
    write_artifact_json(path, {"old": True})
    original = Path.replace
    attempts = []

    def sharing_once(source: Path, target: Path) -> Path:
        attempts.append(source)
        if len(attempts) == 1:
            assert json.loads(path.read_text()) == {"old": True}
            error = PermissionError("simulated Windows sharing failure")
            error.winerror = 32
            raise error
        return original(source, target)

    sleeps: list[float] = []
    monkeypatch.setattr(Path, "replace", sharing_once)
    monkeypatch.setattr(time, "sleep", sleeps.append)
    write_artifact_json(path, {"new": True}, replace=True)
    assert len(attempts) == 2
    assert attempts[0] == attempts[1]
    assert sleeps == [0.01]
    assert json.loads(path.read_text()) == {"new": True}
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("winerror,expected_calls", [(5, 16), (13, 1), (None, 1)])
def test_retry_limit_and_unrelated_failures_preserve_old_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    winerror: int | None,
    expected_calls: int,
) -> None:
    path = tmp_path / "metadata.json"
    write_artifact_json(path, {"old": True})
    attempts = []

    def blocked(source: Path, target: Path) -> Path:
        attempts.append(source)
        error = PermissionError("persistent error")
        if winerror is not None:
            error.winerror = winerror
        raise error

    monkeypatch.setattr(Path, "replace", blocked)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    with pytest.raises(PermissionError):
        write_artifact_json(path, {"new": True}, replace=True)
    assert len(attempts) == expected_calls
    assert json.loads(path.read_text()) == {"old": True}
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file sharing semantics")
def test_actual_windows_reader_lock_is_tolerated(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    write_artifact_json(path, {"old": True})
    kernel = ctypes.windll.kernel32
    create_file = kernel.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    close = kernel.CloseHandle
    close.argtypes = [ctypes.c_void_p]
    close.restype = ctypes.c_int
    # GENERIC_READ; share reads/writes but deny deletion/atomic replacement.
    handle = create_file(str(path), 0x80000000, 3, None, 3, 0x80, None)
    assert handle not in (None, ctypes.c_void_p(-1).value)
    released = threading.Event()

    def release() -> None:
        assert close(handle)
        released.set()

    timer = threading.Timer(0.15, release)
    timer.start()
    try:
        write_artifact_json(path, {"new": True}, replace=True)
        assert released.is_set()
        assert json.loads(path.read_text()) == {"new": True}
    finally:
        timer.join()
