"""Uniform random action selection with caller-owned randomness."""

import random

from chesslab.agents.protocols import AgentDecision
from chesslab.games import GameState
from chesslab.search import SearchBudget


class RandomAgent[ActionT]:
    """Choose uniformly from legal actions without performing search."""

    def select_action(
        self,
        state: GameState[ActionT],
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[ActionT]:
        """Select a legal action using only ``rng``.

        The budget is accepted to satisfy the common agent contract but is not
        consumed because this agent performs no search.
        """
        del budget
        if state.is_terminal():
            raise ValueError("cannot select an action from a terminal state")
        actions = state.legal_actions()
        if not actions:
            raise ValueError("cannot select an action when none are legal")
        return AgentDecision(action=rng.choice(actions))
