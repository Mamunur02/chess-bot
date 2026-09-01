import pytest

from chesslab.games.chess import ChessState, perft


@pytest.mark.parametrize(
    "depth, expected_nodes",
    [(0, 1), (1, 20), (2, 400), (3, 8_902)],
)
def test_initial_position_perft(depth: int, expected_nodes: int) -> None:
    assert perft(ChessState(), depth) == expected_nodes


@pytest.mark.parametrize("depth", [-1, True])
def test_perft_rejects_invalid_depth(depth: int) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        perft(ChessState(), depth)
