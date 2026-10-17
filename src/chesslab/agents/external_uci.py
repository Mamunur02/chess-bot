"""A game-scoped, hash-pinned UCI opponent using python-chess."""

import asyncio
import hashlib
import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import chess
import chess.engine

from chesslab.agents.protocols import AgentDecision
from chesslab.config import json_object, nonempty_string, reject_unknown_fields
from chesslab.games import GameState
from chesslab.games.chess import ChessState
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget

type OptionValue = str | int | bool


def file_sha256(path: Path) -> str:
    """Hash binaries and separately supplied network files without loading them all."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@dataclass(frozen=True, slots=True)
class UciConfig:
    """Pinned executable, explicit options, and a protocol response allowance.

    Paths are relative to the invocation directory. Assets list external networks
    or other engine inputs; embedded networks are covered by the executable hash.
    No engine-independent UCI seed exists: caller seeds are not sent implicitly.
    """

    path: str
    sha256: str
    options: Mapping[str, OptionValue]
    timeout_seconds: float = 10.0
    assets: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: object) -> "UciConfig":
        data = json_object(value, "UCI agent")
        reject_unknown_fields(
            data,
            {"kind", "path", "sha256", "options", "timeout_seconds", "assets"},
            "UCI agent",
        )
        path = nonempty_string(data.get("path"), "UCI path")
        digest = nonempty_string(data.get("sha256"), "UCI sha256").lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("UCI sha256 must contain 64 hexadecimal characters")
        options = json_object(data.get("options", {}), "UCI options")
        parsed: dict[str, OptionValue] = {}
        for key, item in options.items():
            if key.lower() in chess.engine.MANAGED_OPTIONS:
                raise ValueError(f"UCI option {key} is managed by python-chess")
            if not key.strip() or type(item) not in (str, int, bool):
                raise ValueError(
                    "UCI options must be named string, integer or bool values"
                )
            assert isinstance(item, (str, int, bool))
            parsed[key] = item
        timeout = data.get("timeout_seconds", 10.0)
        if (
            type(timeout) not in (int, float)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("UCI timeout_seconds must be finite and positive")
        assets = data.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("UCI assets must be an array of file paths")
        return cls(
            path,
            digest,
            parsed,
            float(timeout),
            tuple(nonempty_string(item, "UCI asset") for item in assets),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "external_uci",
            "path": self.path,
            "sha256": self.sha256,
            "options": dict(self.options),
            "timeout_seconds": self.timeout_seconds,
            "assets": list(self.assets),
        }


def uci_limit(budget: SearchBudget) -> chess.engine.Limit:
    """Translate budgets without treating engine node/depth units as equivalent."""
    if isinstance(budget, DepthBudget):
        return chess.engine.Limit(depth=budget.depth)
    if isinstance(budget, NodeBudget):
        return chess.engine.Limit(nodes=budget.nodes)
    if isinstance(budget, TimeBudget):
        return chess.engine.Limit(time=budget.milliseconds / 1000)
    raise ValueError("unsupported UCI budget")


def bounded_play(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    game: object,
    timeout: float,
) -> chess.engine.PlayResult:
    """Bound even depth/node searches (SimpleEngine.play only bounds timed ones).

    Use the public asynchronous protocol on its owning event loop. A watchdog
    expiry is a failure, never a successful result at a silently reduced budget.
    """

    async def play() -> chess.engine.PlayResult:
        return await asyncio.wait_for(
            engine.protocol.play(board, limit, game=game, info=chess.engine.INFO_BASIC),
            timeout,
        )

    return asyncio.run_coroutine_threadsafe(play(), engine.protocol.loop).result()


class ExternalUciAgent:
    """Lazily start one engine per game; caller must close it in a finally block."""

    def __init__(self, config: UciConfig) -> None:
        self.config = config
        self.engine: chess.engine.SimpleEngine | None = None
        self.game = object()
        self.closed = False
        self.metadata: dict[str, object] = {
            "config": config.to_dict(),
            "status": "not_started",
            "seed_policy": "caller RNG unused; engine-specific seed only via options",
            "cleanup_error": None,
            "managed_settings": {"Ponder": False, "MultiPV": 1, "UCI_Chess960": False},
        }
        self.decisions: list[dict[str, object]] = []
        self.metadata["decisions"] = self.decisions

    def _start(self) -> chess.engine.SimpleEngine:
        started = perf_counter()
        self.metadata["status"] = "starting"
        path = Path(self.config.path).resolve(strict=True)
        digest = file_sha256(path)
        self.metadata.update({"executable": str(path), "executable_sha256": digest})
        if digest != self.config.sha256:
            raise ValueError("UCI executable SHA-256 mismatch")
        self.metadata["assets"] = [
            {"path": str(Path(p).resolve(strict=True)), "sha256": file_sha256(Path(p))}
            for p in self.config.assets
        ]
        engine = chess.engine.SimpleEngine.popen_uci(
            str(path), timeout=self.config.timeout_seconds
        )
        self.engine = engine  # Own it before configuration, so failures still clean up.
        self.metadata["identity"] = dict(engine.id)
        self.metadata["advertised_options"] = {
            name: {
                "type": option.type,
                "default": option.default,
                "min": option.min,
                "max": option.max,
                "var": option.var,
            }
            for name, option in engine.options.items()
        }
        # Fail on unsupported/misspelled settings instead of silently using defaults.
        engine.configure(self.config.options)
        engine.ping()
        self.metadata["startup_seconds"] = perf_counter() - started
        self.metadata["status"] = "ready"
        return engine

    def prepare(self) -> None:
        """Start/configure before timing a decision; close on startup failure."""
        if self.closed:
            raise RuntimeError("UCI agent is closed")
        if self.engine is None:
            try:
                self._start()
            except BaseException as error:
                self.metadata.update(
                    {"status": "failed", "error": f"{type(error).__name__}: {error}"}
                )
                self.close()
                raise

    def select_action(
        self,
        state: GameState[chess.Move],
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[chess.Move]:
        del rng
        if self.closed:
            raise RuntimeError("UCI agent is closed")
        if not isinstance(state, ChessState):
            raise TypeError("ExternalUciAgent requires ChessState")
        if state.is_terminal():
            raise ValueError("cannot play a terminal state")
        started = perf_counter()
        try:
            engine = self.engine if self.engine is not None else self._start()
            limit = uci_limit(budget)
            result = bounded_play(
                engine,
                state.to_board(),
                limit,
                self.game,
                self.config.timeout_seconds + (limit.time or 0.0),
            )
            if result.move is None or result.move not in state.legal_actions():
                raise ValueError("UCI engine returned no legal move")
            self.decisions.append(
                {
                    "action": result.move.uci(),
                    "elapsed_seconds": perf_counter() - started,
                    "reported_nodes": result.info.get("nodes"),
                    "reported_depth": result.info.get("depth"),
                    "reported_seconds": result.info.get("time"),
                }
            )
            return AgentDecision(result.move)
        except BaseException as error:
            self.metadata.update(
                {"status": "failed", "error": f"{type(error).__name__}: {error}"}
            )
            self.close()
            raise

    def close(self) -> None:
        """Attempt bounded graceful exit, always close transport; retain errors."""
        if self.closed:
            return
        self.closed = True
        if self.engine is not None:
            try:
                self.engine.quit()
            except Exception as error:
                self.metadata["cleanup_error"] = f"{type(error).__name__}: {error}"
            finally:
                self.engine.close()
        self.metadata["closed"] = True
