import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

import chesslab.experiment as experiment
from chesslab.agents.material_alpha_beta import MaterialAlphaBetaAgent
from chesslab.eval.benchmarks import (
    BenchmarkProvenance,
    BenchmarkResult,
    BenchmarkSpec,
    capture_provenance,
    run_benchmark,
)
from chesslab.experiment import (
    experiment_manifest_from_dict,
    main,
    run_experiment,
    summarize_experiment,
)

FREE_QUEEN = "7k/q7/8/8/8/8/8/R1K5 w - - 0 1"
TERMINAL = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"


def manifest_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "development-smoke",
        "question": "Does capture ordering change the tiny-budget fallback?",
        "dataset": {
            "id": "synthetic-fixtures",
            "version": "1",
            "split": "development",
            "source": "Synthetic test fixture, not held-out evaluation data.",
            "positions": [
                {"name": "free-queen", "fen": FREE_QUEEN, "expected_moves": ["a1a7"]}
            ],
        },
        "budget": {"kind": "nodes", "value": 1},
        "seeds": [17, 23],
        "variants": [
            {"name": "plain", "agent": {}},
            {"name": "ordered", "agent": {"capture_ordering": True}},
        ],
    }


def test_manifest_round_trip_and_paired_inputs() -> None:
    manifest = experiment_manifest_from_dict(manifest_data())
    assert experiment_manifest_from_dict(manifest.to_dict()) == manifest
    assert len(manifest.specs) == 4
    assert [s.seed for s in manifest.specs] == [17, 23, 17, 23]
    assert len({s.positions for s in manifest.specs}) == 1
    assert len({s.budget for s in manifest.specs}) == 1
    changed = copy.deepcopy(manifest.to_dict())
    dataset = changed["dataset"]
    assert isinstance(dataset, dict)
    dataset["version"] = "2"
    assert experiment_manifest_from_dict(changed).digest != manifest.digest


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("seeds", []),
        ("seeds", [True]),
        ("seeds", [17, 17]),
        ("variants", []),
        ("typo", 1),
    ],
)
def test_manifest_rejects_invalid_grid(field: str, value: object) -> None:
    data = manifest_data()
    data[field] = value
    with pytest.raises(ValueError):
        experiment_manifest_from_dict(data)


def test_manifest_rejects_unknown_search_switch_and_duplicate_names() -> None:
    data = manifest_data()
    data["variants"] = [
        {"name": "plain", "agent": {"transpostion_table": True}},
        {"name": "other", "agent": {}},
    ]
    with pytest.raises(ValueError, match="unknown agent"):
        experiment_manifest_from_dict(data)
    data["variants"] = [{"name": "plain", "agent": {}}, {"name": "plain", "agent": {}}]
    with pytest.raises(ValueError, match="unique"):
        experiment_manifest_from_dict(data)


def test_manifest_rejects_duplicate_positions_with_different_move_numbers() -> None:
    data = manifest_data()
    dataset = data["dataset"]
    assert isinstance(dataset, dict)
    dataset["positions"] = [
        {"name": "a", "fen": FREE_QUEEN},
        {"name": "b", "fen": FREE_QUEEN[:-1] + "2"},
    ]
    with pytest.raises(ValueError, match="duplicate FEN"):
        experiment_manifest_from_dict(data)
    dataset["split"] = "train"
    with pytest.raises(ValueError, match="dataset.split"):
        experiment_manifest_from_dict(data)


def test_paired_summary_preserves_seeds_and_reports_actual_move_changes(
    tmp_path: Path,
) -> None:
    manifest = experiment_manifest_from_dict(manifest_data())
    results = [
        run_benchmark(s, capture_provenance(tmp_path, s.digest)) for s in manifest.specs
    ]
    summary = summarize_experiment(manifest, results)
    assert [c.seed for r in results[:2] for c in r.cases] == [
        c.seed for r in results[2:] for c in r.cases
    ]
    pairs = summary["pairs"]
    assert isinstance(pairs, list)
    assert pairs[0]["comparable_cases"] == 2
    assert pairs[0]["unavailable_cases"] == 0
    assert pairs[0]["changed_actions"] == 2
    assert pairs[0]["node_delta"] == 0
    assert pairs[0]["completed_depth_delta"] == 0
    assert pairs[0]["expected_move_match_delta"] == 2
    with pytest.raises(ValueError, match="duplicate"):
        summarize_experiment(manifest, [results[0], results[0]])
    with pytest.raises(ValueError, match="specification"):
        summarize_experiment(
            manifest,
            [
                replace(
                    results[0],
                    spec=replace(
                        results[0].spec,
                        positions=(
                            replace(results[0].spec.positions[0], expected_moves=()),
                        ),
                    ),
                )
            ],
        )


def test_artifacts_capture_versions_lock_and_refuse_overwrite(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("test lock", encoding="utf-8")
    manifest = experiment_manifest_from_dict(manifest_data())
    output = tmp_path / "artifacts" / "smoke"
    metadata = run_experiment(manifest, output, tmp_path)
    assert metadata["status"] == "completed"
    assert metadata["dependency_lock_sha256"]
    assert metadata["dependency_versions"]
    assert metadata["runs_written"] == 4
    assert len(list((output / "runs").glob("*.json"))) == 4
    assert json.loads((output / "manifest.json").read_text()) == manifest.to_dict()
    before = (output / "metadata.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_experiment(manifest, output, tmp_path)
    assert (output / "metadata.json").read_bytes() == before


def test_failed_cases_remain_in_summary_denominators(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_action(*args: object, **kwargs: object) -> None:
        raise RuntimeError("test agent failure")

    monkeypatch.setattr(MaterialAlphaBetaAgent, "select_action", failing_action)
    manifest = experiment_manifest_from_dict(manifest_data())
    output = tmp_path / "failed"
    assert run_experiment(manifest, output, tmp_path)["status"] == "failed"
    summary = json.loads((output / "summary.json").read_text())
    assert summary["variants"][0]["cases_failed"] == 2
    assert summary["variants"][0]["scored_cases_attempted"] == 2
    assert summary["variants"][0]["expected_move_matches"] == 0
    assert summary["variants"][0]["min_completed_depth"] is None
    assert summary["pairs"][0]["comparable_cases"] == 0
    assert summary["pairs"][0]["unavailable_cases"] == 2


@pytest.mark.parametrize(
    "error,status", [(KeyboardInterrupt, "interrupted"), (RuntimeError, "failed")]
)
def test_partial_runs_preserved_on_interruption_or_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: type[BaseException],
    status: str,
) -> None:
    manifest = experiment_manifest_from_dict(manifest_data())
    original = run_benchmark
    calls = 0

    def failing_run(
        spec: BenchmarkSpec,
        provenance: BenchmarkProvenance,
    ) -> BenchmarkResult:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise error("test interruption")
        return original(spec, provenance)

    monkeypatch.setattr(experiment, "run_benchmark", failing_run)
    output = tmp_path / "partial"
    with pytest.raises(error):
        run_experiment(manifest, output, tmp_path)
    metadata = json.loads((output / "metadata.json").read_text())
    assert metadata["status"] == status
    assert metadata["runs_written"] == 1
    assert metadata["error"]
    assert metadata["dependency_lock_sha256"] is None
    assert metadata["dependency_lock_error"]
    assert (output / "runs" / "0000.json").exists()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["pairs"][0]["unavailable_cases"] == 2


def test_cli_end_to_end_and_invalid_input_leaves_no_artifacts(tmp_path: Path) -> None:
    config = tmp_path / "manifest.json"
    config.write_text(json.dumps(manifest_data()), encoding="utf-8")
    output = tmp_path / "output"
    assert main([str(config), str(output), "--repository", str(tmp_path)]) == 0
    config.write_text('{"schema_version": 99}', encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(config), str(tmp_path / "invalid")])
    assert not (tmp_path / "invalid").exists()
