"""Generic, deterministic execution of two-player matches."""

import random
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from chesslab.agents import Agent
from chesslab.games import GameState, Player, TerminalReturns
from chesslab.search import DepthBudget, NodeBudget, SearchBudget

type BudgetKind = Literal["depth", "nodes"]
type AgentPair[ActionT] = tuple[
    Agent[GameState[ActionT], ActionT],
    Agent[GameState[ActionT], ActionT],
]


class MatchStatus(StrEnum):
    """High-level completion state of a match."""

    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class FailureKind(StrEnum):
    """Machine-readable reason why a match did not complete."""

    PLY_LIMIT = "ply_limit"
    AGENT_ERROR = "agent_error"
    ILLEGAL_ACTION = "illegal_action"
    ENCODING_ERROR = "encoding_error"
    STATE_ERROR = "state_error"


@dataclass(frozen=True, slots=True)
class MatchMetadata:
    """Inputs required to reproduce the match's random action streams."""

    root_seed: int
    player_seeds: tuple[int, int]
    budget_kind: BudgetKind
    budget_value: int
    max_plies: int

    def to_dict(self) -> dict[str, object]:
        return {
            "root_seed": self.root_seed,
            "player_seeds": list(self.player_seeds),
            "budget_kind": self.budget_kind,
            "budget_value": self.budget_value,
            "max_plies": self.max_plies,
        }


@dataclass(frozen=True, slots=True)
class MoveRecord:
    """One successfully encoded and applied action."""

    ply_index: int
    player: Player
    action: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ply_index": self.ply_index,
            "player": self.player,
            "action": self.action,
        }


@dataclass(frozen=True, slots=True)
class MatchFailure:
    """Structured information about an interrupted or failed match."""

    kind: FailureKind
    ply_index: int
    player: Player | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "ply_index": self.ply_index,
            "player": self.player,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class MatchResult:
    """A completed, interrupted, or failed match and its legal move record."""

    status: MatchStatus
    metadata: MatchMetadata
    moves: tuple[MoveRecord, ...]
    terminal_returns: TerminalReturns | None
    failure: MatchFailure | None

    def __post_init__(self) -> None:
        completed = self.status is MatchStatus.COMPLETED
        if completed != (self.terminal_returns is not None):
            raise ValueError("only completed matches have terminal returns")
        if completed == (self.failure is not None):
            raise ValueError("only non-completed matches have failure information")

    @property
    def plies(self) -> int:
        return len(self.moves)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "metadata": self.metadata.to_dict(),
            "moves": [move.to_dict() for move in self.moves],
            "terminal_returns": (
                list(self.terminal_returns)
                if self.terminal_returns is not None
                else None
            ),
            "failure": self.failure.to_dict() if self.failure is not None else None,
            "plies": self.plies,
        }


def _budget_details(budget: SearchBudget) -> tuple[BudgetKind, int]:
    if isinstance(budget, DepthBudget):
        return ("depth", budget.depth)
    if isinstance(budget, NodeBudget):
        return ("nodes", budget.nodes)
    raise ValueError(f"unsupported search budget: {type(budget).__name__}")


def _exception_message(error: Exception) -> str:
    detail = str(error)
    return f"{type(error).__name__}: {detail}" if detail else type(error).__name__


def _stopped_result(
    *,
    status: MatchStatus,
    metadata: MatchMetadata,
    moves: list[MoveRecord],
    kind: FailureKind,
    player: Player | None,
    message: str,
) -> MatchResult:
    return MatchResult(
        status=status,
        metadata=metadata,
        moves=tuple(moves),
        terminal_returns=None,
        failure=MatchFailure(
            kind=kind,
            ply_index=len(moves),
            player=player,
            message=message,
        ),
    )


def run_match[ActionT](
    initial_state: GameState[ActionT],
    agents: AgentPair[ActionT],
    budget: SearchBudget,
    *,
    seed: int,
    max_plies: int,
    encode_action: Callable[[ActionT], str],
) -> MatchResult:
    """Run a deterministic match and return a structured result."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(max_plies, bool) or max_plies <= 0:
        raise ValueError("max_plies must be a positive integer")

    budget_kind, budget_value = _budget_details(budget)
    seed_source = random.Random(seed)
    player_seeds = (seed_source.getrandbits(128), seed_source.getrandbits(128))
    player_rngs = (random.Random(player_seeds[0]), random.Random(player_seeds[1]))
    metadata = MatchMetadata(
        root_seed=seed,
        player_seeds=player_seeds,
        budget_kind=budget_kind,
        budget_value=budget_value,
        max_plies=max_plies,
    )
    state = initial_state
    moves: list[MoveRecord] = []

    while True:
        try:
            if state.is_terminal():
                return MatchResult(
                    status=MatchStatus.COMPLETED,
                    metadata=metadata,
                    moves=tuple(moves),
                    terminal_returns=state.returns(),
                    failure=None,
                )
        except Exception as error:
            return _stopped_result(
                status=MatchStatus.FAILED,
                metadata=metadata,
                moves=moves,
                kind=FailureKind.STATE_ERROR,
                player=None,
                message=_exception_message(error),
            )

        if len(moves) >= max_plies:
            return _stopped_result(
                status=MatchStatus.INTERRUPTED,
                metadata=metadata,
                moves=moves,
                kind=FailureKind.PLY_LIMIT,
                player=None,
                message=f"match reached the maximum of {max_plies} plies",
            )

        try:
            player = state.current_player
            if player not in (0, 1):
                raise ValueError(f"invalid current player: {player}")
            legal_actions = tuple(state.legal_actions())
            if not legal_actions:
                raise ValueError("non-terminal state has no legal actions")
        except Exception as error:
            return _stopped_result(
                status=MatchStatus.FAILED,
                metadata=metadata,
                moves=moves,
                kind=FailureKind.STATE_ERROR,
                player=None,
                message=_exception_message(error),
            )

        try:
            decision = agents[player].select_action(
                state, budget, player_rngs[player]
            )
            action = decision.action
        except Exception as error:
            return _stopped_result(
                status=MatchStatus.FAILED,
                metadata=metadata,
                moves=moves,
                kind=FailureKind.AGENT_ERROR,
                player=player,
                message=_exception_message(error),
            )

        if action not in legal_actions:
            return _stopped_result(
                status=MatchStatus.FAILED,
                metadata=metadata,
                moves=moves,
                kind=FailureKind.ILLEGAL_ACTION,
                player=player,
                message="agent returned an action outside the legal actions",
            )

        try:
            encoded_action = encode_action(action)
            if not isinstance(encoded_action, str):
                raise TypeError("action encoder must return a string")
        except Exception as error:
            return _stopped_result(
                status=MatchStatus.FAILED,
                metadata=metadata,
                moves=moves,
                kind=FailureKind.ENCODING_ERROR,
                player=player,
                message=_exception_message(error),
            )

        try:
            next_state = state.apply(action)
            if next_state.current_player == player:
                raise ValueError("state transition did not alternate players")
        except Exception as error:
            return _stopped_result(
                status=MatchStatus.FAILED,
                metadata=metadata,
                moves=moves,
                kind=FailureKind.STATE_ERROR,
                player=player,
                message=_exception_message(error),
            )

        moves.append(
            MoveRecord(
                ply_index=len(moves),
                player=player,
                action=encoded_action,
            )
        )
        state = next_state
