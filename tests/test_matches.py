import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

import pytest

from chesslab.agents import AgentDecision, RandomAgent
from chesslab.eval import FailureKind, MatchResult, MatchStatus, run_match
from chesslab.games import GameState, Player, TerminalReturns
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget


@dataclass(frozen=True, slots=True)
class CountdownState:
    remaining: int
    player: Player = 0

    @property
    def current_player(self) -> Player:
        return self.player

    def legal_actions(self) -> Sequence[int]:
        return () if self.is_terminal() else (0, 1)

    def apply(self, action: int) -> Self:
        if action not in self.legal_actions():
            raise ValueError("illegal action")
        next_player: Player = 1 if self.player == 0 else 0
        return type(self)(remaining=self.remaining - 1, player=next_player)

    def is_terminal(self) -> bool:
        return self.remaining == 0

    def returns(self) -> TerminalReturns:
        if not self.is_terminal():
            raise ValueError("not terminal")
        return (-1.0, 1.0) if self.player == 0 else (1.0, -1.0)


@dataclass(frozen=True, slots=True)
class EndlessState:
    player: Player = 0

    @property
    def current_player(self) -> Player:
        return self.player

    def legal_actions(self) -> Sequence[int]:
        return (0,)

    def apply(self, action: int) -> Self:
        if action != 0:
            raise ValueError("illegal action")
        next_player: Player = 1 if self.player == 0 else 0
        return type(self)(player=next_player)

    def is_terminal(self) -> bool:
        return False

    def returns(self) -> TerminalReturns:
        raise ValueError("not terminal")


class IllegalAgent:
    def select_action(
        self,
        state: GameState[int],
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[int]:
        del state, budget, rng
        return AgentDecision(action=99)


class ExplodingAgent:
    def select_action(
        self,
        state: GameState[int],
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[int]:
        del state, budget, rng
        raise RuntimeError("agent failed")


class RecordingAgent:
    def __init__(self) -> None:
        self.draws: list[int] = []

    def select_action(
        self,
        state: GameState[int],
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[int]:
        del budget
        self.draws.append(rng.getrandbits(32))
        return AgentDecision(action=state.legal_actions()[0])


class BrokenTransitionState(EndlessState):
    def apply(self, action: int) -> Self:
        del action
        raise RuntimeError("transition failed")


def run_countdown(seed: int = 17) -> MatchResult:
    return run_match(
        CountdownState(remaining=4),
        (RandomAgent[int](), RandomAgent[int]()),
        NodeBudget(1),
        seed=seed,
        max_plies=10,
        encode_action=str,
    )


def test_two_random_agents_complete_game_reproducibly() -> None:
    first = run_countdown()
    repeated = run_countdown()

    assert first == repeated
    assert first.status is MatchStatus.COMPLETED
    assert first.plies == 4
    assert first.terminal_returns == (-1.0, 1.0)
    assert [move.player for move in first.moves] == [0, 1, 0, 1]


def test_player_rng_streams_are_independent_and_recorded() -> None:
    player_zero = RecordingAgent()
    player_one = RecordingAgent()

    result = run_match(
        CountdownState(remaining=4),
        (player_zero, player_one),
        DepthBudget(1),
        seed=23,
        max_plies=10,
        encode_action=str,
    )

    seed_zero, seed_one = result.metadata.player_seeds
    expected_zero = random.Random(seed_zero)
    expected_one = random.Random(seed_one)
    assert seed_zero != seed_one
    assert player_zero.draws == [expected_zero.getrandbits(32) for _ in range(2)]
    assert player_one.draws == [expected_one.getrandbits(32) for _ in range(2)]


def test_time_budget_is_recorded_in_match_metadata() -> None:
    result = run_match(
        CountdownState(remaining=1),
        (RandomAgent[int](), RandomAgent[int]()),
        TimeBudget(25),
        seed=0,
        max_plies=2,
        encode_action=str,
    )

    assert result.metadata.budget_kind == "milliseconds"
    assert result.metadata.budget_value == 25


def test_initial_terminal_state_completes_without_agent_calls() -> None:
    result = run_match(
        CountdownState(remaining=0),
        (ExplodingAgent(), ExplodingAgent()),
        NodeBudget(1),
        seed=0,
        max_plies=1,
        encode_action=str,
    )

    assert result.status is MatchStatus.COMPLETED
    assert result.plies == 0
    assert result.failure is None


def test_illegal_agent_action_fails_without_recording_move() -> None:
    result = run_match(
        CountdownState(remaining=1),
        (IllegalAgent(), RandomAgent[int]()),
        NodeBudget(1),
        seed=0,
        max_plies=2,
        encode_action=str,
    )

    assert result.status is MatchStatus.FAILED
    assert result.failure is not None
    assert result.failure.kind is FailureKind.ILLEGAL_ACTION
    assert result.failure.player == 0
    assert result.moves == ()
    assert result.terminal_returns is None


def test_agent_exception_becomes_structured_failure() -> None:
    result = run_match(
        CountdownState(remaining=1),
        (ExplodingAgent(), RandomAgent[int]()),
        NodeBudget(1),
        seed=0,
        max_plies=2,
        encode_action=str,
    )

    assert result.status is MatchStatus.FAILED
    assert result.failure is not None
    assert result.failure.kind is FailureKind.AGENT_ERROR
    assert "RuntimeError: agent failed" in result.failure.message


def test_transition_exception_becomes_structured_failure() -> None:
    result = run_match(
        BrokenTransitionState(),
        (RandomAgent[int](), RandomAgent[int]()),
        NodeBudget(1),
        seed=0,
        max_plies=2,
        encode_action=str,
    )

    assert result.status is MatchStatus.FAILED
    assert result.failure is not None
    assert result.failure.kind is FailureKind.STATE_ERROR
    assert result.moves == ()


def test_ply_limit_interrupts_without_fabricating_draw() -> None:
    result = run_match(
        EndlessState(),
        (RandomAgent[int](), RandomAgent[int]()),
        NodeBudget(1),
        seed=0,
        max_plies=3,
        encode_action=str,
    )

    assert result.status is MatchStatus.INTERRUPTED
    assert result.failure is not None
    assert result.failure.kind is FailureKind.PLY_LIMIT
    assert result.plies == 3
    assert result.terminal_returns is None


def test_encoding_failure_does_not_record_move() -> None:
    def fail_encoding(action: int) -> str:
        raise RuntimeError(f"cannot encode {action}")

    result = run_match(
        CountdownState(remaining=1),
        (RandomAgent[int](), RandomAgent[int]()),
        NodeBudget(1),
        seed=0,
        max_plies=2,
        encode_action=fail_encoding,
    )

    assert result.status is MatchStatus.FAILED
    assert result.failure is not None
    assert result.failure.kind is FailureKind.ENCODING_ERROR
    assert result.moves == ()


def test_result_is_json_serializable() -> None:
    result = run_countdown()

    serialized = json.dumps(result.to_dict())
    restored = json.loads(serialized)

    assert restored["status"] == "completed"
    assert restored["plies"] == 4
    assert restored["terminal_returns"] == [-1.0, 1.0]


@pytest.mark.parametrize(
    "seed, max_plies, message",
    [(True, 1, "seed must be an integer"), (0, 0, "max_plies")],
)
def test_invalid_configuration_fails_before_match(
    seed: int, max_plies: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        run_match(
            CountdownState(remaining=1),
            (RandomAgent[int](), RandomAgent[int]()),
            NodeBudget(1),
            seed=seed,
            max_plies=max_plies,
            encode_action=str,
        )
