"""Experiment-specific game rules that preserve full chess history."""

import chess


def terminal_reward(board: chess.Board, learner: chess.Color) -> float | None:
    """Return terminal reward from the fixed learner's view, or ``None``.

    Draw claims use python-chess's prospective claim semantics. Administrative
    truncation is managed by the caller and is deliberately not a game result.
    """
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return None
    if outcome.winner is None:
        return 0.0
    return 1.0 if outcome.winner == learner else -1.0


def child_board(board: chess.Board, move: chess.Move) -> chess.Board:
    """Return a legal child while retaining the parent's complete move stack.

    Raises ``ValueError`` when the board is already terminal or the move is
    illegal. The input board is never modified.
    """
    if board.outcome(claim_draw=True) is not None:
        raise ValueError("cannot act on a terminal board")
    if move not in board.legal_moves:
        raise ValueError(f"illegal move: {move}")
    child = board.copy(stack=True)
    child.push(move)
    return child
