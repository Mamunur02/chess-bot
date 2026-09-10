"""Depth-limited minimax and alpha-beta search with explicit perspective."""

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from time import perf_counter

from chesslab.games import GameState, Player
from chesslab.search.budgets import DepthBudget, NodeBudget, SearchBudget, TimeBudget
from chesslab.search.results import SearchResult

MATE_SCORE = 1_000_000

type StateEvaluator[ActionT] = Callable[[GameState[ActionT], Player], int]
type ActionOrderer[ActionT] = Callable[
    [GameState[ActionT], Sequence[ActionT]], Sequence[ActionT]
]
type StateKey[ActionT] = Callable[[GameState[ActionT]], Hashable]
type Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class QuiescenceExpansion[ActionT]:
    """Tactical actions and whether static stand-pat evaluation is legal."""

    actions: Sequence[ActionT]
    allow_stand_pat: bool


type QuiescenceSelector[ActionT] = Callable[
    [GameState[ActionT]], QuiescenceExpansion[ActionT]
]


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


class _SearchLimitReached(Exception):
    """Internal control flow used to stop before exceeding a search budget."""


class _SearchCounter:
    def __init__(
        self,
        node_limit: int | None = None,
        deadline: float | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.node_limit = node_limit
        self.deadline = deadline
        self.clock = clock
        self.nodes = 0
        self.cutoffs = 0
        self.transposition_hits = 0
        self.quiescence_nodes = 0

    def visit(self) -> None:
        if self.node_limit is not None and self.nodes >= self.node_limit:
            raise _SearchLimitReached
        if self.deadline is not None:
            if self.clock is None:  # pragma: no cover - internal invariant
                raise AssertionError("a deadline requires a clock")
            if self.clock() >= self.deadline:
                raise _SearchLimitReached
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


def _validated_subset[ActionT](
    legal_actions: Sequence[ActionT],
    selected_actions: Sequence[ActionT],
) -> tuple[ActionT, ...]:
    selected = tuple(selected_actions)
    remaining = list(legal_actions)
    for action in selected:
        try:
            remaining.remove(action)
        except ValueError as error:
            raise ValueError(
                "quiescence selector returned an unknown or duplicate action"
            ) from error
    return selected


def _quiescence_value[ActionT](
    state: GameState[ActionT],
    remaining_depth: int,
    evaluator: StateEvaluator[ActionT],
    perspective: Player,
    alpha: int | None,
    beta: int | None,
    counter: _SearchCounter,
    action_orderer: ActionOrderer[ActionT] | None,
    selector: QuiescenceSelector[ActionT],
    *,
    count_node: bool,
) -> tuple[int, tuple[ActionT, ...], bool]:
    if count_node:
        counter.visit()
    counter.quiescence_nodes += 1
    if state.is_terminal():
        return terminal_score(state, perspective), (), True

    stand_pat = evaluator(state, perspective)
    if remaining_depth == 0:
        return stand_pat, (), False

    expansion = selector(state)
    legal_actions = state.legal_actions()
    actions = _validated_subset(legal_actions, expansion.actions)
    actions = _ordered_actions(state, actions, action_orderer)
    maximizing = state.current_player == perspective
    best_value: int | None = stand_pat if expansion.allow_stand_pat else None
    best_line: tuple[ActionT, ...] = ()

    if expansion.allow_stand_pat:
        if maximizing:
            if beta is not None and stand_pat >= beta:
                counter.cutoffs += 1
                return stand_pat, (), False
            alpha = stand_pat if alpha is None else max(alpha, stand_pat)
        else:
            if alpha is not None and stand_pat <= alpha:
                counter.cutoffs += 1
                return stand_pat, (), False
            beta = stand_pat if beta is None else min(beta, stand_pat)
    elif not actions:
        raise ValueError(
            "quiescence selector disabled stand pat without returning actions"
        )

    for action in actions:
        value, child_line, _ = _quiescence_value(
            state.apply(action),
            remaining_depth - 1,
            evaluator,
            perspective,
            alpha,
            beta,
            counter,
            action_orderer,
            selector,
            count_node=True,
        )
        if best_value is None or (maximizing and value > best_value):
            best_value = value
            best_line = (action, *child_line)
        elif not maximizing and value < best_value:
            best_value = value
            best_line = (action, *child_line)

        if maximizing:
            alpha = best_value if alpha is None else max(alpha, best_value)
        else:
            beta = best_value if beta is None else min(beta, best_value)
        if alpha is not None and beta is not None and alpha >= beta:
            counter.cutoffs += 1
            break

    if best_value is None:  # pragma: no cover - guarded above
        raise AssertionError("quiescence search did not produce a value")
    return best_value, best_line, False


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
    quiescence_selector: QuiescenceSelector[ActionT] | None,
    quiescence_depth: int,
) -> tuple[int, tuple[ActionT, ...], bool]:
    counter.visit()
    if state.is_terminal():
        return terminal_score(state, perspective), (), True
    if depth == 0:
        if quiescence_selector is not None:
            return _quiescence_value(
                state,
                quiescence_depth,
                evaluator,
                perspective,
                alpha,
                beta,
                counter,
                action_orderer,
                quiescence_selector,
                count_node=False,
            )
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
            quiescence_selector,
            quiescence_depth,
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
    quiescence_selector: QuiescenceSelector[ActionT] | None,
    quiescence_depth: int,
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
            quiescence_selector,
            quiescence_depth,
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


def _validate_quiescence_config[ActionT](
    selector: QuiescenceSelector[ActionT] | None,
    depth: int,
) -> None:
    if isinstance(depth, bool) or depth < 0:
        raise ValueError("quiescence depth must be a non-negative integer")
    if depth == 0 and selector is not None:
        raise ValueError("quiescence selector requires a positive depth")
    if depth > 0 and selector is None:
        raise ValueError("positive quiescence depth requires a selector")


def alpha_beta_search[ActionT](
    state: GameState[ActionT],
    depth: int,
    evaluator: StateEvaluator[ActionT],
    *,
    action_orderer: ActionOrderer[ActionT] | None = None,
    transposition_key: StateKey[ActionT] | None = None,
    quiescence_selector: QuiescenceSelector[ActionT] | None = None,
    quiescence_depth: int = 0,
) -> SearchResult[ActionT]:
    """Choose an action with deterministic depth-limited alpha-beta search."""
    _validate_quiescence_config(quiescence_selector, quiescence_depth)
    counter = _SearchCounter()
    table: _TranspositionTable[ActionT] | None = (
        {} if transposition_key is not None else None
    )
    best_action, best_value, principal_variation, _ = _alpha_beta_iteration(
        state,
        depth,
        evaluator,
        counter,
        action_orderer,
        transposition_key,
        table,
        quiescence_selector,
        quiescence_depth,
    )
    return SearchResult(
        action=best_action,
        value=best_value,
        nodes=counter.nodes,
        depth=depth,
        principal_variation=principal_variation,
        cutoffs=counter.cutoffs,
        transposition_hits=counter.transposition_hits,
        quiescence_nodes=counter.quiescence_nodes,
    )


def iterative_deepening_search[ActionT](
    state: GameState[ActionT],
    budget: SearchBudget,
    evaluator: StateEvaluator[ActionT],
    *,
    action_orderer: ActionOrderer[ActionT] | None = None,
    transposition_key: StateKey[ActionT] | None = None,
    quiescence_selector: QuiescenceSelector[ActionT] | None = None,
    quiescence_depth: int = 0,
    clock: Clock = perf_counter,
) -> SearchResult[ActionT]:
    """Search complete depths in order without exceeding the supplied budget.

    Node and time budgets include all work across iterations. If depth one
    cannot be completed, the first legal action is returned with a depth of
    zero and the static root value. A time budget can expire before the root is
    entered, in which case the node count is zero. Partial iterations affect
    statistics but do not replace the last fully completed decision.
    """
    _validate_quiescence_config(quiescence_selector, quiescence_depth)
    started_at: float | None = None
    deadline: float | None = None
    if isinstance(budget, DepthBudget):
        node_limit = None
        requested_depth: int | None = budget.depth
    elif isinstance(budget, NodeBudget):
        node_limit = budget.nodes
        requested_depth = None
    elif isinstance(budget, TimeBudget):
        node_limit = None
        requested_depth = None
        started_at = clock()
        deadline = started_at + budget.milliseconds / 1000
    else:
        raise ValueError(f"unsupported search budget: {type(budget).__name__}")
    actions = _ordered_actions(state, _require_searchable(state, 1), action_orderer)
    perspective = state.current_player
    counter = _SearchCounter(
        node_limit, deadline, clock if deadline is not None else None
    )
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
                quiescence_selector,
                quiescence_depth,
            )
        except _SearchLimitReached:
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
            quiescence_nodes=counter.quiescence_nodes,
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
            quiescence_nodes=counter.quiescence_nodes,
            elapsed_seconds=(
                None if started_at is None else max(0.0, clock() - started_at)
            ),
        )

    # One root node is always affordable under a positive node budget.
    if counter.nodes == 0 and deadline is None:
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
        quiescence_nodes=counter.quiescence_nodes,
        elapsed_seconds=(
            None if started_at is None else max(0.0, clock() - started_at)
        ),
    )
