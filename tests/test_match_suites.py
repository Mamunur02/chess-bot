import json
import random
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import chess
import pytest

import chesslab.match_suite as suite
from chesslab.agents.material_greedy import MaterialGreedyAgent
from chesslab.eval.matches import AgentPair, MatchResult, run_match
from chesslab.games import GameState
from chesslab.games.chess import ChessState
from chesslab.match_suite import (
    SuiteGame,
    main,
    match_suite_spec_from_dict,
    run_match_suite,
    summarize_match_suite,
)
from chesslab.search import SearchBudget

WHITE_MATE = "7k/8/5KQ1/8/8/8/8/1r6 w - - 0 1"
BLACK_MATE = chess.Board(WHITE_MATE).mirror().fen()


def suite_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "development-match-smoke",
        "question": "Verify outcome attribution with swapped agent colours.",
        "dataset": {
            "id": "synthetic-mates",
            "version": "1",
            "split": "development",
            "source": "Synthetic correctness fixtures, not held-out data.",
            "positions": [
                {"name": "white-mate", "fen": WHITE_MATE},
                {"name": "black-mate", "fen": BLACK_MATE},
            ],
        },
        "agents": [
            {"name": "greedy", "agent": {"kind": "material_greedy"}},
            {"name": "search", "agent": {"kind": "material_alpha_beta"}},
        ],
        "seeds": [17, 23],
        "budget": {"kind": "depth", "value": 1},
        "max_plies": 4,
    }


def load_games(output: Path) -> list[dict[str, object]]:
    return [
        json.loads(p.read_text()) for p in sorted((output / "games").glob("*.json"))
    ]


def test_round_trip_and_strict_agent_validation() -> None:
    spec = match_suite_spec_from_dict(suite_data())
    assert spec.games_planned == 8
    assert match_suite_spec_from_dict(spec.to_dict()) == spec
    data = suite_data()
    data["agents"] = [
        {"name": "one", "agent": {"kind": "random", "quiescence_depth": 1}},
        {"name": "two", "agent": {"kind": "random"}},
    ]
    with pytest.raises(ValueError, match="unknown random agent"):
        match_suite_spec_from_dict(data)
    data["agents"] = [
        {"name": "same", "agent": {"kind": "random"}},
        {"name": "same", "agent": {"kind": "random"}},
    ]
    with pytest.raises(ValueError, match="unique"):
        match_suite_spec_from_dict(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("max_plies", 0),
        ("max_plies", 1.5),
        ("seeds", [True]),
        ("seeds", [17, 17]),
        ("agents", []),
        ("unknown", 1),
    ],
)
def test_invalid_manifest_leaves_no_ambiguity(field: str, value: object) -> None:
    data = suite_data()
    data[field] = value
    with pytest.raises(ValueError):
        match_suite_spec_from_dict(data)


def test_terminal_and_duplicate_starting_positions_rejected() -> None:
    data = suite_data()
    dataset = data["dataset"]
    assert isinstance(dataset, dict)
    dataset["positions"] = [{"name": "mate", "fen": "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1"}]
    with pytest.raises(ValueError, match="non-terminal"):
        match_suite_spec_from_dict(data)
    dataset["positions"] = [
        {"name": "a", "fen": WHITE_MATE},
        {"name": "b", "fen": WHITE_MATE[:-1] + "2"},
    ]
    with pytest.raises(ValueError, match="unique"):
        match_suite_spec_from_dict(data)


def test_colour_pairs_score_white_and_black_mates_correctly(tmp_path: Path) -> None:
    spec = match_suite_spec_from_dict(suite_data())
    output = tmp_path / "suite"
    metadata = run_match_suite(spec, output, tmp_path)
    assert metadata["status"] == "completed"
    assert metadata["runs_written"] == 8
    assert metadata["active_game"] is None
    summary = json.loads((output / "summary.json").read_text())
    assert summary["completed"] == 8
    assert summary["pairs_completed"] == 4
    assert summary["total_plies"] == 8
    assert summary["unrecorded"] == summary["failed"] == summary["interrupted"] == 0
    for row in summary["agents"]:
        assert (row["wins"], row["draws"], row["losses"]) == (4, 0, 4)
        assert row["score_fraction_completed"] == 0.5
    games = load_games(output)
    for index in range(0, 8, 2):
        first, second = games[index : index + 2]
        assert first["white_agent"] == second["black_agent"]
        assert first["black_agent"] == second["white_agent"]
        assert first["pair_index"] == second["pair_index"]
        a, b = first["result"], second["result"]
        assert isinstance(a, dict) and isinstance(b, dict)
        assert a["metadata"] == b["metadata"]
    before = (output / "metadata.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_match_suite(spec, output, tmp_path)
    assert (output / "metadata.json").read_bytes() == before


def test_automatic_draws_count_as_draws(tmp_path: Path) -> None:
    data = suite_data()
    dataset = data["dataset"]
    assert isinstance(dataset, dict)
    dataset["positions"] = [
        {"name": "draw-next-ply", "fen": "7k/8/8/8/8/8/8/KR6 w - - 149 76"}
    ]
    output = tmp_path / "draws"
    assert (
        run_match_suite(match_suite_spec_from_dict(data), output, tmp_path)["status"]
        == "completed"
    )
    summary = json.loads((output / "summary.json").read_text())
    assert summary["completed"] == 4
    assert all(row["draws"] == 4 for row in summary["agents"])
    assert all(row["score_fraction_completed"] == 0.5 for row in summary["agents"])


def test_ply_limits_are_not_draws_and_random_suite_repeats(tmp_path: Path) -> None:
    data = suite_data()
    dataset = data["dataset"]
    assert isinstance(dataset, dict)
    dataset["positions"] = [{"name": "initial", "fen": chess.STARTING_FEN}]
    data["agents"] = [
        {"name": "random-a", "agent": {"kind": "random"}},
        {"name": "random-b", "agent": {"kind": "random"}},
    ]
    data["max_plies"] = 4
    spec = match_suite_spec_from_dict(data)
    first, second = tmp_path / "first", tmp_path / "second"
    assert run_match_suite(spec, first, tmp_path)["status"] == "interrupted"
    run_match_suite(spec, second, tmp_path)
    assert load_games(first) == load_games(second)
    summary = json.loads((first / "summary.json").read_text())
    assert summary["interrupted"] == 4
    assert summary["completed"] == summary["failed"] == summary["pairs_completed"] == 0
    assert all(
        row["draws"] == 0 and row["score_fraction_completed"] is None
        for row in summary["agents"]
    )


def test_agent_failures_are_recorded_without_forfeits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_action(*args: object, **kwargs: object) -> None:
        raise RuntimeError("test agent failure")

    monkeypatch.setattr(MaterialGreedyAgent, "select_action", failing_action)
    output = tmp_path / "failures"
    metadata = run_match_suite(
        match_suite_spec_from_dict(suite_data()), output, tmp_path
    )
    assert metadata["status"] == "failed"
    summary = json.loads((output / "summary.json").read_text())
    assert summary["failed"] == 4
    assert summary["completed"] == 4
    assert summary["pairs_completed"] == 0
    assert all(
        row["wins"] + row["draws"] + row["losses"] == 4 for row in summary["agents"]
    )


@pytest.mark.parametrize(
    "error,status", [(KeyboardInterrupt, "interrupted"), (RuntimeError, "failed")]
)
def test_partial_colour_pair_preserved_on_abort(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: type[BaseException],
    status: str,
) -> None:
    calls = 0

    def aborting_match(
        initial_state: GameState[chess.Move],
        agents: AgentPair[chess.Move],
        budget: SearchBudget,
        *,
        seed: int,
        max_plies: int,
        encode_action: Callable[[chess.Move], str],
    ) -> MatchResult:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise error("test abort")
        return run_match(
            initial_state,
            agents,
            budget,
            seed=seed,
            max_plies=max_plies,
            encode_action=encode_action,
        )

    monkeypatch.setattr(suite, "run_match", aborting_match)
    output = tmp_path / "partial"
    with pytest.raises(error):
        run_match_suite(match_suite_spec_from_dict(suite_data()), output, tmp_path)
    metadata = json.loads((output / "metadata.json").read_text())
    assert metadata["status"] == status
    assert metadata["runs_written"] == 1
    assert metadata["active_game"]["pair_index"] == 0
    summary = json.loads((output / "summary.json").read_text())
    assert summary["unrecorded"] == 7
    assert summary["pairs_completed"] == 0
    assert summary["pairs_without_two_completed_games"] == 4


def test_summary_rejects_games_that_do_not_match_manifest() -> None:
    spec = match_suite_spec_from_dict(suite_data())
    # Obtain the exact recorded schedule seed without duplicating RNG derivation.
    match_seed = random.Random(spec.seeds[0]).getrandbits(128)
    result = run_match(
        ChessState.from_fen(WHITE_MATE),
        (spec.agents[0].build(), spec.agents[1].build()),
        spec.budget,
        seed=match_seed,
        max_plies=spec.max_plies,
        encode_action=lambda m: m.uci(),
    )
    game = SuiteGame(0, 17, "white-mate", WHITE_MATE, "greedy", "search", result)
    assert summarize_match_suite(spec, [game])["completed"] == 1
    with pytest.raises(ValueError, match="duplicate"):
        summarize_match_suite(spec, [game, game])
    with pytest.raises(ValueError, match="inputs"):
        summarize_match_suite(spec, [replace(game, black_agent="unrelated")])


def test_cli_writes_suite_and_rejects_invalid_input_before_creating_output(
    tmp_path: Path,
) -> None:
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite_data()), encoding="utf-8")
    assert main([str(path), str(tmp_path / "out"), "--repository", str(tmp_path)]) == 0
    path.write_text('{"schema_version": 2}', encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(path), str(tmp_path / "invalid")])
    assert not (tmp_path / "invalid").exists()
