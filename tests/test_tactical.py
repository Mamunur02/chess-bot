import hashlib
import json
from pathlib import Path

import pytest

import chesslab.tactical as tactical
from chesslab.agents.material_alpha_beta import MaterialAlphaBetaAgent
from chesslab.eval.benchmarks import run_benchmark
from chesslab.tactical import run_tactical, tactical_specs

POSITION = {
    "name": "free-queen",
    "fen": "7k/q7/8/8/8/8/8/R1K5 w - - 0 1",
    "expected_moves": ["a1a7"],
}
SECOND = {
    "name": "mate",
    "fen": "7k/8/5KQ1/8/8/8/8/1r6 w - - 0 1",
    "expected_moves": ["g6g7"],
}


def test_schedule_balances_order_and_preserves_paired_inputs() -> None:
    specs = tactical_specs([POSITION, SECOND], (1, 2), 2)
    assert len(specs) == 32
    assert [s.name for s in specs[:4]] == [
        "plain",
        "capture-ordering",
        "transposition-table",
        "quiescence-1",
    ]
    assert specs[8].name == "capture-ordering"
    assert specs[16].name == "capture-ordering"
    assert specs[0].positions == specs[4].positions
    assert specs[0].seed == specs[16].seed
    assert specs[0].budget != specs[8].budget


@pytest.mark.parametrize("budgets,repeats", [((1, 1), 1), ((0,), 1), ((1,), 0)])
def test_invalid_schedule_rejected(budgets: tuple[int, ...], repeats: int) -> None:
    with pytest.raises(ValueError):
        tactical_specs([POSITION], budgets, repeats)


def test_duplicate_positions_rejected() -> None:
    with pytest.raises(ValueError):
        tactical_specs([POSITION, {**POSITION, "name": "copy"}], (1,), 1)


def test_irrelevant_en_passant_and_clock_fields_do_not_hide_duplicates() -> None:
    a = {
        "name": "a",
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    }
    b = {"name": "b", "fen": a["fen"].replace("e3 0 1", "- 7 4")}
    with pytest.raises(ValueError, match="duplicate"):
        tactical_specs([a, b], (1,), 1)


def test_heldout_run_requires_explicit_protocol_before_loading_data(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="explicit frozen protocol"):
        run_tactical(
            tmp_path,
            tmp_path / "output",
            split="test",
            budgets=(1,),
            repeats=1,
            max_seconds=60,
            repository=tmp_path,
        )


def inputs(tmp_path: Path) -> tuple[Path, Path]:
    prepared, repository = tmp_path / "prepared", tmp_path / "repo"
    prepared.mkdir()
    repository.mkdir()
    (repository / "src").mkdir()
    (repository / "src" / "snapshot.py").write_text("# reproducible source\n")
    (repository / "pyproject.toml").write_text("# fixture\n")
    (repository / "uv.lock").write_text("# fixture\n")
    payload = json.dumps([POSITION]).encode()
    (prepared / "development.json").write_bytes(payload)
    (prepared / "manifest.json").write_text(
        json.dumps(
            {"split_sha256": {"development": hashlib.sha256(payload).hexdigest()}}
        )
    )
    return prepared, repository


def test_cap_resume_source_snapshot_and_no_overwrite(tmp_path: Path) -> None:
    prepared, repository = inputs(tmp_path)
    output = tmp_path / "run"
    capped = run_tactical(
        prepared,
        output,
        split="development",
        budgets=(1,),
        repeats=1,
        max_seconds=1e-12,
        repository=repository,
    )
    assert capped["status"] == "capped"
    assert capped["runs_written"] == 0
    assert (output / "sources" / "src" / "snapshot.py").exists()
    resumed = run_tactical(
        prepared,
        output,
        split="development",
        budgets=(1,),
        repeats=1,
        max_seconds=60,
        repository=repository,
        resume=True,
    )
    assert resumed["status"] == "completed"
    assert resumed["runs_written"] == 4
    first_bytes = (output / "cases" / "000000.json").read_bytes()
    run_tactical(
        prepared,
        output,
        split="development",
        budgets=(1,),
        repeats=1,
        max_seconds=60,
        repository=repository,
        resume=True,
    )
    assert first_bytes == (output / "cases" / "000000.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_tactical(
            prepared,
            output,
            split="development",
            budgets=(1,),
            repeats=1,
            max_seconds=60,
            repository=repository,
        )
    (repository / "src" / "snapshot.py").write_text("# changed\n")
    with pytest.raises(ValueError, match="resume plan/source/data"):
        run_tactical(
            prepared,
            output,
            split="development",
            budgets=(1,),
            repeats=1,
            max_seconds=60,
            repository=repository,
            resume=True,
        )


def test_corrupt_split_fails_before_creating_output(tmp_path: Path) -> None:
    prepared, repository = inputs(tmp_path)
    (prepared / "development.json").write_text("[]")
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="digest"):
        run_tactical(
            prepared,
            output,
            split="development",
            budgets=(1,),
            repeats=1,
            max_seconds=60,
            repository=repository,
        )
    assert not output.exists()


def test_interruption_records_active_case_and_can_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared, repository = inputs(tmp_path)
    original = run_benchmark

    def interrupt(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(tactical, "run_benchmark", interrupt)
    output = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        run_tactical(
            prepared,
            output,
            split="development",
            budgets=(1,),
            repeats=1,
            max_seconds=60,
            repository=repository,
        )
    metadata = json.loads((output / "metadata.json").read_text())
    assert metadata["status"] == "interrupted"
    assert metadata["active_case"] == 0
    assert metadata["runs_written"] == 0
    monkeypatch.setattr(tactical, "run_benchmark", original)
    assert (
        run_tactical(
            prepared,
            output,
            split="development",
            budgets=(1,),
            repeats=1,
            max_seconds=60,
            repository=repository,
            resume=True,
        )["status"]
        == "completed"
    )


def test_failures_stay_failed_and_are_not_retried_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared, repository = inputs(tmp_path)

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("deliberate test failure")

    monkeypatch.setattr(MaterialAlphaBetaAgent, "select_action", fail)
    output = tmp_path / "run"
    metadata = run_tactical(
        prepared,
        output,
        split="development",
        budgets=(1,),
        repeats=1,
        max_seconds=60,
        repository=repository,
    )
    assert metadata["status"] == "failed"
    assert metadata["runs_written"] == 4
    raw = json.loads((output / "cases" / "000000.json").read_text())
    assert raw["cases"][0]["status"] == "failed"
    monkeypatch.undo()
    resumed = run_tactical(
        prepared,
        output,
        split="development",
        budgets=(1,),
        repeats=1,
        max_seconds=60,
        repository=repository,
        resume=True,
    )
    assert resumed["status"] == "failed"
    assert raw == json.loads((output / "cases" / "000000.json").read_text())


def test_modified_case_is_rejected_on_resume(tmp_path: Path) -> None:
    prepared, repository = inputs(tmp_path)
    output = tmp_path / "run"
    run_tactical(
        prepared,
        output,
        split="development",
        budgets=(1,),
        repeats=1,
        max_seconds=60,
        repository=repository,
    )
    first = output / "cases" / "000000.json"
    data = json.loads(first.read_text())
    data["spec"]["seed"] = -1
    first.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="scheduled spec"):
        run_tactical(
            prepared,
            output,
            split="development",
            budgets=(1,),
            repeats=1,
            max_seconds=60,
            repository=repository,
            resume=True,
        )
