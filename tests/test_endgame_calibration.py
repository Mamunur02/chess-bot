"""Fast contract checks for bounded endgame calibration helpers."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import chess
import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_endgame_calibration.py"
_SPEC = importlib.util.spec_from_file_location("run_endgame_calibration", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
calibration = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = calibration
_SPEC.loader.exec_module(calibration)


def test_hash_verification_rejects_corrupt_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / "initial-checkpoint.pt"
    checkpoint.write_bytes(b"altered")
    manifest = {"pretraining": {"initial_checkpoint_sha256": "0" * 64}}
    with pytest.raises(ValueError, match="checkpoint hash mismatch"):
        calibration._models(tmp_path, object(), object(), manifest)


def test_game_progress_persists_partial_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "game.json"
    record = {"status": "running"}
    snapshot = SimpleNamespace(
        plies=3,
        start_fen="start",
        learner=True,
        p=0.5,
        moves=("a1a2",),
        reward=None,
        truncated=True,
        truncation_reason="deadline",
        failure=None,
        learner_decisions=2,
        reference_evaluated_decisions=2,
        predictor_calls=2,
        forward_evaluations=2,
        learner_reference_errors=0,
        reference_failures=0,
        neural_work=2,
        encountered_keys=("position",),
        choice_records=(),
    )
    calibration._record_game(path, record, snapshot)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["progress"]["plies"] == 3
    assert saved["progress"]["truncation_reason"] == "deadline"
    assert saved["progress"]["start_fen"] == "start"


def test_manifest_write_failure_attaches_complete_snapshot(monkeypatch, tmp_path):
    error = OSError("disk full")
    manifest = {"status": "failed", "active_game": {"progress": {"moves": ["a2a4"]}}}

    def fail(*_args):
        raise error

    monkeypatch.setattr(calibration, "_atomic_json", fail)
    with pytest.raises(OSError) as raised:
        calibration._persist_or_attach(tmp_path / "manifest.json", manifest, None)
    assert raised.value is error
    assert raised.value.partial_manifest["active_game"]["progress"]["moves"] == ["a2a4"]


def test_final_manifest_failure_preserves_active_exception(monkeypatch, tmp_path):
    persistence_error = OSError("disk full")
    original = KeyboardInterrupt()
    manifest = {"status": "interrupted"}

    def fail(*_args):
        raise persistence_error

    monkeypatch.setattr(calibration, "_atomic_json", fail)
    calibration._persist_or_attach(tmp_path / "manifest.json", manifest, original)
    assert original.persistence_error is persistence_error
    assert original.partial_manifest is manifest


def test_timed_predictor_counts_failed_attempt_and_elapsed() -> None:
    def failing(_boards, _learner):
        raise RuntimeError("inference failed")

    predictor = calibration._TimedPredictor(failing)
    with pytest.raises(RuntimeError, match="inference failed"):
        predictor([object()], True)
    assert predictor.calls == predictor.boards == predictor.failures == 1
    assert predictor.seconds >= 0


@pytest.mark.parametrize("error", [RuntimeError("probe failed"), KeyboardInterrupt()])
def test_timed_tablebase_retains_failed_probe_and_elapsed(monkeypatch, error) -> None:
    ticks = iter((1.0, 1.25))
    monkeypatch.setattr(calibration.time, "perf_counter", lambda: next(ticks))

    class Table:
        def probe_wdl(self, _board):
            raise error

    timed = calibration._TimedTablebase(Table())
    with pytest.raises(type(error)):
        timed.probe_wdl(chess.Board())
    assert timed.probes["probe_wdl"] == 1
    assert timed.failures["probe_wdl"] == 1
    assert timed.seconds["probe_wdl"] == pytest.approx(0.25)
    if isinstance(error, RuntimeError):
        assert timed.errors["probe_wdl"] == ["RuntimeError: probe failed"]


def test_timed_tablebase_counts_success(monkeypatch) -> None:
    ticks = iter((2.0, 2.5))
    monkeypatch.setattr(calibration.time, "perf_counter", lambda: next(ticks))
    timed = calibration._TimedTablebase(SimpleNamespace(probe_dtz=lambda _: 4))
    assert timed.probe_dtz(chess.Board()) == 4
    assert timed.probes["probe_dtz"] == 1
    assert timed.seconds["probe_dtz"] == pytest.approx(0.5)


@pytest.mark.parametrize("mode", ["pretraining", "evaluation"])
@pytest.mark.parametrize("error", [RuntimeError("work failed"), KeyboardInterrupt()])
def test_attempted_work_failure_survives_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode, error
) -> None:
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    rows = [{"fen": board.fen()}]
    pilot_manifest_path = tmp_path / "pilot" / "pilot.json"
    pilot_manifest_path.parent.mkdir()
    acquisition_path = tmp_path / "acquisition.json"
    acquisition_path.write_text("{}", encoding="utf-8")
    acquisition_hash = calibration._sha256(acquisition_path.read_bytes())
    table = SimpleNamespace(close=lambda: setattr(table, "closed", table.closed + 1))
    table.closed = 0
    fake_pilot = SimpleNamespace(
        _load_development=lambda _: (rows, "development-hash"),
        DEV_SEED=1101,
        verify_acquisition_manifest=lambda *_: {"table_sha256": {"tb": "hash"}},
    )
    pilot_manifest_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "development": {
                    "jsonl_sha256": "development-hash",
                    "verified_seed": 1101,
                },
                "acquisition_manifest_sha256": acquisition_hash,
                "table_hashes": {"tb": "hash"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(calibration, "_pilot_module", lambda: fake_pilot)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    fake_neural = ModuleType("chesslab.endgames.neural")
    fake_neural.PretrainingConfig = object
    fake_neural.ValueNetwork = object
    fake_neural.pretrain = lambda *args, **kwargs: None

    def fail(*_args):
        raise error

    fake_neural.BatchPredictor = lambda _model: fail
    monkeypatch.setitem(sys.modules, "chesslab.endgames.neural", fake_neural)
    monkeypatch.setattr(calibration, "_configure_torch", lambda _: {})
    monkeypatch.setattr(calibration, "_models", lambda *_: [("pretrained", object())])
    monkeypatch.setattr(calibration, "_provenance", lambda *_: {})
    monkeypatch.setattr(calibration.chess.syzygy, "open_tablebase", lambda _: table)
    monkeypatch.setattr(
        table,
        "probe_wdl",
        fail,
        raising=False,
    )
    output = tmp_path / "output"
    output.mkdir()
    args = SimpleNamespace(
        output_dir=output,
        pilot_dir=pilot_manifest_path.parent,
        development_dir=tmp_path / "development",
        acquisition_manifest=acquisition_path,
        tablebase_dir=tmp_path / "tablebase",
        deadline_seconds=60.0,
        samples=1,
    )
    with pytest.raises(type(error)):
        getattr(calibration, f"run_{mode}")(args)
    saved = json.loads((output / "calibration.json").read_text(encoding="utf-8"))
    assert saved["status"] == (
        "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
    )
    work = saved["attempted_work"]
    if mode == "pretraining":
        assert work["tablebase"]["probes"]["probe_wdl"] == 1
        assert work["tablebase"]["failures"]["probe_wdl"] == 1
        assert work["tablebase"]["errors"]["probe_wdl"] == [
            f"{type(error).__name__}: {error}"
        ]
    else:
        assert work["predictors"]["pretrained"]["calls"] == 1
        assert work["predictors"]["pretrained"]["failures"] == 1
        assert work["predictors"]["pretrained"]["boards"] > 0
    assert table.closed == 1


def test_predictor_cumulative_work_survives_phase_reset(monkeypatch):
    ticks = iter((1.0, 1.25, 2.0, 2.5))
    monkeypatch.setattr(calibration.time, "perf_counter", lambda: next(ticks))
    predictor = calibration._TimedPredictor(lambda boards, _: [0.0] * len(boards))
    predictor([object()], True)
    predictor.calls = predictor.boards = predictor.failures = 0
    predictor.seconds = 0.0
    predictor([object(), object()], False)
    assert predictor.totals == {"calls": 2, "boards": 3, "failures": 0, "seconds": 0.75}


def test_source_snapshot_records_calibration_script(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    provenance = calibration._provenance(root, tmp_path)
    assert "scripts/run_endgame_calibration.py" in provenance["source_sha256"]
    assert (tmp_path / "source" / "scripts" / "run_endgame_calibration.py").is_file()


def test_evaluation_runner_completes_with_paired_fixed_streams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("torch")
    import chesslab.endgames.neural as neural

    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    rows = [
        {"fen": board.fen(), "canonical_position": f"fixture-{index}"}
        for index in range(2000)
    ]
    pilot_manifest_path = tmp_path / "pilot" / "pilot.json"
    pilot_manifest_path.parent.mkdir()
    acquisition_path = tmp_path / "acquisition.json"
    acquisition_path.write_text("{}", encoding="utf-8")
    acquisition_hash = calibration._sha256(acquisition_path.read_bytes())
    table = SimpleNamespace(close=lambda: None)
    fake_pilot = SimpleNamespace(
        _load_development=lambda _: (rows, "development-hash"),
        DEV_SEED=1101,
        verify_acquisition_manifest=lambda *_: {"table_sha256": {"tb": "hash"}},
    )
    pilot_manifest_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "development": {
                    "jsonl_sha256": "development-hash",
                    "verified_seed": 1101,
                },
                "acquisition_manifest_sha256": acquisition_hash,
                "table_hashes": {"tb": "hash"},
            }
        ),
        encoding="utf-8",
    )

    class Predictor:
        def __call__(self, _boards, _learner):
            return [0.0] * len(_boards)

    class FakeGame:
        start_fen = board.fen()
        learner = chess.WHITE
        p = 0.0
        reward = 0.0
        truncated = False
        truncation_reason = None
        failure = None
        plies = 1
        moves = ("a1a2",)
        learner_decisions = reference_evaluated_decisions = 1
        predictor_calls = forward_evaluations = neural_work = 1
        learner_reference_errors = reference_failures = 0
        encountered_keys = ("fixture",)
        choice_records = ()

    monkeypatch.setattr(calibration, "_pilot_module", lambda: fake_pilot)
    monkeypatch.setattr(
        calibration,
        "_models",
        lambda *_: [
            (name, object())
            for name in ("pretrained", "beta-0.0", "beta-0.5", "beta-1.0")
        ],
    )
    monkeypatch.setattr(calibration, "_provenance", lambda *_: {"source_sha256": {}})
    monkeypatch.setattr(neural, "BatchPredictor", lambda _model: Predictor())
    monkeypatch.setattr(calibration.chess.syzygy, "open_tablebase", lambda _: table)
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_predictions",
        lambda *_: SimpleNamespace(mse=0.0),
    )
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_choices",
        lambda *_: SimpleNamespace(loss_rate=0.0),
    )

    def play(*args, **kwargs):
        game = FakeGame()
        kwargs["progress_callback"](game)
        return game

    monkeypatch.setattr(calibration.evaluation, "play_fixed_game", play)
    args = SimpleNamespace(
        pilot_dir=pilot_manifest_path.parent,
        development_dir=tmp_path / "development",
        acquisition_manifest=acquisition_path,
        tablebase_dir=tmp_path / "tablebase",
        output_dir=tmp_path / "output",
        samples=1,
        deadline_seconds=60.0,
    )
    args.output_dir.mkdir()
    result = calibration.run_evaluation(args)
    assert result["status"] == "complete"
    assert len(list((args.output_dir / "games").glob("*.json"))) == 120

    # Real network and trainer, bounded repeated-development timing surrogate.
    monkeypatch.setattr(calibration, "TRAINING_COUNT", 4)
    monkeypatch.setattr(calibration, "VALIDATION_COUNT", 2)
    monkeypatch.setattr(
        calibration, "evaluate_reference", lambda *_: SimpleNamespace(value=0)
    )
    args.output_dir = tmp_path / "pretraining-output"
    args.output_dir.mkdir()
    fitted = calibration.run_pretraining(args)
    assert fitted["status"] == "complete"
    assert fitted["scales"][0]["epochs"] == 30
    assert fitted["current"]["completed_epochs"] == list(range(1, 31))
    saved = json.loads((args.output_dir / "calibration.json").read_text())
    assert saved["status"] == "complete"
    assert saved["threads"] == {"torch_intraop": 1, "torch_interop": 1}


@pytest.mark.parametrize(
    "runner", [calibration.run_evaluation, calibration.run_pretraining]
)
@pytest.mark.parametrize(
    "error,status",
    [
        (ValueError("setup broke"), "failed"),
        (TimeoutError("setup timeout"), "deadline"),
        (KeyboardInterrupt(), "interrupted"),
    ],
)
def test_setup_failures_are_durable(tmp_path, monkeypatch, runner, error, status):
    def fail():
        raise error

    monkeypatch.setattr(calibration, "_pilot_module", fail)
    args = SimpleNamespace(output_dir=tmp_path, deadline_seconds=60)
    if status == "deadline":
        assert runner(args)["status"] == status
    else:
        with pytest.raises(type(error)):
            runner(args)
    saved = json.loads((tmp_path / "calibration.json").read_text())
    assert saved["status"] == status
    assert saved["elapsed_seconds"] >= 0
    if status != "interrupted":
        assert str(error) in saved["error"]


@pytest.mark.parametrize("status", ["failed", "deadline", "interrupted"])
def test_cli_rejects_unsuccessful_manifest(tmp_path, monkeypatch, status):
    monkeypatch.setattr(calibration, "run_evaluation", lambda _: {"status": status})
    arguments = ["calibration", "evaluation"]
    for flag in [
        "development-dir",
        "pilot-dir",
        "tablebase-dir",
        "acquisition-manifest",
    ]:
        arguments.extend(["--" + flag, str(tmp_path)])
    arguments.extend(["--output-dir", str(tmp_path / "new")])
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit) as exc:
        calibration.main()
    assert exc.value.code == 1


@pytest.fixture
def runner_setup(tmp_path, monkeypatch):
    """Exercise real orchestration without Torch or local research artifacts."""
    board = chess.Board("7k/8/8/8/8/8/8/KR6 w - - 0 1")
    rows = [{"fen": board.fen(), "canonical_position": str(i)} for i in range(2000)]
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text("{}")
    (tmp_path / "pilot.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "development": {"jsonl_sha256": "data", "verified_seed": 1101},
                "acquisition_manifest_sha256": calibration._sha256(
                    acquisition.read_bytes()
                ),
                "table_hashes": {},
            }
        )
    )
    pilot = SimpleNamespace(
        DEV_SEED=1101,
        _load_development=lambda _: (rows, "data"),
        verify_acquisition_manifest=lambda *_: {"table_sha256": {}},
    )
    table = SimpleNamespace(closed=0)

    def close():
        table.closed += 1

    table.close = close
    neural = ModuleType("chesslab.endgames.neural")
    neural.BatchPredictor = lambda _: lambda boards, color: [0.0] * len(boards)
    neural.ValueNetwork = lambda **_: object()
    neural.PretrainingConfig = lambda **_: object()

    def pretrain(*args, **kwargs):
        kwargs["progress_callback"](SimpleNamespace(epoch=1))
        return SimpleNamespace(epochs=[1])

    neural.pretrain = pretrain
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "chesslab.endgames.neural", neural)
    monkeypatch.setattr(calibration, "_pilot_module", lambda: pilot)
    monkeypatch.setattr(calibration, "_configure_torch", lambda _: {})
    monkeypatch.setattr(calibration, "_models", lambda *_: [("pretrained", object())])
    monkeypatch.setattr(calibration, "_provenance", lambda *_: {})
    monkeypatch.setattr(calibration.chess.syzygy, "open_tablebase", lambda _: table)
    monkeypatch.setattr(calibration, "TRAINING_COUNT", 2)
    monkeypatch.setattr(calibration, "VALIDATION_COUNT", 2)
    monkeypatch.setattr(
        calibration, "evaluate_reference", lambda *_: SimpleNamespace(value=0)
    )
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_predictions",
        lambda *_: SimpleNamespace(mse=0),
    )
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_choices",
        lambda *_: SimpleNamespace(loss_rate=0),
    )
    choice = calibration.evaluation.ChoiceRecord("key", True, "b1b2", 0, 1, True, 0.5)
    snapshot = calibration.evaluation.GameEvaluation(
        board.fen(),
        True,
        0.5,
        None,
        True,
        "ply_cap",
        None,
        1,
        ("b1b2",),
        1,
        1,
        1,
        5,
        1,
        0,
        5,
        ("key",),
        (choice,),
    )

    def play(*args, **kwargs):
        kwargs["progress_callback"](snapshot)
        return snapshot

    monkeypatch.setattr(calibration.evaluation, "play_fixed_game", play)
    output = tmp_path / "out"
    output.mkdir()
    args = SimpleNamespace(
        output_dir=output,
        pilot_dir=tmp_path,
        development_dir=tmp_path,
        tablebase_dir=tmp_path,
        acquisition_manifest=acquisition,
        samples=1,
        deadline_seconds=60,
    )
    return args, table, neural, snapshot


@pytest.mark.parametrize("mode", ["evaluation", "pretraining"])
@pytest.mark.parametrize("phase", ["initial", "progress", "final"])
def test_runner_manifest_write_failures(runner_setup, monkeypatch, mode, phase):
    args, table, _, _ = runner_setup
    write = calibration._atomic_json
    error = OSError(f"{phase} write")
    calls = 0

    def inject(path, value):
        nonlocal calls
        if path.name == "calibration.json":
            calls += 1
            fail = (
                phase == "initial"
                and calls == 1
                or phase == "progress"
                and calls == 2
                or phase == "final"
                and "elapsed_seconds" in value
            )
            if fail:
                raise error
        write(path, value)

    monkeypatch.setattr(calibration, "_atomic_json", inject)
    with pytest.raises(OSError) as raised:
        getattr(calibration, f"run_{mode}")(args)
    assert raised.value is error
    if phase == "final":
        assert error.partial_manifest["status"] != "complete"
    else:
        saved = json.loads((args.output_dir / "calibration.json").read_text())
        assert saved["status"] == "failed"
        assert str(error) in saved["error"]
    assert table.closed == (0 if phase == "initial" else 1)


@pytest.mark.parametrize("mode", ["evaluation", "pretraining"])
@pytest.mark.parametrize("kind", [ValueError, KeyboardInterrupt, TimeoutError])
def test_original_work_error_survives_cleanup_and_final_write(
    runner_setup, monkeypatch, mode, kind
):
    args, table, _, _ = runner_setup
    original = kind("original work")
    cleanup = RuntimeError("cleanup failed")
    write_error = OSError("final write failed")

    def work(*_args, **_kwargs):
        raise original

    def close():
        table.closed += 1
        raise cleanup

    table.close = close
    monkeypatch.setattr(calibration, "select_learner_move", work)
    monkeypatch.setattr(calibration, "evaluate_reference", work)
    write = calibration._atomic_json

    def inject(path, value):
        if "elapsed_seconds" in value:
            raise write_error
        write(path, value)

    monkeypatch.setattr(calibration, "_atomic_json", inject)
    with pytest.raises(kind) as raised:
        getattr(calibration, f"run_{mode}")(args)
    assert raised.value is original
    assert original.cleanup_error is cleanup
    assert original.persistence_error is write_error
    assert "cleanup failed" in original.partial_manifest["cleanup_error"]
    assert table.closed == 1


@pytest.mark.parametrize("mode", ["evaluation", "pretraining"])
def test_cleanup_failure_after_work_cannot_return_success(
    runner_setup, monkeypatch, mode
):
    args, table, _, _ = runner_setup
    error = OSError("close failed")

    def close():
        table.closed += 1
        raise error

    table.close = close
    # Evaluation can finish all games without a failure or cap.
    from dataclasses import replace

    snap = replace(runner_setup[3], reward=0.0, truncated=False, truncation_reason=None)
    monkeypatch.setattr(calibration.evaluation, "play_fixed_game", lambda *a, **k: snap)
    with pytest.raises(OSError) as raised:
        getattr(calibration, f"run_{mode}")(args)
    assert raised.value is error
    saved = json.loads((args.output_dir / "calibration.json").read_text())
    assert saved["status"] == "failed"
    assert table.closed == 1


@pytest.mark.parametrize("phase", ["initial", "progress", "final"])
def test_game_write_failure_aborts_with_full_latest_state(
    runner_setup, monkeypatch, phase
):
    args, table, _, snap = runner_setup
    write = calibration._atomic_json
    error = OSError("game write failed")
    calls = 0

    def inject(path, value):
        nonlocal calls
        if path.parent.name == "games":
            calls += 1
            if calls == {"initial": 1, "progress": 2, "final": 3}[phase]:
                raise error
        write(path, value)

    monkeypatch.setattr(calibration, "_atomic_json", inject)
    with pytest.raises(OSError) as raised:
        calibration.run_evaluation(args)
    assert raised.value is error
    saved = json.loads((args.output_dir / "calibration.json").read_text())
    assert saved["status"] == "failed"
    if phase != "initial":
        assert saved["active_game"]["progress"] == calibration._game_progress(snap)
        assert saved["active_game"]["progress"]["reward"] is None
    assert table.closed == 1


@pytest.mark.parametrize("kind", [KeyboardInterrupt, ValueError, TimeoutError])
@pytest.mark.parametrize("write_target", ["game", "manifest"])
def test_real_game_error_survives_progress_and_final_write_failure(
    runner_setup, monkeypatch, kind, write_target
):
    args, table, _, _ = runner_setup
    # Restore the real primitive captured from a separate module load.
    spec = importlib.util.spec_from_file_location(
        "real_evaluation_persistence", Path(calibration.evaluation.__file__)
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        calibration.evaluation, "play_fixed_game", module.play_fixed_game
    )
    original = kind("game failed")

    def interrupt(*_args, **_kwargs):
        raise original

    monkeypatch.setattr(module, "select_learner_move", interrupt)
    monkeypatch.setattr(module, "choose_action", interrupt)
    write = calibration._atomic_json

    def fail(path, value):
        if (
            write_target == "game"
            and path.parent.name == "games"
            and "progress" in value
        ):
            raise OSError("game disk failure")
        if write_target == "manifest" and value.get("active_game", {}).get("progress"):
            raise OSError("progress manifest disk failure")
        if "elapsed_seconds" in value:
            raise OSError("manifest disk failure")
        write(path, value)

    monkeypatch.setattr(calibration, "_atomic_json", fail)
    with pytest.raises(kind) as raised:
        calibration.run_evaluation(args)
    assert raised.value is original
    manifest = original.partial_manifest
    expected_status = (
        "interrupted"
        if kind is KeyboardInterrupt
        else "deadline"
        if kind is TimeoutError
        else "failed"
    )
    assert manifest["status"] == expected_status
    progress = manifest["active_game"]["progress"]
    assert progress["reward"] is None
    assert progress["moves"] == []
    assert progress["encountered_keys"]
    assert progress["reference_evaluated_decisions"] == 0
    assert manifest["active_game"]["status"] == (
        "interrupted" if kind is KeyboardInterrupt else "failed"
    )
    if kind is not KeyboardInterrupt:
        assert progress["failure"] == f"{kind.__name__}: game failed"
    assert len(manifest["persistence_errors"]) == 2
    assert table.closed == 1


def _finish_latency(monkeypatch):
    monkeypatch.setattr(
        calibration,
        "select_learner_move",
        lambda board, learner, predictor, *_args: predictor([board], learner),
    )


def test_evaluation_deadline_between_prediction_and_choice_keeps_prediction(
    runner_setup, monkeypatch
):
    args, table, _, _ = runner_setup
    _finish_latency(monkeypatch)
    checks = 0

    def deadline():
        nonlocal checks
        checks += 1
        return checks == 8  # Setup, warmup, three samples, model, item, then choice.

    monkeypatch.setattr(calibration, "_deadline", lambda *_: deadline)
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_predictions",
        lambda boards, predictor, *_: (
            predictor(boards, boards[0].turn),
            SimpleNamespace(mse=0.25),
        )[1],
    )
    choice_calls = []
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_choices",
        lambda *_: choice_calls.append(True),
    )
    snapshots = []
    atomic_write = calibration._atomic_json

    def capture(path, value):
        if path.name == "calibration.json":
            snapshots.append(json.loads(json.dumps(value)))
        atomic_write(path, value)

    monkeypatch.setattr(calibration, "_atomic_json", capture)
    result = calibration.run_evaluation(args)
    item = result["items"][0]
    assert result["status"] == "deadline"
    assert item["prediction_status"] == "complete"
    assert item["prediction_mse"] == 0.25
    assert item["choice_status"] == "not_started"
    assert choice_calls == []
    saved = json.loads((args.output_dir / "calibration.json").read_text())
    assert saved["items"] == result["items"]
    assert saved["attempted_work"]["predictors"]["pretrained"]["calls"] > 0
    assert any(
        snapshot["status"] == "running"
        and snapshot["items"][0].get("prediction_status") == "complete"
        and snapshot["attempted_work"]["predictors"]["pretrained"]["calls"] > 0
        for snapshot in snapshots
        if snapshot.get("items")
    )


def test_evaluation_choice_error_keeps_prediction_and_attempted_work(
    runner_setup, monkeypatch
):
    args, _, _, _ = runner_setup
    _finish_latency(monkeypatch)
    monkeypatch.setattr(calibration, "_deadline", lambda *_: lambda: False)
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_predictions",
        lambda boards, predictor, *_: (
            predictor(boards, boards[0].turn),
            SimpleNamespace(mse=0.5),
        )[1],
    )
    error = RuntimeError("choice broke")

    def fail(*_args):
        raise error

    monkeypatch.setattr(calibration.evaluation, "evaluate_choices", fail)
    with pytest.raises(RuntimeError) as raised:
        calibration.run_evaluation(args)
    assert raised.value is error
    item = error.partial_manifest["items"][0]
    assert item["prediction_status"] == "complete"
    assert item["prediction_mse"] == 0.5
    assert item["choice_status"] == "failed"
    assert item["choice_seconds"] is not None
    assert (
        error.partial_manifest["attempted_work"]["predictors"]["pretrained"]["calls"]
        > 0
    )


def test_latency_failure_keeps_successful_samples_and_failed_attempt(
    runner_setup, monkeypatch
):
    args, _, _, _ = runner_setup
    calls = 0

    def select(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:  # One warmup, one successful sample, then failure.
            raise RuntimeError("latency failed")
        _args[2]([_args[0]], _args[1])

    monkeypatch.setattr(calibration, "select_learner_move", select)
    with pytest.raises(RuntimeError) as raised:
        calibration.run_evaluation(args)
    manifest = raised.value.partial_manifest
    assert len(manifest["latency"]["pretrained"]["seconds"]) == 1
    attempts = manifest["latency_attempts"]["pretrained"]
    assert [a["status"] for a in attempts] == ["complete", "complete", "failed"]
    assert attempts[-1]["seconds"] is not None
    assert manifest["attempted_work"]["predictors"]["pretrained"]["failures"] == 0


def test_warmup_deadline_keeps_partial_warmup_and_work_snapshot(
    runner_setup, monkeypatch
):
    args, _, _, _ = runner_setup
    args.samples = 2
    monkeypatch.setattr(
        calibration,
        "select_learner_move",
        lambda board, learner, predictor, *_args: predictor([board], learner),
    )
    checks = 0

    def deadline():
        nonlocal checks
        checks += 1
        return checks == 3  # Initial checkpoint check then between warmup attempts.

    monkeypatch.setattr(calibration, "_deadline", lambda *_: deadline)
    result = calibration.run_evaluation(args)
    assert result["status"] == "deadline"
    assert len(result["latency_attempts"]["pretrained"]) == 1
    assert result["latency_attempts"]["pretrained"][0]["phase"] == "warmup"
    saved = json.loads((args.output_dir / "calibration.json").read_text())
    assert saved["attempted_work"] == result["attempted_work"]


@pytest.mark.parametrize("phase", ["latency", "prediction", "choice"])
@pytest.mark.parametrize("kind", [ValueError, TimeoutError, KeyboardInterrupt])
def test_incremental_error_survives_write_failure(
    runner_setup, monkeypatch, phase, kind
):
    args, table, _, _ = runner_setup
    _finish_latency(monkeypatch)
    error = kind("operation failed")
    disk_error = OSError("progress write failed")
    failing = False
    original_write = calibration._atomic_json

    def fail(*_args):
        nonlocal failing
        failing = True
        raise error

    def write(path, value):
        if failing and path.name == "calibration.json":
            raise disk_error
        original_write(path, value)

    if phase == "latency":
        monkeypatch.setattr(calibration, "select_learner_move", fail)
    else:
        helper = "evaluate_predictions" if phase == "prediction" else "evaluate_choices"
        monkeypatch.setattr(calibration.evaluation, helper, fail)
    monkeypatch.setattr(calibration, "_atomic_json", write)
    with pytest.raises(kind) as raised:
        calibration.run_evaluation(args)
    assert raised.value is error
    assert error.persistence_error is disk_error
    manifest = error.partial_manifest
    expected = (
        "deadline"
        if kind is TimeoutError
        else "interrupted"
        if kind is KeyboardInterrupt
        else "failed"
    )
    assert manifest["status"] == expected
    if phase == "latency":
        record = manifest["latency_attempts"]["pretrained"][0]
        assert record["status"] == expected
        assert record["seconds"] >= 0
        assert manifest["latency"]["pretrained"]["warmup_count"] == 0
    else:
        record = manifest["items"][0]
        assert record[f"{phase}_status"] == expected
        assert record[f"{phase}_seconds"] >= 0
        if phase == "choice":
            assert record["prediction_status"] == "complete"
            assert record["prediction_mse"] == 0
    assert "attempted_work" in manifest
    assert table.closed == 1


def test_latency_seconds_exclude_incremental_persistence(runner_setup, monkeypatch):
    args, _, _, _ = runner_setup
    now = 0.0
    calls = 0
    original_write = calibration._atomic_json

    def clock():
        return now

    def write(path, value):
        nonlocal now
        original_write(path, value)
        now += 10.0

    def select(board, learner, predictor, *_args):
        nonlocal now, calls
        calls += 1
        now += 2.0
        predictor([board], learner)
        if calls == 3:
            raise ValueError("stop after one sample")

    monkeypatch.setattr(calibration.time, "perf_counter", clock)
    monkeypatch.setattr(calibration, "_deadline", lambda *_: lambda: False)
    monkeypatch.setattr(calibration, "_atomic_json", write)
    monkeypatch.setattr(calibration, "select_learner_move", select)
    with pytest.raises(ValueError):
        calibration.run_evaluation(args)
    saved = json.loads((args.output_dir / "calibration.json").read_text())
    assert saved["latency"]["pretrained"]["seconds"] == [2.0]
    assert [a["seconds"] for a in saved["latency_attempts"]["pretrained"]] == [2.0] * 3
    assert saved["attempted_work"]["predictors"]["pretrained"]["calls"] == 3
    assert saved["attempted_work"]["predictors"]["pretrained"]["failures"] == 0


def test_consecutive_games_have_isolated_attempted_work_deltas(
    runner_setup, monkeypatch
):
    args, table, _, snapshot = runner_setup
    monkeypatch.setattr(calibration, "P_VALUES", (0.1,))
    table.probe_wdl = lambda *_: 1
    table.probe_dtz = lambda *_: 2
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_predictions",
        lambda boards, predictor, tb: (
            predictor(boards, boards[0].turn),
            tb.probe_wdl(boards[0]),
            SimpleNamespace(mse=0.0),
        )[2],
    )
    monkeypatch.setattr(
        calibration.evaluation,
        "evaluate_choices",
        lambda boards, predictor, tb: (
            predictor(boards, boards[0].turn),
            tb.probe_dtz(boards[0]),
            SimpleNamespace(loss_rate=0.0),
        )[2],
    )

    game_index = 0

    def play(_board, _color, predictor, tb, *_args, **kwargs):
        nonlocal game_index
        game_index += 1
        for _ in range(game_index):
            predictor([snapshot], True)
        tb.probe_wdl(snapshot)
        successful_probe = table.probe_wdl

        def probe_failure(*_args):
            raise ValueError(f"probe error game {game_index}")

        table.probe_wdl = probe_failure
        try:
            with pytest.raises(ValueError):
                tb.probe_wdl(snapshot)
        finally:
            table.probe_wdl = successful_probe
        if game_index > 1:
            tb.probe_dtz(snapshot)
        kwargs["progress_callback"](snapshot)
        return snapshot

    monkeypatch.setattr(calibration.evaluation, "play_fixed_game", play)
    result = calibration.run_evaluation(args)
    games = sorted((args.output_dir / "games").glob("*.json"))
    first, second = [
        json.loads(path.read_text())["attempted_work_delta"] for path in games[:2]
    ]
    # Static work is cumulative before game one, but excluded from both deltas.
    assert first["predictors"]["pretrained"]["calls"] == 1
    assert second["predictors"]["pretrained"]["calls"] == 2
    assert first["tablebase"]["probes"] == {"probe_wdl": 2, "probe_dtz": 0}
    assert second["tablebase"]["probes"] == {"probe_wdl": 2, "probe_dtz": 1}
    for index, delta in enumerate((first, second), 1):
        assert delta["predictors"]["pretrained"]["boards"] == index
        assert delta["tablebase"]["failures"]["probe_wdl"] == 1
        assert delta["tablebase"]["errors"]["probe_wdl"] == [
            f"ValueError: probe error game {index}"
        ]
    assert result["attempted_work"]["predictors"]["pretrained"]["calls"] > 3


def test_second_game_progress_write_failure_keeps_delta_and_original_error(
    runner_setup, monkeypatch
):
    args, table, _, snapshot = runner_setup
    monkeypatch.setattr(calibration, "P_VALUES", (0.1,))
    table.probe_wdl = lambda *_: 1
    game_index = 0
    original = RuntimeError("second game failed")

    def play(_board, _color, predictor, tb, *_args, **kwargs):
        nonlocal game_index
        game_index += 1
        if game_index == 2:
            predictor.predictor = lambda *_: (_ for _ in ()).throw(original)
            try:
                predictor([snapshot], True)
            except RuntimeError:
                tb.probe_wdl(snapshot)
                try:
                    raise original
                except RuntimeError:
                    kwargs["progress_callback"](snapshot)
                    return snapshot
        else:
            predictor([snapshot], True)
            tb.probe_wdl(snapshot)
        kwargs["progress_callback"](snapshot)
        return snapshot

    monkeypatch.setattr(calibration.evaluation, "play_fixed_game", play)
    atomic_write = calibration._atomic_json
    failed_once = False

    # Trigger manifest failure while the second game's original exception is active.
    def inject(path, value):
        nonlocal failed_once
        if path.name == "calibration.json" and game_index == 2 and not failed_once:
            if value.get("active_game", {}).get("progress"):
                failed_once = True
                raise OSError("second progress manifest failure")
        atomic_write(path, value)

    monkeypatch.setattr(calibration, "_atomic_json", inject)
    with pytest.raises(RuntimeError) as raised:
        calibration.run_evaluation(args)
    assert raised.value is original
    manifest = original.partial_manifest
    delta = manifest["active_game"]["attempted_work_delta"]
    assert delta["predictors"]["pretrained"]["calls"] == 1
    assert delta["predictors"]["pretrained"]["failures"] == 1
    assert delta["tablebase"]["probes"]["probe_wdl"] == 1
    assert manifest["active_game"]["progress"] == calibration._game_progress(snapshot)
    assert manifest["attempted_work"]["predictors"]["pretrained"]["calls"] > 1
    assert manifest["persistence_errors"]
    assert table.closed == 1
