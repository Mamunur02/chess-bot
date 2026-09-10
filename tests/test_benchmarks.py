import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from chesslab.benchmark import benchmark_spec_from_dict, main
from chesslab.eval import (
    BenchmarkAgentConfig,
    BenchmarkPosition,
    BenchmarkProvenance,
    BenchmarkSpec,
    capture_provenance,
    run_benchmark,
)
from chesslab.search import DepthBudget, NodeBudget

FREE_QUEEN_FEN = "7k/q7/8/8/8/8/8/R1K5 w - - 0 1"
MATE_OR_CAPTURE_FEN = "7k/8/5KQ1/8/8/8/8/1r6 w - - 0 1"
CHECKMATE_FEN = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"


class StepClock:
    def __init__(self, step: float) -> None:
        self.current = 0.0
        self.step = step

    def __call__(self) -> float:
        value = self.current
        self.current += self.step
        return value


def fixed_provenance(digest: str) -> BenchmarkProvenance:
    return BenchmarkProvenance(
        started_at="2026-09-10T12:00:00+00:00",
        git_commit="a" * 40,
        git_dirty=False,
        git_error=None,
        python_version="3.12.14",
        platform="test-platform",
        machine="test-machine",
        processor="test-processor",
        config_digest=digest,
    )


def tactical_spec() -> BenchmarkSpec:
    return BenchmarkSpec(
        name="tactical-smoke",
        seed=17,
        budget=DepthBudget(1),
        agent=BenchmarkAgentConfig(),
        positions=(
            BenchmarkPosition(
                name="free-queen",
                fen=FREE_QUEEN_FEN,
                expected_moves=("a1a7",),
            ),
            BenchmarkPosition(
                name="mate-over-capture",
                fen=MATE_OR_CAPTURE_FEN,
                expected_moves=("g6g7",),
            ),
        ),
    )


def test_benchmark_records_raw_cases_seeds_and_exact_summary() -> None:
    spec = tactical_spec()

    result = run_benchmark(
        spec,
        fixed_provenance(spec.digest),
        clock=StepClock(0.1),
    )
    serialized = result.to_dict()

    assert [case.status for case in result.cases] == ["completed", "completed"]
    assert [case.expected_move_match for case in result.cases] == [True, True]
    assert result.cases[0].seed != result.cases[1].seed
    assert result.elapsed_seconds == pytest.approx(0.5)
    assert serialized["summary"] == {
        "positions": 2,
        "completed": 2,
        "failed": 0,
        "expected_move_cases": 2,
        "expected_move_matches": 2,
        "total_nodes": 37,
        "elapsed_seconds": pytest.approx(0.5),
    }
    assert serialized["provenance"] == fixed_provenance(spec.digest).to_dict()


def test_benchmark_seed_stream_and_digest_are_reproducible() -> None:
    first_spec = tactical_spec()
    repeated_spec = tactical_spec()

    first = run_benchmark(
        first_spec,
        fixed_provenance(first_spec.digest),
        clock=StepClock(0.1),
    )
    repeated = run_benchmark(
        repeated_spec,
        fixed_provenance(repeated_spec.digest),
        clock=StepClock(0.1),
    )

    assert first_spec.digest == repeated_spec.digest
    assert [case.seed for case in first.cases] == [case.seed for case in repeated.cases]
    assert [case.decision for case in first.cases] == [
        case.decision for case in repeated.cases
    ]


def test_terminal_position_is_recorded_as_failure_not_draw() -> None:
    spec = BenchmarkSpec(
        name="failure-smoke",
        seed=0,
        budget=NodeBudget(1),
        agent=BenchmarkAgentConfig(),
        positions=(BenchmarkPosition("terminal", CHECKMATE_FEN),),
    )

    result = run_benchmark(
        spec,
        fixed_provenance(spec.digest),
        clock=StepClock(0.1),
    )

    assert result.cases[0].status == "failed"
    assert result.cases[0].decision is None
    assert result.cases[0].error is not None
    assert "terminal state" in result.cases[0].error
    assert result.to_dict()["summary"] == {
        "positions": 1,
        "completed": 0,
        "failed": 1,
        "expected_move_cases": 0,
        "expected_move_matches": 0,
        "total_nodes": 0,
        "elapsed_seconds": pytest.approx(0.3),
    }


def test_benchmark_rejects_mismatched_provenance_digest() -> None:
    spec = tactical_spec()

    with pytest.raises(ValueError, match="digest does not match"):
        run_benchmark(
            spec,
            fixed_provenance("wrong-digest"),
            clock=StepClock(0.1),
        )


def test_agent_config_requires_real_booleans() -> None:
    with pytest.raises(ValueError, match="boolean"):
        BenchmarkAgentConfig(capture_ordering=1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "positions, message",
    [
        ((), "at least one"),
        (
            (
                BenchmarkPosition("duplicate", FREE_QUEEN_FEN),
                BenchmarkPosition("duplicate", MATE_OR_CAPTURE_FEN),
            ),
            "unique",
        ),
    ],
)
def test_benchmark_requires_named_unique_positions(
    positions: tuple[BenchmarkPosition, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        BenchmarkSpec(
            name="invalid",
            seed=0,
            budget=DepthBudget(1),
            agent=BenchmarkAgentConfig(),
            positions=positions,
        )


def test_material_greedy_can_run_as_explicit_benchmark_baseline() -> None:
    spec = BenchmarkSpec(
        name="greedy-smoke",
        seed=0,
        budget=NodeBudget(1),
        agent=BenchmarkAgentConfig(kind="material_greedy"),
        positions=(
            BenchmarkPosition(
                "free-queen",
                FREE_QUEEN_FEN,
                expected_moves=("a1a7",),
            ),
        ),
    )

    result = run_benchmark(
        spec,
        fixed_provenance(spec.digest),
        clock=StepClock(0.1),
    )

    assert result.cases[0].expected_move_match is True
    assert result.cases[0].decision is not None
    assert result.cases[0].decision.nodes == 13


def test_material_greedy_rejects_alpha_beta_switches() -> None:
    with pytest.raises(ValueError, match="does not accept"):
        BenchmarkAgentConfig(kind="material_greedy", capture_ordering=True)


def test_expected_moves_must_be_legal_in_the_position() -> None:
    with pytest.raises(ValueError, match="not legal"):
        BenchmarkPosition(
            name="bad-answer",
            fen=FREE_QUEEN_FEN,
            expected_moves=("a1a8",),
        )


def test_json_configuration_parser_builds_explicit_switches() -> None:
    spec = benchmark_spec_from_dict(
        {
            "name": "parsed",
            "seed": 4,
            "budget": {"kind": "nodes", "value": 12},
            "agent": {
                "capture_ordering": True,
                "transposition_table": True,
                "quiescence_depth": 1,
            },
            "positions": [{"name": "free-queen", "fen": FREE_QUEEN_FEN}],
        }
    )

    assert spec.budget == NodeBudget(12)
    assert spec.agent == BenchmarkAgentConfig(True, True, 1)
    assert spec.agent.kind == "material_alpha_beta"
    assert spec.positions == (BenchmarkPosition("free-queen", FREE_QUEEN_FEN),)


@pytest.mark.parametrize(
    "budget",
    [
        {"kind": "unknown", "value": 1},
        {"kind": "nodes", "value": 0},
        {"kind": "nodes", "value": True},
    ],
)
def test_json_configuration_rejects_invalid_budgets(
    budget: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        benchmark_spec_from_dict(
            {
                "name": "invalid",
                "seed": 0,
                "budget": budget,
                "positions": [{"name": "free-queen", "fen": FREE_QUEEN_FEN}],
            }
        )


def test_provenance_records_git_failure_and_runtime_environment(
    tmp_path: Path,
) -> None:
    provenance = capture_provenance(
        tmp_path / "missing-repository",
        "digest",
        now=lambda: datetime(2026, 9, 10, 12, tzinfo=UTC),
    )

    assert provenance.started_at == "2026-09-10T12:00:00+00:00"
    assert provenance.git_commit is None
    assert provenance.git_dirty is None
    assert provenance.git_error is not None
    assert provenance.python_version
    assert provenance.platform
    assert provenance.config_digest == "digest"


def test_cli_writes_json_result_from_caller_supplied_positions(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    config_path.write_text(
        json.dumps(
            {
                "name": "cli-smoke",
                "seed": 5,
                "budget": {"kind": "depth", "value": 1},
                "positions": [
                    {
                        "name": "free-queen",
                        "fen": FREE_QUEEN_FEN,
                        "expected_moves": ["a1a7"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main([str(config_path), str(output_path), "--repository", str(tmp_path)]) == 0
    )

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["spec"]["name"] == "cli-smoke"
    assert result["summary"]["completed"] == 1
    assert result["summary"]["expected_move_matches"] == 1
    assert result["provenance"]["config_digest"]


def test_cli_refuses_to_overwrite_existing_result(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    config_path.write_text(
        json.dumps(
            {
                "name": "cli-smoke",
                "seed": 5,
                "budget": {"kind": "depth", "value": 1},
                "positions": [
                    {
                        "name": "free-queen",
                        "fen": FREE_QUEEN_FEN,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path.write_text("preserve me", encoding="utf-8")

    with pytest.raises(SystemExit):
        main([str(config_path), str(output_path), "--repository", str(tmp_path)])

    assert output_path.read_text(encoding="utf-8") == "preserve me"
