"""Offline UCI adapter tests: no third-party engine or network required."""

import asyncio
import json
import random
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from typing import cast

import chess
import chess.engine
import pytest

import chesslab.agents.external_uci as uci
from chesslab.agents.external_uci import ExternalUciAgent, UciConfig, file_sha256
from chesslab.games.chess import ChessState
from chesslab.match_suite import match_suite_spec_from_dict, run_match_suite
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget


class FakeEngine:
    def __init__(self) -> None:
        self.id = {"name": "offline-test-engine", "author": "test"}
        self.options = {
            "Threads": chess.engine.Option("Threads", "spin", 1, 1, 16, None)
        }
        self.configured: object = None
        self.quit_calls = 0
        self.close_calls = 0
        self.configure_error: Exception | None = None
        self.quit_error: Exception | None = None

    def configure(self, options: object) -> None:
        if self.configure_error:
            raise self.configure_error
        self.configured = options

    def ping(self) -> None:
        pass

    def quit(self) -> None:
        self.quit_calls += 1
        if self.quit_error:
            raise self.quit_error

    def close(self) -> None:
        self.close_calls += 1


@pytest.fixture
def config(tmp_path: Path) -> UciConfig:
    binary = tmp_path / "fake-engine"
    binary.write_bytes(b"not executable: process creation is mocked")
    asset = tmp_path / "network.nnue"
    asset.write_bytes(b"fixture network")
    return UciConfig(
        str(binary), file_sha256(binary), {"Threads": 1}, 0.1, (str(asset),)
    )


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> FakeEngine:
    fake = FakeEngine()
    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda *a, **kw: fake)
    monkeypatch.setattr(
        uci,
        "bounded_play",
        lambda e, b, *a: chess.engine.PlayResult(
            next(iter(b.legal_moves)), None, {"nodes": 7, "depth": 2, "time": 0.01}
        ),
    )
    return fake


@pytest.mark.parametrize(
    "budget,expected",
    [
        (DepthBudget(3), chess.engine.Limit(depth=3)),
        (NodeBudget(100), chess.engine.Limit(nodes=100)),
        (TimeBudget(250), chess.engine.Limit(time=0.25)),
    ],
)
def test_budget_translation(budget: SearchBudget, expected: chess.engine.Limit) -> None:
    assert uci.uci_limit(budget) == expected


def test_history_copy_and_game_scoped_lifecycle(
    config: UciConfig,
    engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ChessState()
    for text in ("g1f3", "g8f6", "f3g1", "f6g8"):
        state = state.apply(chess.Move.from_uci(text))
    board = state.to_board()
    board.push_uci("e2e4")
    assert len(state.to_board().move_stack) == 4
    seen: list[object] = []

    def play(
        e: object, b: chess.Board, limit: object, game: object, timeout: float
    ) -> chess.engine.PlayResult:
        assert len(b.move_stack) == 4
        assert b.is_repetition(2)
        seen.append(game)
        return chess.engine.PlayResult(chess.Move.from_uci("e2e4"), None)

    monkeypatch.setattr(uci, "bounded_play", play)
    agent = ExternalUciAgent(config)
    for _ in range(2):
        agent.select_action(state, NodeBudget(20), random.Random(17))
    assert seen[0] is seen[1]
    assert engine.configured == {"Threads": 1}
    assert agent.metadata["identity"] == engine.id
    assert agent.metadata["assets"]
    agent.close()
    agent.close()
    assert (engine.quit_calls, engine.close_calls) == (1, 1)
    with pytest.raises(RuntimeError, match="closed"):
        agent.select_action(state, NodeBudget(1), random.Random(17))


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("watchdog"),
        chess.engine.EngineTerminatedError("crash"),
        chess.engine.EngineError("bad protocol"),
    ],
)
def test_play_failure_closes_engine(
    config: UciConfig,
    engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def fail(*args: object) -> None:
        raise error

    monkeypatch.setattr(uci, "bounded_play", fail)
    agent = ExternalUciAgent(config)
    with pytest.raises(type(error)):
        agent.select_action(ChessState(), DepthBudget(1), random.Random(0))
    assert agent.metadata["status"] == "failed"
    assert agent.closed and engine.close_calls == 1


@pytest.mark.parametrize("move", [None, chess.Move.from_uci("e2e5"), chess.Move.null()])
def test_missing_or_illegal_move_is_failure(
    config: UciConfig,
    engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
    move: chess.Move | None,
) -> None:
    monkeypatch.setattr(
        uci, "bounded_play", lambda *a: chess.engine.PlayResult(move, None)
    )
    agent = ExternalUciAgent(config)
    with pytest.raises(ValueError, match="no legal move"):
        agent.select_action(ChessState(), DepthBudget(1), random.Random(0))
    assert engine.close_calls == 1


def test_configuration_and_cleanup_failures_retained(
    config: UciConfig, engine: FakeEngine
) -> None:
    engine.configure_error = chess.engine.EngineError("unsupported option")
    engine.quit_error = TimeoutError("quit hung")
    agent = ExternalUciAgent(config)
    with pytest.raises(chess.engine.EngineError, match="unsupported option"):
        agent.select_action(ChessState(), DepthBudget(1), random.Random(0))
    assert engine.close_calls == 1
    assert "quit hung" in str(agent.metadata["cleanup_error"])


def test_prepare_is_idempotent_and_keeps_engine_for_decision(
    config: UciConfig,
    engine: FakeEngine,
) -> None:
    agent = ExternalUciAgent(config)
    agent.prepare()
    original = agent.engine
    agent.prepare()
    assert agent.engine is original
    assert "startup_seconds" in agent.metadata
    agent.select_action(ChessState(), DepthBudget(1), random.Random(0))
    assert len(agent.decisions) == 1
    agent.close()
    assert engine.close_calls == 1


def test_hash_mismatch_prevents_process_launch(
    config: UciConfig, engine: FakeEngine
) -> None:
    Path(config.path).write_bytes(b"changed")
    agent = ExternalUciAgent(config)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        agent.select_action(ChessState(), DepthBudget(1), random.Random(0))
    assert agent.engine is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "x"),
        ("timeout_seconds", True),
        ("timeout_seconds", 0),
        ("timeout_seconds", float("nan")),
        ("options", {"Threads": 1.5}),
        ("options", {"MultiPV": 1}),
        ("assets", "file"),
        ("typo", 1),
    ],
)
def test_config_strict_validation(config: UciConfig, field: str, value: object) -> None:
    data = config.to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        UciConfig.from_dict(data)


def test_watchdog_bounds_node_search_without_an_engine_binary() -> None:
    loop = asyncio.new_event_loop()
    thread = Thread(target=loop.run_forever)
    thread.start()

    async def hung(*args: object, **kwargs: object) -> chess.engine.PlayResult:
        await asyncio.sleep(60)
        raise AssertionError("watchdog did not fire")

    fake = SimpleNamespace(protocol=SimpleNamespace(loop=loop, play=hung))
    try:
        with pytest.raises(TimeoutError):
            uci.bounded_play(
                cast(chess.engine.SimpleEngine, fake),
                chess.Board(),
                chess.engine.Limit(nodes=10),
                object(),
                0.01,
            )
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        loop.close()


def test_external_suite_failures_and_cleanup_are_in_denominator(
    config: UciConfig,
    engine: FakeEngine,
    tmp_path: Path,
) -> None:
    data = {
        "schema_version": 1,
        "name": "offline-external",
        "question": "Lifecycle smoke",
        "dataset": {
            "id": "fixture",
            "version": "1",
            "source": "synthetic",
            "split": "development",
            "positions": [{"name": "initial", "fen": chess.STARTING_FEN}],
        },
        "agents": [
            {"name": "our", "agent": {"kind": "random"}},
            {"name": "external", "agent": config.to_dict()},
        ],
        "seeds": [17],
        "budget": {"kind": "nodes", "value": 10},
        "max_plies": 2,
    }
    spec = match_suite_spec_from_dict(data)
    assert match_suite_spec_from_dict(spec.to_dict()) == spec
    engine.configure_error = chess.engine.EngineError("invalid settings")
    output = tmp_path / "out"
    result = run_match_suite(spec, output, Path.cwd())
    assert result["status"] == "failed"
    assert result["source_sha256"]
    summary = json.loads((output / "summary.json").read_text())
    assert summary["failed"] == 2
    assert summary["completed"] == summary["unrecorded"] == 0
    games = [json.loads(p.read_text()) for p in (output / "games").glob("*.json")]
    assert len(games) == 2
    for game in games:
        assert game["result"]["failure"]["kind"] == "agent_error"
        assert game["engines"]["external"]["closed"]
    assert engine.close_calls == 2


def test_process_start_failure_is_retained(
    config: UciConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("cannot start executable")

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", fail)
    agent = ExternalUciAgent(config)
    with pytest.raises(OSError, match="cannot start"):
        agent.select_action(ChessState(), DepthBudget(1), random.Random(0))
    assert agent.engine is None and agent.closed
    assert agent.metadata["status"] == "failed"


def test_keyboard_interrupt_still_closes_engine(
    config: UciConfig,
    engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(uci, "bounded_play", fail)
    agent = ExternalUciAgent(config)
    with pytest.raises(KeyboardInterrupt):
        agent.select_action(ChessState(), DepthBudget(1), random.Random(0))
    assert engine.close_calls == 1


def test_successful_external_suite_records_timing_and_ply_caps(
    config: UciConfig,
    engine: FakeEngine,
    tmp_path: Path,
) -> None:
    data = {
        "schema_version": 1,
        "name": "offline-success",
        "question": "Ply cap smoke",
        "dataset": {
            "id": "fixture",
            "version": "1",
            "source": "synthetic",
            "split": "development",
            "positions": [{"name": "initial", "fen": chess.STARTING_FEN}],
        },
        "agents": [
            {"name": "our", "agent": {"kind": "random"}},
            {"name": "external", "agent": config.to_dict()},
        ],
        "seeds": [17],
        "budget": {"kind": "nodes", "value": 10},
        "max_plies": 2,
    }
    output = tmp_path / "out"
    result = run_match_suite(match_suite_spec_from_dict(data), output, Path.cwd())
    assert result["status"] == "interrupted"
    summary = json.loads((output / "summary.json").read_text())
    assert summary["interrupted"] == 2
    assert summary["completed"] == summary["failed"] == 0
    assert all(a["draws"] == 0 and a["timed_decisions"] == 2 for a in summary["agents"])
    assert engine.close_calls == 2
    games = [json.loads(p.read_text()) for p in (output / "games").glob("*.json")]
    for game in games:
        assert game["engines"]["external"]["decisions"][0]["reported_nodes"] == 7
        assert game["result"]["failure"]["kind"] == "ply_limit"
