import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

import pytest

from chesslab.agents import Agent, RandomAgent
from chesslab.games import GameState, Player, TerminalReturns
from chesslab.search import DepthBudget, NodeBudget


@dataclass(frozen=True, slots=True)
class ChoiceState:
    terminal: bool = False

    @property
    def current_player(self) -> Player:
        return 0

    def legal_actions(self) -> Sequence[int]:
        return () if self.terminal else (10, 20, 30)

    def apply(self, action: int) -> Self:
        if action not in self.legal_actions():
            raise ValueError("illegal action")
        return type(self)(terminal=True)

    def is_terminal(self) -> bool:
        return self.terminal

    def returns(self) -> TerminalReturns:
        if not self.terminal:
            raise ValueError("not terminal")
        return (0.0, 0.0)


def require_agent(agent: Agent[GameState[int], int]) -> Agent[GameState[int], int]:
    return agent


def test_random_agent_implements_contract_and_is_reproducible() -> None:
    agent = require_agent(RandomAgent[int]())
    state = ChoiceState()

    first = agent.select_action(state, DepthBudget(1), random.Random(42))
    repeated = agent.select_action(state, NodeBudget(99), random.Random(42))

    assert first == repeated
    assert first.action in state.legal_actions()


def test_random_agent_uses_caller_rng_sequence() -> None:
    agent = RandomAgent[int]()
    state = ChoiceState()
    rng = random.Random(9)

    actual = [agent.select_action(state, NodeBudget(1), rng).action for _ in range(4)]

    expected_rng = random.Random(9)
    expected = [expected_rng.choice(state.legal_actions()) for _ in range(4)]
    assert actual == expected


def test_random_agent_rejects_terminal_state() -> None:
    with pytest.raises(ValueError, match="terminal state"):
        RandomAgent[int]().select_action(
            ChoiceState(terminal=True), NodeBudget(1), random.Random(0)
        )
