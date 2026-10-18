"""Uniform, history-preserving replay storage for endgame transitions."""

import random
from dataclasses import dataclass

import chess

from chesslab.endgames.rules import terminal_reward

DEFAULT_REPLAY_CAPACITY = 10_000


@dataclass(frozen=True, slots=True)
class ReplayTransition:
    """A learner afterstate and the opponent reply actually observed."""

    afterstate: chess.Board
    learner: chess.Color
    observed_reply: chess.Move | None


@dataclass(frozen=True, slots=True)
class _ReplaySnapshot:
    """Private board and move data, detached from caller-owned move objects."""

    afterstate: chess.Board
    learner: chess.Color
    observed_reply_uci: str | None


class ReplayBuffer:
    """Fixed-capacity ring buffer sampled uniformly with an explicit RNG."""

    def __init__(self, capacity: int = DEFAULT_REPLAY_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items: list[_ReplaySnapshot] = []
        self._next_index = 0

    def __len__(self) -> int:
        return len(self._items)

    def append(
        self,
        afterstate: chess.Board,
        learner: chess.Color,
        observed_reply: chess.Move | None,
    ) -> None:
        """Copy and append one valid afterstate/reply pair."""
        if learner not in chess.COLORS:
            raise ValueError("learner must be a chess color")
        terminal = terminal_reward(afterstate, learner) is not None
        if terminal:
            if observed_reply is not None:
                raise ValueError("terminal afterstate must not have an observed reply")
        else:
            if afterstate.turn == learner:
                raise ValueError(
                    "nonterminal afterstate must have the opponent to move"
                )
            if observed_reply is None:
                raise ValueError("nonterminal afterstate requires an observed reply")
            if observed_reply not in afterstate.legal_moves:
                raise ValueError("stored observed opponent reply is illegal")
        stored = _ReplaySnapshot(
            _copy_board(afterstate),
            learner,
            observed_reply.uci() if observed_reply is not None else None,
        )
        if len(self._items) < self.capacity:
            self._items.append(stored)
            return
        self._items[self._next_index] = stored
        self._next_index = (self._next_index + 1) % self.capacity

    def sample(
        self, batch_size: int, rng: random.Random
    ) -> tuple[ReplayTransition, ...]:
        """Return a uniform sample without replacement, copying board histories."""
        if batch_size < 0:
            raise ValueError("batch_size must be nonnegative")
        selected = rng.sample(self._items, batch_size)
        return tuple(
            ReplayTransition(
                _copy_board(transition.afterstate),
                transition.learner,
                chess.Move.from_uci(transition.observed_reply_uci)
                if transition.observed_reply_uci is not None
                else None,
            )
            for transition in selected
        )


def _copy_board(board: chess.Board) -> chess.Board:
    """Copy a board and detach the mutable move objects in its history stack."""
    copied = board.copy(stack=True)
    copied.move_stack = [chess.Move.from_uci(move.uci()) for move in board.move_stack]
    return copied
