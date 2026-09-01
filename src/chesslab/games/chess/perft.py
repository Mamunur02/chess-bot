"""Small correctness-oriented perft implementation for the chess adapter."""

from chesslab.games.chess.state import ChessState


def perft(state: ChessState, depth: int) -> int:
    """Count legal move sequences from ``state`` to exactly ``depth`` plies."""
    if isinstance(depth, bool) or depth < 0:
        raise ValueError("depth must be a non-negative integer")
    if depth == 0:
        return 1
    return sum(
        perft(state.apply(action), depth - 1) for action in state.legal_actions()
    )
