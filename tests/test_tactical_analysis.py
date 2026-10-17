import copy
import hashlib
import json
import runpy
from pathlib import Path
from typing import Any

import pytest

from chesslab.eval.artifacts import configuration_digest, write_artifact_json
from chesslab.tactical import VARIANTS, run_tactical

ANALYSIS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "analyse_tactical.py")
)


def test_linear_percentiles_and_shared_paired_bootstrap() -> None:
    percentile = ANALYSIS["percentile"]
    bootstrap = ANALYSIS["paired_intervals"]
    assert percentile([0.0, 10.0], 0.025) == pytest.approx(0.25)
    assert percentile([10.0, 0.0], 0.975) == pytest.approx(9.75)
    assert percentile([3.0], 0.5) == 3.0
    assert bootstrap([[1, 1], [-1, -1]], seed=17, replicates=20) == [
        (100.0, 100.0),
        (-100.0, -100.0),
    ]
    a = bootstrap([[1, -1], [1, -1]], seed=17, replicates=100)
    assert a[0] == a[1]
    assert a == bootstrap([[1, -1], [1, -1]], seed=17, replicates=100)
    with pytest.raises(ValueError):
        bootstrap([[1], [1, 0]], seed=17, replicates=10)
    with pytest.raises(ValueError):
        percentile([], 0.5)


def test_logging_amendment_is_separate_and_rejects_tampering(tmp_path: Path) -> None:
    plan = {"code_sha256": {"src/chesslab/eval/artifacts.py": "original-hash"}}
    verify = ANALYSIS["load_logging_amendment"]
    assert verify(tmp_path, plan) is None
    recovery = tmp_path / "recovery-v2"
    recovery.mkdir()
    writer = recovery / "logging-writer.py"
    launcher = recovery / "launcher.py"
    writer.write_bytes(b"fixed writer")
    launcher.write_bytes(b"launcher")
    amendment = {
        "old_writer_sha256": "original-hash",
        "new_writer_sha256": hashlib.sha256(writer.read_bytes()).hexdigest(),
        "launcher_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
        "original_plan_digest": configuration_digest(plan),
    }
    write_artifact_json(recovery / "amendment.json", amendment)
    assert verify(tmp_path, plan) == amendment
    writer.write_bytes(b"changed")
    with pytest.raises(ValueError, match="amendment source digest"):
        verify(tmp_path, plan)


def fixture_cells() -> tuple[dict[str, Any], list[dict[str, Any]], dict[Any, Any]]:
    plan = {"budgets": [5000], "repeats": 3, "split": "synthetic-test-fixture"}
    positions = [{"name": "a"}, {"name": "b"}]
    outcomes = [[1, 0], [0, 1], [1, 0], [1, 1]]
    ratios = [1, 2, 0.5, 1.5]
    cells = {}
    for index, (variant, _) in enumerate(VARIANTS):
        for pos, success in zip(positions, outcomes[index], strict=True):
            cells[(variant, 5000, pos["name"])] = [
                {
                    "status": "completed",
                    "expected_move_match": bool(success),
                    "elapsed_seconds": time * ratios[index],
                    "decision": {
                        "action": "a1a7",
                        "value": 900,
                        "nodes": 5000,
                        "depth": 3,
                        "cutoffs": 10,
                        "transposition_hits": 0,
                        "quiescence_nodes": 0,
                        "search_elapsed_seconds": None,
                    },
                }
                for time in (1, 2, 100)
            ]
    return plan, positions, cells


def test_first_pass_quality_repeated_medians_and_discordant_pairs() -> None:
    plan, positions, cells = fixture_cells()
    summary = ANALYSIS["summarize"](plan, positions, cells, replicates=100)
    assert summary["positions"] == 2
    assert summary["status"] == "validated"
    plain = summary["variants"][0]
    assert plain["first_successes"] == 1
    assert plain["first_agreement_percent"] == 50
    assert plain["median_case_seconds"] == 2
    ordering = summary["contrasts"][0]
    assert ordering["complete_pair_delta_pp"] == 0
    assert ordering["candidate_only_success"] == 1
    assert ordering["reference_only_success"] == 1
    assert ordering["median_paired_runtime_ratio"] == 2
    assert summary["contrasts"][2]["complete_pair_delta_pp"] == 50


def test_missing_pairs_keep_denominators_bounds_and_exclusions() -> None:
    plan, positions, cells = fixture_cells()
    cells[("capture-ordering", 5000, "a")][0] = None
    summary = ANALYSIS["summarize"](plan, positions, cells, replicates=100)
    row = summary["variants"][1]
    assert row["planned_positions"] == 2
    assert row["first_successes"] == 1
    assert row["first_missing"] == 1
    assert row["complete_timing_positions"] == 1
    paired = summary["contrasts"][0]
    assert paired["complete_pairs"] == 1
    assert paired["missing_outcome_lower_pp"] == 0
    assert paired["missing_outcome_upper_pp"] == 50
    assert summary["status"] == "needs_investigation"


def test_repeated_decision_disagreement_is_not_silently_aggregated() -> None:
    plan, positions, cells = fixture_cells()
    cells[("plain", 5000, "a")][1]["decision"]["value"] = 100
    summary = ANALYSIS["summarize"](plan, positions, cells, replicates=50)
    assert summary["status"] == "needs_investigation"
    assert summary["nondeterministic_conditions"] == [
        {"variant": "plain", "budget": 5000, "position": "a"}
    ]


def make_run(tmp_path: Path) -> Path:
    prepared, repository = tmp_path / "prepared", tmp_path / "repo"
    prepared.mkdir()
    (repository / "src").mkdir(parents=True)
    (repository / "src" / "fixture.py").write_text("# test snapshot\n")
    (repository / "pyproject.toml").write_text("# fixture\n")
    (repository / "uv.lock").write_text("# fixture\n")
    position = {
        "name": "free-queen",
        "game_id": "fixture1",
        "fen": "7k/q7/8/8/8/8/8/R1K5 w - - 0 1",
        "expected_moves": ["a1a7"],
    }
    write_artifact_json(prepared / "development.json", [position])
    digest = hashlib.sha256((prepared / "development.json").read_bytes()).hexdigest()
    write_artifact_json(
        prepared / "manifest.json", {"split_sha256": {"development": digest}}
    )
    output = tmp_path / "run"
    run_tactical(
        prepared,
        output,
        split="development",
        budgets=(1,),
        repeats=2,
        max_seconds=60,
        repository=repository,
    )
    return output


def test_loader_verifies_real_run_and_rejects_tampered_decision(tmp_path: Path) -> None:
    output = make_run(tmp_path)
    plan, _, positions, cells = ANALYSIS["load_run"](output)
    summary = ANALYSIS["summarize"](plan, positions, cells, replicates=100)
    assert summary["status"] == "validated"
    assert len(cells) == 4
    path = output / "cases" / "000000.json"
    data = json.loads(path.read_text())
    original = copy.deepcopy(data)
    data["cases"][0]["decision"]["action"] = "a1a8"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="illegal"):
        ANALYSIS["load_run"](output)
    path.write_text(json.dumps(original))
    snapshot = output / "sources" / "src" / "fixture.py"
    snapshot.write_text("# changed\n")
    with pytest.raises(ValueError, match="snapshot"):
        ANALYSIS["load_run"](output)


def test_loader_rejects_unfinished_run_and_label_mismatch(tmp_path: Path) -> None:
    output = make_run(tmp_path)
    case = output / "cases" / "000000.json"
    record = json.loads(case.read_text())
    record["cases"][0]["expected_move_match"] = not record["cases"][0][
        "expected_move_match"
    ]
    case.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="frozen labels"):
        ANALYSIS["load_run"](output)
    meta = output / "metadata.json"
    record = json.loads(meta.read_text())
    record["status"] = "running"
    meta.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="completed run"):
        ANALYSIS["load_run"](output)
