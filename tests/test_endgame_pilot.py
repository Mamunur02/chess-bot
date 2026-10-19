"""Fast contract tests for pilot bounds and update scheduling."""

import importlib.util
import json
import math
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import chess
import pytest

_PILOT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_endgame_pilot.py"
_SPEC = importlib.util.spec_from_file_location("run_endgame_pilot", _PILOT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
pilot = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = pilot
_SPEC.loader.exec_module(pilot)

create_fresh_output = pilot.create_fresh_output
update_is_eligible = pilot.update_is_eligible
validate_decisions = pilot.validate_decisions


@pytest.mark.parametrize(
    ("count", "replay", "expected"),
    [
        (255, 255, False),
        (256, 256, True),
        (257, 257, False),
        (263, 263, False),
        (264, 264, True),
        (264, 31, False),
    ],
)
def test_update_schedule(count: int, replay: int, expected: bool) -> None:
    assert update_is_eligible(count, replay) is expected


@pytest.mark.parametrize("value", [1, 512])
def test_valid_decision_limits(value: int) -> None:
    validate_decisions(value)


@pytest.mark.parametrize("value", [0, -1, 513, True])
def test_rejects_decision_outside_bounded_pilot(value: int) -> None:
    with pytest.raises(ValueError):
        validate_decisions(value)


def test_fresh_output_refuses_existing_results() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as temporary:
        output = Path(temporary) / "pilot"
        create_fresh_output(output)
        (output / "prior-result.json").write_text("keep", encoding="utf-8")
        with pytest.raises(FileExistsError):
            create_fresh_output(output)
        assert (output / "prior-result.json").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize(
    ("status", "error"),
    [("failed", "RuntimeError: update failed"), ("interrupted", "KeyboardInterrupt")],
)
def test_method_failure_persists_status_and_partial_progress(
    tmp_path: Path, status: str, error: str
) -> None:
    result_path = tmp_path / "beta-0.5.json"
    method: dict[str, object] = {
        "beta": 0.5,
        "status": "running",
        "updates": 3,
        "update_records": [{"update": 3, "loss": 0.25}],
    }

    pilot._record_method_failure(
        method,
        result_path,
        status=status,
        error=error,
        elapsed_seconds=12.5,
    )

    import json

    saved = json.loads(result_path.read_text(encoding="utf-8"))
    assert saved["status"] == status
    assert saved["error"] == error
    assert saved["elapsed_seconds"] == 12.5
    assert saved["updates"] == 3
    assert saved["update_records"] == [{"update": 3, "loss": 0.25}]


def test_validation_uses_opposite_of_side_to_move() -> None:
    boards = [chess.Board(), chess.Board()]
    boards[1].turn = chess.BLACK

    class Predictor:
        def predict(self, positions):
            assert [learner for _, learner in positions] == [False, True]
            return [-1.0, 1.0]

    assert pilot._mse(Predictor(), boards, [-1.0, 1.0]) == 0.0


@pytest.mark.parametrize("error", [RuntimeError("injected"), KeyboardInterrupt()])
def test_runner_perspective_seed_and_active_failure(tmp_path, monkeypatch, error):
    pytest.importorskip("torch")
    import argparse
    from types import SimpleNamespace

    import chesslab.endgames.neural as neural

    boards = [chess.Board(), chess.Board()]
    boards[1].turn = chess.BLACK
    rows = [{"fen": boards[index % 2].fen()} for index in range(2000)]
    monkeypatch.setattr(pilot, "_load_development", lambda _: (rows, "fixture"))
    monkeypatch.setattr(pilot, "_source_snapshot", lambda *_: {})
    monkeypatch.setattr(pilot, "_git_state", lambda _: {})
    monkeypatch.setattr(
        pilot, "verify_acquisition_manifest",
        lambda *_: {"table_sha256": {"fixture": "hash"}},
    )
    monkeypatch.setattr(
        pilot.chess.syzygy, "open_tablebase",
        lambda _: SimpleNamespace(close=lambda: None),
    )
    monkeypatch.setattr(
        pilot, "evaluate", lambda *_: SimpleNamespace(value=1, raw_wdl=2)
    )

    def pretrain(model, train_x, train_y, valid_x, valid_y, *, seed, config):
        assert seed == 9001
        assert [row[769] for row in train_x[:2]] == [0.0, 1.0]
        assert [row[769] for row in valid_x[:2]] == [0.0, 1.0]
        assert set(train_y) == {-1.0}
        return SimpleNamespace(
            best_state_dict=model.state_dict(), epochs=(),
            best_epoch=0, stop_reason="fixture",
        )

    monkeypatch.setattr(neural, "pretrain", pretrain)
    streams = []
    original_rng = pilot.make_rng

    def rng(seed, stream):
        assert seed == 9001
        streams.append(stream)
        return original_rng(seed, stream)

    monkeypatch.setattr(pilot, "make_rng", rng)

    def fail_interaction(*args):
        raise error

    monkeypatch.setattr(pilot, "run_interaction", fail_interaction)
    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text("{}")
    output = tmp_path / "pilot"
    args = argparse.Namespace(
        decisions=1, threads=1, output_dir=output, development_dir=tmp_path,
        acquisition_manifest=acquisition, tablebase_dir=tmp_path,
    )
    with pytest.raises(type(error)):
        pilot.run_pilot(args)
    expected = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
    manifest = json.loads((output / "pilot.json").read_text())
    method = json.loads((output / "beta-0.0.json").read_text())
    assert manifest["status"] == method["status"] == expected
    assert method["partial_transitions"] == 0
    assert method["elapsed_seconds"] >= 0
    assert streams == ["replay", "starts", "exploration", "opponent"]


def test_successful_three_method_run_records_training_and_costs(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    import argparse
    from dataclasses import replace
    from types import SimpleNamespace

    import chesslab.endgames.neural as neural

    fen = "7k/8/8/8/8/8/8/KR5r w - - 0 1"
    rows = [{"fen": fen} for _ in range(2000)]
    monkeypatch.setattr(pilot, "_load_development", lambda _: (rows, "fixture"))
    monkeypatch.setattr(pilot, "_git_state", lambda _: {"head": "fixture"})
    monkeypatch.setattr(
        pilot,
        "verify_acquisition_manifest",
        lambda *_: {"table_sha256": {"fixture": "hash"}},
    )
    table_state = {"closed": False}

    def open_tablebase(_):
        def close():
            table_state["closed"] = True

        return SimpleNamespace(
            probe_wdl=lambda board: 0,
            probe_dtz=lambda board: 0,
            close=close,
        )

    monkeypatch.setattr(
        pilot.chess.syzygy,
        "open_tablebase",
        open_tablebase,
    )
    monkeypatch.setattr(
        pilot,
        "evaluate",
        lambda *_: SimpleNamespace(value=1, raw_wdl=2),
    )

    # Keep the real pretrainer, trainer, target builder and simulator, with a
    # single small supervised epoch and an abbreviated warmup for this test.
    original_pretraining_config = neural.PretrainingConfig
    monkeypatch.setattr(
        neural,
        "PretrainingConfig",
        lambda: replace(
            original_pretraining_config(), batch_size=1600, max_epochs=1
        ),
    )
    monkeypatch.setattr(pilot, "REPLAY_WARMUP", 8)
    monkeypatch.setattr(pilot, "UPDATE_INTERVAL", 4)
    monkeypatch.setattr(pilot, "REPLAY_BATCH_SIZE", 2)

    initial_states = []
    streams = []
    original_rng = pilot.make_rng

    def recording_rng(seed, stream):
        streams.append((seed, stream))
        return original_rng(seed, stream)

    monkeypatch.setattr(pilot, "make_rng", recording_rng)
    original_trainer = neural.RLValueTrainer

    class RecordingTrainer(original_trainer):
        def __init__(self, online, **kwargs):
            initial_states.append(
                {
                    name: value.detach().clone()
                    for name, value in online.state_dict().items()
                }
            )
            super().__init__(online, **kwargs)

    monkeypatch.setattr(neural, "RLValueTrainer", RecordingTrainer)

    acquisition = tmp_path / "acquisition.json"
    acquisition.write_text("{}", encoding="utf-8")
    output = tmp_path / "successful-pilot"
    args = argparse.Namespace(
        decisions=12,
        threads=1,
        output_dir=output,
        development_dir=tmp_path,
        acquisition_manifest=acquisition,
        tablebase_dir=tmp_path,
    )

    manifest = pilot.run_pilot(args)

    assert manifest["status"] == "complete"
    assert len(manifest["methods"]) == 3
    assert manifest["pretraining"]["untrained_validation_forward_boards"] == 400
    assert manifest["pretraining"]["frozen_validation_forward_boards"] == 400
    accounting = manifest["cost_accounting"][
        "simulator_and_online_inference_seconds"
    ]
    assert all(name in accounting for name in ("encoding", "replay", "logging"))
    assert "must not be added again" in accounting
    assert "nonterminal network leaves" in manifest["cost_accounting"][
        "target_forward_leaves"
    ]
    assert len(initial_states) == 3
    assert table_state["closed"] is True
    assert streams == [
        (pilot.PILOT_SEED, stream)
        for _ in pilot.BETAS
        for stream in ("replay", "starts", "exploration", "opponent")
    ]
    pretrained = torch.load(
        output / "pretrained-checkpoint.pt", weights_only=True
    )
    for state in initial_states:
        assert all(torch.equal(state[name], pretrained[name]) for name in pretrained)

    for beta in pilot.BETAS:
        method = json.loads((output / f"beta-{beta:.1f}.json").read_text())
        assert method["status"] == "complete"
        assert method["decisions"] == method["transitions"] == 12
        assert method["updates"] == 2
        assert method["parameters_changed"] is True
        assert method["interaction_tablebase_probe_calls"] > 0
        assert method["online_forward_boards"] > 0
        assert (
            method["target_forward_boards"]
            == method["target_forward_leaves"]
            > 0
        )
        assert method["interaction_forward_evaluations"] > 0
        assert all(
            math.isfinite(record[key])
            for record in method["update_records"]
            for key in ("loss", "gradient_norm")
        )
        assert (output / f"beta-{beta:.1f}-checkpoint.pt").is_file()

    assert (output / "initial-checkpoint.pt").is_file()
    assert (output / "resolved-config.json").is_file()
