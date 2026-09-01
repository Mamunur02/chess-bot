from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Self

import pytest

from chesslab.games import GameState, Player, TerminalReturns
from chesslab.search.classical import (
    MATE_SCORE,
    alpha_beta_search,
    exhaustive_search,
    terminal_score,
)

TRANSITIONS: Mapping[str, Mapping[str, str]] = {
    "root": {"A": "a", "B": "b"},
    "a": {"A1": "a1", "A2": "a2"},
    "b": {"B1": "b1", "B2": "b2"},
    "horizon0": {"high": "high", "low": "low"},
    "horizon1": {"high-for-zero": "high", "low-for-zero": "low"},
    "high": {"continue": "draw"},
    "low": {"continue": "draw"},
    "ties": {"first": "equal1", "second": "equal2"},
    "equal1": {"continue": "draw"},
    "equal2": {"continue": "draw"},
}
PLAYERS: Mapping[str, Player] = {
    "root": 0,
    "a": 1,
    "b": 1,
    "a1": 0,
    "a2": 0,
    "b1": 0,
    "b2": 0,
    "draw": 0,
    "horizon0": 0,
    "horizon1": 1,
    "high": 1,
    "low": 0,
    "ties": 0,
    "equal1": 1,
    "equal2": 1,
}
RETURNS: Mapping[str, TerminalReturns] = {
    "a1": (1.0, -1.0),
    "a2": (1.0, -1.0),
    "b1": (0.0, 0.0),
    "b2": (1.0, -1.0),
    "draw": (0.0, 0.0),
}
HEURISTICS: Mapping[str, int] = {"high": 30, "low": -20, "equal1": 5, "equal2": 5}


@dataclass(frozen=True, slots=True)
class TreeState:
    node: str

    @property
    def current_player(self) -> Player:
        return PLAYERS[self.node]

    def legal_actions(self) -> Sequence[str]:
        return tuple(TRANSITIONS.get(self.node, ()))

    def apply(self, action: str) -> Self:
        destination = TRANSITIONS.get(self.node, {}).get(action)
        if destination is None:
            raise ValueError(f"illegal action: {action}")
        return type(self)(destination)

    def is_terminal(self) -> bool:
        return self.node in RETURNS

    def returns(self) -> TerminalReturns:
        if not self.is_terminal():
            raise ValueError("returns are only defined for terminal states")
        return RETURNS[self.node]


def tree_evaluator(state: GameState[str], perspective: Player) -> int:
    if not isinstance(state, TreeState):
        raise TypeError("tree evaluator requires TreeState")
    player_zero_value = HEURISTICS[state.node]
    return player_zero_value if perspective == 0 else -player_zero_value


def test_depth_one_evaluates_immediate_children_from_root_perspective() -> None:
    player_zero = exhaustive_search(TreeState("horizon0"), 1, tree_evaluator)
    player_one = exhaustive_search(TreeState("horizon1"), 1, tree_evaluator)

    assert (player_zero.action, player_zero.value, player_zero.nodes) == (
        "high",
        30,
        3,
    )
    assert (player_one.action, player_one.value, player_one.nodes) == (
        "low-for-zero",
        20,
        3,
    )


def test_equal_values_preserve_legal_action_order() -> None:
    result = alpha_beta_search(TreeState("ties"), 1, tree_evaluator)

    assert result.action == "first"
    assert result.value == 5


def test_alpha_beta_matches_reference_and_measures_pruning() -> None:
    reference = exhaustive_search(TreeState("root"), 2, tree_evaluator)
    pruned = alpha_beta_search(TreeState("root"), 2, tree_evaluator)

    assert (reference.action, reference.value, reference.nodes, reference.depth) == (
        "A",
        MATE_SCORE,
        7,
        2,
    )
    assert (pruned.action, pruned.value, pruned.nodes, pruned.depth) == (
        "A",
        MATE_SCORE,
        6,
        2,
    )


def test_terminal_scores_use_fixed_perspective() -> None:
    win = TreeState("a1")
    draw = TreeState("b1")

    assert terminal_score(win, 0) == MATE_SCORE
    assert terminal_score(win, 1) == -MATE_SCORE
    assert terminal_score(draw, 0) == 0


@pytest.mark.parametrize("depth", [0, -1, True])
def test_search_requires_positive_depth(depth: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        exhaustive_search(TreeState("root"), depth, tree_evaluator)


def test_search_rejects_terminal_root() -> None:
    with pytest.raises(ValueError, match="terminal state"):
        alpha_beta_search(TreeState("a1"), 1, tree_evaluator)
