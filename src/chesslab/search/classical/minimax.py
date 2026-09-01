"""Depth-limited minimax and alpha-beta search with explicit perspective."""

from collections.abc import Callable, Sequence

from chesslab.games import GameState, Player
from chesslab.search.results import SearchResult

MATE_SCORE = 1_000_000

type StateEvaluator[ActionT] = Callable[[GameState[ActionT], Player], int]


def terminal_score[ActionT](
    state: GameState[ActionT], perspective: Player
) -> int:
    """Return a terminal score from one stable player's perspective."""
    if not state.is_terminal():
        raise ValueError("terminal score requires a terminal state")

    value = state.returns()[perspective]
    if value > 0:
        return MATE_SCORE
    if value < 0:
        return -MATE_SCORE
    return 0


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
        value, child_nodes = _alpha_beta_value(
            state.apply(action), depth - 1, evaluator, perspective, alpha, beta
        )
        nodes += child_nodes
        if best_value is None or (maximizing and value > best_value):
            best_value = value
        elif not maximizing and value < best_value:
            best_value = value

        if maximizing:
            alpha = best_value if alpha is None else max(alpha, best_value)
        else:
            beta = best_value if beta is None else min(beta, best_value)
        if alpha is not None and beta is not None and alpha >= beta:
            break

    if best_value is None:  # pragma: no cover - guarded by the actions check
        raise AssertionError("search node did not produce a value")
    return best_value, nodes


def alpha_beta_search[ActionT](
    state: GameState[ActionT],
    depth: int,
    evaluator: StateEvaluator[ActionT],
) -> SearchResult[ActionT]:
    """Choose an action with deterministic depth-limited alpha-beta search."""
    actions = _require_searchable(state, depth)
    perspective = state.current_player
    best_action = actions[0]
    best_value: int | None = None
    alpha: int | None = None
    nodes = 1

    for action in actions:
        value, child_nodes = _alpha_beta_value(
            state.apply(action), depth - 1, evaluator, perspective, alpha, None
        )
        nodes += child_nodes
        if best_value is None or value > best_value:
            best_action = action
            best_value = value
        alpha = value if alpha is None else max(alpha, value)

    if best_value is None:  # pragma: no cover
        raise AssertionError("search root did not produce a decision")
    return SearchResult(
        action=best_action,
        value=best_value,
        nodes=nodes,
        depth=depth,
    )
