"""Minimal contracts for deterministic, alternating, two-player games."""

from collections.abc import Sequence
from typing import Literal, Protocol, Self, TypeVar

ActionT = TypeVar("ActionT")

type Player = Literal[0, 1]
type TerminalReturns = tuple[float, float]


class GameState(Protocol[ActionT]):
    """A state in a deterministic, alternating, two-player, zero-sum game.

    Public transitions are immutable-looking: applying an action returns a new
    logical state and must not change the state on which ``apply`` was called.
    Terminal returns are ordered by stable player identity, not by the player
    whose turn it would be.
    """

    @property
    def current_player(self) -> Player:
        """Return the stable identity of the player whose turn is next."""
        ...

    def legal_actions(self) -> Sequence[ActionT]:
        """Return legal actions for the current player, or an empty sequence."""
        ...

    def apply(self, action: ActionT) -> Self:
        """Return the successor state, raising ``ValueError`` if action is illegal."""
        ...

    def is_terminal(self) -> bool:
        """Return whether the game has ended."""
        ...

    def returns(self) -> TerminalReturns:
        """Return terminal utilities by player, or raise ``ValueError``."""
        ...
