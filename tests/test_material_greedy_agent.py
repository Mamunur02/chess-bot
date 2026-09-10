import random

import chess
import pytest

from chesslab.agents import Agent, MaterialGreedyAgent
from chesslab.games import GameState
from chesslab.games.chess import ChessState
from chesslab.search import DepthBudget, NodeBudget
from chesslab.search.classical import MATE_SCORE

CHECKMATE_FEN = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
FREE_QUEEN_FEN = "7k/q7/8/8/8/8/8/R1K5 w - - 0 1"
MATE_OR_CAPTURE_FEN = "7k/8/5KQ1/8/8/8/8/1r6 w - - 0 1"


def require_agent(
    agent: Agent[GameState[chess.Move], chess.Move],
) -> Agent[GameState[chess.Move], chess.Move]:
    return agent


def test_agent_implements_contract_and_captures_free_queen() -> None:
    agent = MaterialGreedyAgent()
    require_agent(agent)

    result = agent.select_action(
        ChessState.from_fen(FREE_QUEEN_FEN),
        NodeBudget(1),
        random.Random(1),
    )

    assert result.action == chess.Move.from_uci("a1a7")
    assert result.value == 500
    assert result.depth == 1
    assert result.nodes == 13


def test_agent_prefers_immediate_mate_over_material_capture() -> None:
    result = MaterialGreedyAgent().select_action(
        ChessState.from_fen(MATE_OR_CAPTURE_FEN),
        DepthBudget(7),
        random.Random(2),
    )

    assert result.action == chess.Move.from_uci("g6g7")
    assert result.value == MATE_SCORE


def test_agent_is_independent_of_budget_and_rng() -> None:
    state = ChessState.from_fen(FREE_QUEEN_FEN)
    agent = MaterialGreedyAgent()

    first = agent.select_action(state, NodeBudget(1), random.Random(1))
    repeated = agent.select_action(state, DepthBudget(9), random.Random(999))

    assert first == repeated


def test_equal_values_preserve_python_chess_legal_order() -> None:
    state = ChessState()

    result = MaterialGreedyAgent().select_action(
        state,
        NodeBudget(1),
        random.Random(0),
    )

    assert result.action == state.legal_actions()[0]


def test_agent_rejects_terminal_state() -> None:
    with pytest.raises(ValueError, match="terminal state"):
        MaterialGreedyAgent().select_action(
            ChessState.from_fen(CHECKMATE_FEN),
            NodeBudget(1),
            random.Random(0),
        )


def test_agent_rejects_non_chess_state() -> None:
    class NotChess:
        pass

    with pytest.raises(TypeError, match="requires ChessState"):
        MaterialGreedyAgent().select_action(
            NotChess(),  # type: ignore[arg-type]
            NodeBudget(1),
            random.Random(0),
        )
