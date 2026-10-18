"""Pure, history-aware bootstrapped target construction for protocol v1."""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import chess

from chesslab.endgames.rules import terminal_reward

Predictor = Callable[[Sequence[chess.Board], chess.Color], Sequence[float]]


class Transition(Protocol):
    """The replay fields needed by pure target construction."""

    @property
    def afterstate(self) -> chess.Board: ...

    @property
    def learner(self) -> chess.Color: ...

    @property
    def observed_reply(self) -> chess.Move | None: ...


@dataclass(frozen=True, slots=True)
class TargetBatch:
    """Targets in input order and the number of leaves passed to predictors."""

    targets: tuple[float, ...]
    forward_leaf_count: int


@dataclass(frozen=True, slots=True)
class _Leaf:
    index: int


_ValueRef = float | _Leaf


@dataclass(frozen=True, slots=True)
class _PlannedTarget:
    direct: float | None
    observed: tuple[_ValueRef, ...] | None
    defensive: tuple[tuple[_ValueRef, ...], ...] | None


def _validate_beta(beta: float) -> None:
    if not math.isfinite(beta) or not 0.0 <= beta <= 1.0:
        raise ValueError("beta must be finite and in [0, 1]")


def _plan_reply(
    afterstate: chess.Board,
    reply: chess.Move,
    learner: chess.Color,
    leaves: list[tuple[chess.Board, chess.Color]],
) -> tuple[_ValueRef, ...]:
    reply_board = afterstate.copy(stack=True)
    reply_board.push(reply)
    reward = terminal_reward(reply_board, learner)
    if reward is not None:
        return (reward,)

    values: list[_ValueRef] = []
    for learner_move in reply_board.legal_moves:
        child = reply_board.copy(stack=True)
        child.push(learner_move)
        reward = terminal_reward(child, learner)
        if reward is not None:
            values.append(reward)
        else:
            index = len(leaves)
            leaves.append((child, learner))
            values.append(_Leaf(index))
    if not values:
        raise RuntimeError("nonterminal reply position has no legal learner move")
    return tuple(values)


def _predict_leaves(
    leaves: Sequence[tuple[chess.Board, chess.Color]], predictor: Predictor
) -> tuple[float, ...]:
    predictions = [0.0] * len(leaves)
    for learner in chess.COLORS:
        indices = [index for index, (_, color) in enumerate(leaves) if color == learner]
        if not indices:
            continue
        boards = [leaves[index][0].copy(stack=True) for index in indices]
        values = predictor(boards, learner)
        if len(values) != len(indices):
            raise ValueError(
                "predictor returned a different number of values than boards"
            )
        for index, value in zip(indices, values, strict=True):
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("predictor values must be finite numbers")
            if not -1.0 <= value <= 1.0:
                raise ValueError("predictor values must be in [-1, 1]")
            predictions[index] = float(value)
    return tuple(predictions)


def _resolve(values: Sequence[_ValueRef], predictions: Sequence[float]) -> float:
    return max(
        predictions[value.index] if isinstance(value, _Leaf) else value
        for value in values
    )


def build_targets(
    transitions: Sequence[Transition],
    beta: float,
    predictor: Predictor,
) -> TargetBatch:
    """Build protocol targets from afterstates and stored opponent replies.

    Predictions are injected so this module remains independent of a model
    framework. Each transition retains the actual reply observed after its
    learner afterstate.
    """
    _validate_beta(beta)
    leaves: list[tuple[chess.Board, chess.Color]] = []
    plans: list[_PlannedTarget] = []

    for transition in transitions:
        afterstate = transition.afterstate
        learner = transition.learner
        observed_reply = transition.observed_reply
        if not isinstance(afterstate, chess.Board) or learner not in chess.COLORS:
            raise ValueError(
                "transition requires an afterstate and fixed learner color"
            )
        direct = terminal_reward(afterstate, learner)
        if direct is not None:
            if observed_reply is not None:
                raise ValueError("terminal afterstate must not have an observed reply")
            plans.append(_PlannedTarget(direct, None, None))
            continue
        if afterstate.turn == learner:
            raise ValueError("nonterminal afterstate must have the opponent to move")
        if not isinstance(observed_reply, chess.Move):
            raise ValueError(
                "nonterminal afterstate requires its observed opponent reply"
            )
        if observed_reply not in afterstate.legal_moves:
            raise ValueError("stored observed opponent reply is illegal")

        observed = None
        defensive = None
        if beta < 1.0:
            observed = _plan_reply(afterstate, observed_reply, learner, leaves)
        if beta > 0.0:
            defensive_branches: list[tuple[_ValueRef, ...]] = []
            for reply in afterstate.legal_moves:
                if observed is not None and reply == observed_reply:
                    defensive_branches.append(observed)
                else:
                    defensive_branches.append(
                        _plan_reply(afterstate, reply, learner, leaves)
                    )
            defensive = tuple(defensive_branches)
        plans.append(_PlannedTarget(None, observed, defensive))

    predictions = _predict_leaves(leaves, predictor)
    results: list[float] = []
    for plan in plans:
        if plan.direct is not None:
            results.append(plan.direct)
            continue
        observed_value = (
            _resolve(plan.observed, predictions) if plan.observed is not None else None
        )
        defensive_value = (
            min(_resolve(branch, predictions) for branch in plan.defensive)
            if plan.defensive is not None
            else None
        )
        if beta == 0.0:
            assert observed_value is not None
            target = observed_value
        elif beta == 1.0:
            assert defensive_value is not None
            target = defensive_value
        else:
            assert observed_value is not None and defensive_value is not None
            target = (1.0 - beta) * observed_value + beta * defensive_value
        results.append(target)
    return TargetBatch(tuple(results), len(leaves))
