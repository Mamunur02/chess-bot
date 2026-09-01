"""Minimal agent contract with explicit randomness and computation budget."""

import random
from dataclasses import dataclass
from typing import Protocol, TypeVar

from chesslab.search import SearchBudget

StateT_contra = TypeVar("StateT_contra", contravariant=True)
ActionT_co = TypeVar("ActionT_co", covariant=True)


@dataclass(frozen=True, slots=True)
class AgentDecision[ActionT]:
    """The action selected by an agent.

    Search measurements will be added when a concrete searched agent can
    produce and test them.
    """

    action: ActionT


class Agent(Protocol[StateT_contra, ActionT_co]):
    """Select an action under an explicit budget and caller-owned RNG."""

    def select_action(
        self,
        state: StateT_contra,
        budget: SearchBudget,
        rng: random.Random,
    ) -> AgentDecision[ActionT_co]:
        """Return a decision for a non-terminal state."""
        ...
