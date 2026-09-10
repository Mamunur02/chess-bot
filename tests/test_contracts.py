import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

import pytest

from chesslab.agents import Agent, AgentDecision
from chesslab.games import GameState, Player, TerminalReturns
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget


@dataclass(frozen=True, slots=True)
class TakeAwayState:
    """Test-only game where players remove one or two stones."""

    stones: int
    player: Player = 0

    @property
    def current_player(self) -> Player:
        return self.player

    def legal_actions(self) -> Sequence[int]:
        if self.is_terminal():
            return ()
        return tuple(range(1, min(2, self.stones) + 1))

    def apply(self, action: int) -> Self:
        if action not in self.legal_actions():
            raise ValueError(f"illegal action: {action}")
        next_player: Player = 1 if self.player == 0 else 0
        return type(self)(stones=self.stones - action, player=next_player)

    def is_terminal(self) -> bool:
        return self.stones == 0

    def returns(self) -> TerminalReturns:
        if not self.is_terminal():
            raise ValueError("returns are only defined for terminal states")
        return (-1.0, 1.0) if self.player == 0 else (1.0, -1.0)


@dataclass(frozen=True, slots=True)
class DrawState:
    @property
    def current_player(self) -> Player:
        return 0

    def legal_actions(self) -> Sequence[int]:
        return ()

    def apply(self, action: int) -> Self:
        raise ValueError(f"illegal action: {action}")

    def is_terminal(self) -> bool:
        return True

    def returns(self) -> TerminalReturns:
        return (0.0, 0.0)


class RandomLegalAgent:
    def select_action(
        self,
        state: GameState[int],
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[int]:
        del budget
        actions = state.legal_actions()
        if not actions:
            raise ValueError("cannot act in a terminal state")
        return AgentDecision(action=rng.choice(actions))


def choose_with_contract(
    agent: Agent[GameState[int], int],
    state: GameState[int],
    budget: SearchBudget,
    rng: random.Random,
) -> AgentDecision[int]:
    """Exercise structural protocol compatibility during test type-checking."""
    return agent.select_action(state, budget, rng)


def test_apply_returns_new_state_and_alternates_players() -> None:
    parent = TakeAwayState(stones=3)

    child = parent.apply(2)

    assert parent == TakeAwayState(stones=3, player=0)
    assert child == TakeAwayState(stones=1, player=1)
    assert child is not parent


@pytest.mark.parametrize("action", [0, 3])
def test_illegal_actions_fail_clearly(action: int) -> None:
    with pytest.raises(ValueError, match="illegal action"):
        TakeAwayState(stones=2).apply(action)


def test_terminal_returns_use_stable_player_order() -> None:
    assert TakeAwayState(stones=0, player=0).returns() == (-1.0, 1.0)
    assert TakeAwayState(stones=0, player=1).returns() == (1.0, -1.0)
    assert DrawState().returns() == (0.0, 0.0)


def test_non_terminal_returns_fail_clearly() -> None:
    with pytest.raises(ValueError, match="terminal states"):
        TakeAwayState(stones=1).returns()


@pytest.mark.parametrize(
    "budget_type, value",
    [
        (DepthBudget, 0),
        (DepthBudget, -1),
        (NodeBudget, 0),
        (NodeBudget, -1),
        (TimeBudget, 0),
        (TimeBudget, -1),
    ],
)
def test_budgets_require_positive_integers(
    budget_type: type[DepthBudget] | type[NodeBudget] | type[TimeBudget],
    value: int,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        budget_type(value)


def test_bool_is_not_accepted_as_an_integer_budget() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        DepthBudget(True)
    with pytest.raises(ValueError, match="positive integer"):
        TimeBudget(True)


def test_agent_randomness_is_owned_by_the_caller() -> None:
    agent = RandomLegalAgent()
    state = TakeAwayState(stones=2)

    first = choose_with_contract(agent, state, NodeBudget(1), random.Random(7))
    repeated = choose_with_contract(agent, state, NodeBudget(1), random.Random(7))

    assert first == repeated
    assert first.action in state.legal_actions()
