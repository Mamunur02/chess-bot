"""Depth-limited minimax and alpha-beta search with explicit perspective."""

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from enum import Enum, auto

from chesslab.games import GameState, Player
from chesslab.search.budgets import DepthBudget, NodeBudget, SearchBudget
from chesslab.search.results import SearchResult

MATE_SCORE = 1_000_000

type StateEvaluator[ActionT] = Callable[[GameState[ActionT], Player], int]
type ActionOrderer[ActionT] = Callable[
    [GameState[ActionT], Sequence[ActionT]], Sequence[ActionT]
]
type StateKey[ActionT] = Callable[[GameState[ActionT]], Hashable]


class _Bound(Enum):
    EXACT = auto()
    LOWER = auto()
    UPPER = auto()


@dataclass(frozen=True, slots=True)
class _TranspositionEntry[ActionT]:
    value: int
    principal_variation: tuple[ActionT, ...]
    solved: bool
    bound: _Bound


type _TranspositionTable[ActionT] = dict[
    tuple[Hashable, int], _TranspositionEntry[ActionT]
]


class _NodeLimitReached(Exception):
    """Internal control flow used to stop before exceeding a node budget."""


class _SearchCounter:
    def __init__(self, node_limit: int | None = None) -> None:
        self.node_limit = node_limit
        self.nodes = 0
        self.cutoffs = 0
        self.transposition_hits = 0

    def visit(self) -> None:
        if self.node_limit is not None and self.nodes >= self.node_limit:
            raise _NodeLimitReached
        self.nodes += 1


def terminal_score[ActionT](state: GameState[ActionT], perspective: Player) -> int:
    """Return a terminal score from one stable player's perspective."""
    if not state.is_terminal():
        raise ValueError("terminal score requires a terminal state")

    value = state.returns()[perspective]
    if value > 0:
        return MATE_SCORE
    if value < 0:
        return -MATE_SCORE
    return 0


def _ordered_actions[ActionT](
    state: GameState[ActionT],
    actions: Sequence[ActionT],
    action_orderer: ActionOrderer[ActionT] | None,
) -> tuple[ActionT, ...]:
    if action_orderer is None:
        return tuple(actions)

    ordered = tuple(action_orderer(state, actions))
    remaining = list(actions)
    for action in ordered:
        try:
            remaining.remove(action)
        except ValueError as error:
            raise ValueError("action orderer returned an unknown action") from error
    if remaining:
        raise ValueError("action orderer omitted one or more legal actions")
    return ordered


def _require_searchable[ActionT](
    state: GameState[ActionT], depth: int
) -> Sequence[ActionT]:
    if isinstance(depth, bool) or depth <= 0:
        raise ValueError("search depth must be a positive integer")
    if state.is_terminal():
        raise ValueError("cannot search a terminal state")
    actions = state.legal_actions()
    if not actions:
        raise ValueError("non-terminal state has no legal actions")
    return actions


def _evaluate_node[ActionT](
    state: GameState[ActionT],
    depth: int,
    evaluator: StateEvaluator[ActionT],
    perspective: Player,
) -> tuple[int, int]:
    if state.is_terminal():
        return terminal_score(state, perspective), 1
    if depth == 0:
        return evaluator(state, perspective), 1

    actions = state.legal_actions()
    if not actions:
        raise ValueError("non-terminal state has no legal actions")

    maximizing = state.current_player == perspective
    best_value: int | None = None
    nodes = 1
    for action in actions:
        value, child_nodes = _evaluate_node(
            state.apply(action), depth - 1, evaluator, perspective
        )
        nodes += child_nodes
        if best_value is None or (maximizing and value > best_value):
            best_value = value
        elif not maximizing and value < best_value:
            best_value = value

    if best_value is None:  # pragma: no cover - guarded by the actions check
        raise AssertionError("search node did not produce a value")
    return best_value, nodes


def exhaustive_search[ActionT](
    state: GameState[ActionT],
    depth: int,
    evaluator: StateEvaluator[ActionT],
) -> SearchResult[ActionT]:
    """Choose an action with unpruned depth-limited minimax."""
    actions = _require_searchable(state, depth)
    perspective = state.current_player
    best_action = actions[0]
    best_value: int | None = None
    nodes = 1

    for action in actions:
        value, child_nodes = _evaluate_node(
            state.apply(action), depth - 1, evaluator, perspective
        )
        nodes += child_nodes
        if best_value is None or value > best_value:
            best_action = action
            best_value = value

    if best_value is None:  # pragma: no cover
        raise AssertionError("search root did not produce a decision")
    return SearchResult(
        action=best_action,
        value=best_value,
        nodes=nodes,
        depth=depth,
    )


def _alpha_beta_value[ActionT](
    state: GameState[ActionT],
    depth: int,
    evaluator: StateEvaluator[ActionT],
    perspective: Player,
    alpha: int | None,
    beta: int | None,
    counter: _SearchCounter,
    action_orderer: ActionOrderer[ActionT] | None,
    transposition_key: StateKey[ActionT] | None,
    table: _TranspositionTable[ActionT] | None,
) -> tuple[int, tuple[ActionT, ...], bool]:
    counter.visit()
    if state.is_terminal():
        return terminal_score(state, perspective), (), True
    if depth == 0:
        return evaluator(state, perspective), (), False

    original_alpha = alpha
    original_beta = beta
    cache_key: tuple[Hashable, int] | None = None
    if transposition_key is not None and table is not None:
        cache_key = (transposition_key(state), depth)
        entry = table.get(cache_key)
        if entry is not None:
            counter.transposition_hits += 1
            if entry.bound is _Bound.EXACT:
                return entry.value, entry.principal_variation, entry.solved
            if entry.bound is _Bound.LOWER:
                alpha = entry.value if alpha is None else max(alpha, entry.value)
            else:
                beta = entry.value if beta is None else min(beta, entry.value)
            if alpha is not None and beta is not None and alpha >= beta:
                return entry.value, entry.principal_variation, False

    actions = state.legal_actions()
    if not actions:
        raise ValueError("non-terminal state has no legal actions")
    actions = _ordered_actions(state, actions, action_orderer)

    maximizing = state.current_player == perspective
    best_value: int | None = None
    best_line: tuple[ActionT, ...] = ()
    solved = True
    for action in actions:
        value, child_line, child_solved = _alpha_beta_value(
            state.apply(action),
            depth - 1,
            evaluator,
            perspective,
            alpha,
            beta,
            counter,
            action_orderer,
            transposition_key,
            table,
        )
        if best_value is None or (maximizing and value > best_value):
            best_value = value
            best_line = (action, *child_line)
        elif not maximizing and value < best_value:
            best_value = value
            best_line = (action, *child_line)
        solved = solved and child_solved

        if maximizing:
            alpha = best_value if alpha is None else max(alpha, best_value)
        else:
            beta = best_value if beta is None else min(beta, best_value)
        if alpha is not None and beta is not None and alpha >= beta:
            counter.cutoffs += 1
            break

    if best_value is None:  # pragma: no cover - guarded by the actions check
        raise AssertionError("search node did not produce a value")
    if cache_key is not None and table is not None:
        if original_alpha is not None and best_value <= original_alpha:
            bound = _Bound.UPPER
        elif original_beta is not None and best_value >= original_beta:
            bound = _Bound.LOWER
        else:
            bound = _Bound.EXACT
        table[cache_key] = _TranspositionEntry(
            value=best_value,
            principal_variation=best_line,
            solved=solved,
            bound=bound,
        )
    return best_value, best_line, solved


def _alpha_beta_iteration[ActionT](
    state: GameState[ActionT],
    depth: int,
    evaluator: StateEvaluator[ActionT],
    counter: _SearchCounter,
    action_orderer: ActionOrderer[ActionT] | None,
    transposition_key: StateKey[ActionT] | None,
    table: _TranspositionTable[ActionT] | None,
) -> tuple[ActionT, int, tuple[ActionT, ...], bool]:
    actions = _ordered_actions(state, _require_searchable(state, depth), action_orderer)
    perspective = state.current_player
    counter.visit()
    best_action = actions[0]
    best_value: int | None = None
    best_line: tuple[ActionT, ...] = ()
    alpha: int | None = None
    solved = True

    for action in actions:
        value, child_line, child_solved = _alpha_beta_value(
            state.apply(action),
            depth - 1,
            evaluator,
            perspective,
            alpha,
            None,
            counter,
            action_orderer,
            transposition_key,
            table,
        )
        if best_value is None or value > best_value:
            best_action = action
            best_value = value
            best_line = (action, *child_line)
        alpha = value if alpha is None else max(alpha, value)
        solved = solved and child_solved

    if best_value is None:  # pragma: no cover
        raise AssertionError("search root did not produce a decision")
    return best_action, best_value, best_line, solved


def alpha_beta_search[ActionT](
    state: GameState[ActionT],
    depth: int,
    evaluator: StateEvaluator[ActionT],
    *,
    action_orderer: ActionOrderer[ActionT] | None = None,
    transposition_key: StateKey[ActionT] | None = None,
) -> SearchResult[ActionT]:
    """Choose an action with deterministic depth-limited alpha-beta search."""
    counter = _SearchCounter()
    table: _TranspositionTable[ActionT] | None = (
        {} if transposition_key is not None else None
    )
    best_action, best_value, principal_variation, _ = _alpha_beta_iteration(
        state, depth, evaluator, counter, action_orderer, transposition_key, table
    )
    return SearchResult(
        action=best_action,
        value=best_value,
        nodes=counter.nodes,
        depth=depth,
        principal_variation=principal_variation,
        cutoffs=counter.cutoffs,
        transposition_hits=counter.transposition_hits,
    )


def iterative_deepening_search[ActionT](
    state: GameState[ActionT],
    budget: SearchBudget,
    evaluator: StateEvaluator[ActionT],
    *,
    action_orderer: ActionOrderer[ActionT] | None = None,
    transposition_key: StateKey[ActionT] | None = None,
) -> SearchResult[ActionT]:
    """Search complete depths in order without exceeding the supplied budget.

    Node budgets include all work across iterations. If depth one cannot be
    completed, the first legal action is returned with a depth of zero and the
    static root value. Partial iterations affect node and cutoff counts but do
    not replace the last fully completed decision.
    """
    actions = _ordered_actions(state, _require_searchable(state, 1), action_orderer)
    perspective = state.current_player
    if isinstance(budget, DepthBudget):
        node_limit = None
        requested_depth: int | None = budget.depth
    elif isinstance(budget, NodeBudget):
        node_limit = budget.nodes
        requested_depth = None
    else:
        raise ValueError(f"unsupported search budget: {type(budget).__name__}")
    counter = _SearchCounter(node_limit)
    table: _TranspositionTable[ActionT] | None = (
        {} if transposition_key is not None else None
    )
    completed: SearchResult[ActionT] | None = None
    depth = 1

    while requested_depth is None or depth <= requested_depth:
        try:
            action, value, line, solved = _alpha_beta_iteration(
                state,
                depth,
                evaluator,
                counter,
                action_orderer,
                transposition_key,
                table,
            )
        except _NodeLimitReached:
            break
        completed = SearchResult(
            action=action,
            value=value,
            nodes=counter.nodes,
            depth=depth,
            principal_variation=line,
            cutoffs=counter.cutoffs,
            iterations=depth,
            transposition_hits=counter.transposition_hits,
        )
        if requested_depth is None and solved:
            break
        depth += 1

    if completed is not None:
        return SearchResult(
            action=completed.action,
            value=completed.value,
            nodes=counter.nodes,
            depth=completed.depth,
            principal_variation=completed.principal_variation,
            cutoffs=counter.cutoffs,
            iterations=completed.iterations,
            transposition_hits=counter.transposition_hits,
        )

    # One root node is always affordable because NodeBudget is positive.
    if counter.nodes == 0:
        counter.visit()
    return SearchResult(
        action=actions[0],
        value=evaluator(state, perspective),
        nodes=counter.nodes,
        depth=0,
        principal_variation=(actions[0],),
        cutoffs=counter.cutoffs,
        iterations=0,
        transposition_hits=counter.transposition_hits,
    )
