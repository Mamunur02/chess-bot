"""Small semantic tests for shared tactics; no engine binary or data download."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import chess
import pytest

import chesslab.compare_tactics as comparison
from chesslab.agents import AgentDecision
from chesslab.agents.external_uci import ExternalUciAgent, UciConfig
from chesslab.agents.material_greedy import MaterialGreedyAgent
from chesslab.compare_tactics import (
    comparison_spec_from_dict,
    main,
    run_case,
    run_comparison,
    summarize_comparison,
)
from chesslab.match_suite import MatchAgentConfig
from chesslab.search import DepthBudget

WHITE_MATE = "7k/8/5KQ1/8/8/8/8/1r6 w - - 0 1"


def manifest() -> dict[str, object]:
    board = chess.Board(WHITE_MATE)
    expected = []
    for move in board.legal_moves:
        child = board.copy()
        child.push(move)
        if child.is_checkmate():
            expected.append(move.uci())
    return {
        "schema_version": 1,
        "name": "shared-tactics-test",
        "question": "Check pairing",
        "dataset": {
            "id": "synthetic",
            "version": "1",
            "split": "development",
            "source": "synthetic fixtures only",
            "positions": [
                {"name": "white-mate", "fen": WHITE_MATE, "expected_moves": expected},
                {
                    "name": "black-mate",
                    "fen": board.mirror().fen(),
                    "expected_moves": [
                        chess.Move(
                            chess.square_mirror(chess.Move.from_uci(m).from_square),
                            chess.square_mirror(chess.Move.from_uci(m).to_square),
                        ).uci()
                        for m in expected
                    ],
                },
            ],
        },
        "agents": [
            {"name": "greedy", "agent": {"kind": "material_greedy"}},
            {"name": "search", "agent": {"kind": "material_alpha_beta"}},
        ],
        "seeds": [17, 23],
        "budget": {"kind": "depth", "value": 1},
    }


def test_round_trip_counterbalanced_order_and_equal_seeds() -> None:
    spec = comparison_spec_from_dict(manifest())
    assert comparison_spec_from_dict(spec.to_dict()) == spec
    schedule = spec.schedule()
    assert len(schedule) == 8
    assert [agent.name for _, _, _, agent in schedule] == [
        "greedy",
        "search",
        "search",
        "greedy",
        "search",
        "greedy",
        "greedy",
        "search",
    ]
    assert schedule[0][1] == schedule[1][1]
    assert schedule[0][1] != schedule[2][1]


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("agents", []),
        ("seeds", [True]),
        ("seeds", [1, 1]),
        ("budget", {"kind": "depth", "value": 1, "typo": 1}),
        ("typo", 1),
    ],
)
def test_reject_ambiguous_manifest(field: str, value: object) -> None:
    data = manifest()
    data[field] = value
    with pytest.raises(ValueError):
        comparison_spec_from_dict(data)


@pytest.mark.parametrize("moves", [[], ["g6g8", "g6g8"], ["a1a8"], [1]])
def test_labels_required_legal_and_unique(moves: list[object]) -> None:
    data = manifest()
    dataset = data["dataset"]
    assert isinstance(dataset, dict)
    dataset["positions"][0]["expected_moves"] = moves
    with pytest.raises(ValueError):
        comparison_spec_from_dict(data)


def test_duplicate_position_not_extra_sample() -> None:
    data = manifest()
    dataset = data["dataset"]
    assert isinstance(dataset, dict)
    dataset["positions"][1] = dict(dataset["positions"][0], name="duplicate")
    with pytest.raises(ValueError, match="duplicate position"):
        comparison_spec_from_dict(data)


def test_all_mating_labels_black_perspective_and_source_snapshots(
    tmp_path: Path,
) -> None:
    spec = comparison_spec_from_dict(manifest())
    output = tmp_path / "run"
    metadata = run_comparison(spec, output, Path.cwd())
    assert metadata["status"] == "completed" and metadata["runs_written"] == 8
    assert metadata["source_sha256"] and metadata["active_case"] is None
    summary = json.loads((output / "summary.json").read_text())
    assert summary["recorded"] == 8
    assert summary["missing"] == summary["failed"] == summary["interrupted"] == 0
    for row in summary["agents"]:
        assert row["accepted_first_moves"] == row["completed"] == row["planned"] == 4
        assert row["agreement_fraction_planned"] == 1
    pairs = summary["paired_with_first_agent"]
    assert isinstance(pairs, list)
    assert pairs[0]["complete_pairs"] == 4
    raw = json.loads((output / "cases/0001.json").read_text())
    assert raw["elapsed_seconds"] >= 0 and raw["diagnostics"]["nodes"] > 0
    before = (output / "metadata.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_comparison(spec, output, Path.cwd())
    assert (output / "metadata.json").read_bytes() == before


def test_failures_and_missing_pairs_keep_planned_denominators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object) -> None:
        raise TimeoutError("synthetic decision failure")

    spec = comparison_spec_from_dict(manifest())
    schedule = spec.schedule()
    good = run_case(1, *schedule[1], spec.budget)
    monkeypatch.setattr(MaterialGreedyAgent, "select_action", fail)
    bad = run_case(0, *schedule[0], spec.budget)
    assert bad.agreement is None and bad.action is None
    assert bad.phase == "decision" and bad.elapsed_seconds is not None
    summary = summarize_comparison(spec, [good, bad])
    assert summary["failed"] == 1 and summary["missing"] == 6
    rows = summary["agents"]
    assert isinstance(rows, list)
    assert rows[1]["agreement_fraction_planned"] == 0.25
    assert rows[1]["agreement_fraction_completed"] == 1.0
    pairs = summary["paired_with_first_agent"]
    assert isinstance(pairs, list)
    assert pairs[0]["complete_pairs"] == 0
    with pytest.raises(ValueError, match="duplicate"):
        summarize_comparison(spec, [good, good])
    with pytest.raises(ValueError, match="inputs"):
        summarize_comparison(spec, [replace(good, seed=1)])
    with pytest.raises(ValueError, match="inconsistent"):
        summarize_comparison(spec, [replace(good, agreement=False)])
    with pytest.raises(ValueError, match="timing"):
        summarize_comparison(spec, [replace(good, elapsed_seconds=float("nan"))])


def test_illegal_decision_fails_instead_of_becoming_a_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        MaterialGreedyAgent,
        "select_action",
        lambda *a: AgentDecision(chess.Move.from_uci("a1a8")),
    )
    spec = comparison_spec_from_dict(manifest())
    case = run_case(0, *spec.schedule()[0], spec.budget)
    assert case.agreement is None and case.action is None
    assert "illegal action" in str(case.error)


def test_external_setup_excluded_and_cleanup_error_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = comparison_spec_from_dict(manifest())
    config = MatchAgentConfig("external", external=UciConfig("fake", "0" * 64, {}))
    clock = iter([0.0, 10.0, 10.0, 10.05])
    monkeypatch.setattr(comparison, "perf_counter", lambda: next(clock))
    monkeypatch.setattr(ExternalUciAgent, "prepare", lambda self: None)
    monkeypatch.setattr(
        ExternalUciAgent,
        "select_action",
        lambda self, state, *a: AgentDecision(
            chess.Move.from_uci(spec.positions[0].expected_moves[0])
        ),
    )

    def close(self: ExternalUciAgent) -> None:
        self.metadata["cleanup_error"] = "quit timeout"

    monkeypatch.setattr(ExternalUciAgent, "close", close)
    case = run_case(0, 17, 1, spec.positions[0], config, DepthBudget(1))
    assert case.error is None and case.setup_seconds == 10.0
    assert case.elapsed_seconds == pytest.approx(0.05)
    assert case.engine["cleanup_error"] == "quit timeout"


def test_setup_failure_still_closes_external_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(self: ExternalUciAgent) -> None:
        raise OSError("engine unavailable")

    monkeypatch.setattr(ExternalUciAgent, "prepare", fail)
    spec = comparison_spec_from_dict(manifest())
    case = run_case(
        0,
        17,
        1,
        spec.positions[0],
        MatchAgentConfig("external", external=UciConfig("fake", "0" * 64, {})),
        spec.budget,
    )
    assert case.phase == "setup" and case.elapsed_seconds is None
    assert case.engine["closed"] and "engine unavailable" in str(case.error)


def test_keyboard_interrupt_preserves_attempt_and_stops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def interrupt(*args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(MaterialGreedyAgent, "select_action", interrupt)
    spec = comparison_spec_from_dict(manifest())
    output = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        run_comparison(spec, output, Path.cwd())
    metadata = json.loads((output / "metadata.json").read_text())
    summary = json.loads((output / "summary.json").read_text())
    assert metadata["status"] == "interrupted" and metadata["runs_written"] == 1
    assert summary["interrupted"] == 1 and summary["missing"] == 7
    assert summary["failed"] == 0


def test_external_runner_mixed_failures_keep_provenance_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data = manifest()
    data["agents"] = [
        {"name": "greedy", "agent": {"kind": "material_greedy"}},
        {"name": "external", "agent": UciConfig("fake", "0" * 64, {}).to_dict()},
    ]

    def prepare(self: ExternalUciAgent) -> None:
        self.metadata.update(
            identity={"name": "offline-engine"}, executable_sha256=self.config.sha256
        )

    def select(
        self: ExternalUciAgent, state: object, *args: object
    ) -> AgentDecision[chess.Move]:
        from chesslab.games.chess import ChessState

        assert isinstance(state, ChessState)
        if state.current_player == 1:
            raise TimeoutError("synthetic engine timeout")
        return AgentDecision(state.legal_actions()[0])

    monkeypatch.setattr(ExternalUciAgent, "prepare", prepare)
    monkeypatch.setattr(ExternalUciAgent, "select_action", select)
    output = tmp_path / "external"
    spec = comparison_spec_from_dict(data)
    metadata = run_comparison(spec, output, Path.cwd())
    assert metadata["status"] == "failed"
    summary = json.loads((output / "summary.json").read_text())
    assert summary["failed"] == 2 and summary["missing"] == 0
    raw = [json.loads(p.read_text()) for p in (output / "cases").glob("*.json")]
    assert all(c["engine"]["closed"] for c in raw if c["agent"] == "external")
    subprocess.run(
        [
            sys.executable,
            "scripts/summarise_tactical_comparison.py",
            str(output),
            str(tmp_path / "external-summary.json"),
        ],
        check=True,
        capture_output=True,
    )


def test_cli_validates_before_creating_output(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version": false}')
    with pytest.raises(SystemExit):
        main([str(path), str(tmp_path / "out")])
    assert not (tmp_path / "out").exists()


def test_audit_script_reaggregates_and_rejects_tampering(tmp_path: Path) -> None:
    output = tmp_path / "run"
    run_comparison(comparison_spec_from_dict(manifest()), output, Path.cwd())
    command = [sys.executable, "scripts/summarise_tactical_comparison.py", str(output)]
    compact = tmp_path / "compact.json"
    subprocess.run([*command, str(compact)], check=True, capture_output=True)
    assert json.loads(compact.read_text())["audit"]["source_snapshots"] == "passed"
    path = output / "cases/0000.json"
    data = json.loads(path.read_text())
    data["agreement"] = False
    path.write_text(json.dumps(data))
    rejected = tmp_path / "rejected.json"
    result = subprocess.run([*command, str(rejected)], capture_output=True)
    assert result.returncode != 0
    assert not rejected.exists()
