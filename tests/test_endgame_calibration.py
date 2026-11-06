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
    assert predictor.totals == {
        "calls": 2, "boards": 3, "failures": 0, "seconds": 0.75
    }


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
