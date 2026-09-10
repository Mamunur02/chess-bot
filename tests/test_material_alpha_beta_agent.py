import random

import chess
import pytest

from chesslab.agents import Agent
from chesslab.agents.material_alpha_beta import MaterialAlphaBetaAgent
from chesslab.games import GameState
from chesslab.games.chess import ChessState
from chesslab.search import DepthBudget, NodeBudget
from chesslab.search.classical import MATE_SCORE, terminal_score

CHECKMATE_FEN = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
STALEMATE_FEN = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
FREE_QUEEN_FEN = "7k/q7/8/8/8/8/8/R1K5 w - - 0 1"
MATE_OR_CAPTURE_FEN = "7k/8/5KQ1/8/8/8/8/1r6 w - - 0 1"


def require_agent(
    agent: Agent[GameState[chess.Move], chess.Move],
) -> Agent[GameState[chess.Move], chess.Move]:
    return agent


def test_agent_implements_contract_and_captures_free_queen() -> None:
    agent = MaterialAlphaBetaAgent()
    require_agent(agent)

    result = agent.select_action(
        ChessState.from_fen(FREE_QUEEN_FEN), DepthBudget(1), random.Random(1)
    )

    assert result.action == chess.Move.from_uci("a1a7")
    assert result.value == 500
    assert result.depth == 1


def test_agent_prefers_mate_over_material_capture() -> None:
    result = MaterialAlphaBetaAgent().select_action(
        ChessState.from_fen(MATE_OR_CAPTURE_FEN),
        DepthBudget(1),
        random.Random(2),
    )

    assert result.action == chess.Move.from_uci("g6g7")
    assert result.value == MATE_SCORE


def test_agent_is_independent_of_rng_state() -> None:
    state = ChessState.from_fen(FREE_QUEEN_FEN)
    agent = MaterialAlphaBetaAgent()

    first = agent.select_action(state, DepthBudget(1), random.Random(1))
    repeated = agent.select_action(state, DepthBudget(1), random.Random(999))

    assert first == repeated


def test_terminal_chess_scores_override_material() -> None:
    checkmate = ChessState.from_fen(CHECKMATE_FEN)
    stalemate = ChessState.from_fen(STALEMATE_FEN)

    assert terminal_score(checkmate, 0) == -MATE_SCORE
    assert terminal_score(checkmate, 1) == MATE_SCORE
    assert terminal_score(stalemate, 0) == 0
    assert terminal_score(stalemate, 1) == 0


def test_agent_honors_node_budget() -> None:
    state = ChessState.from_fen(FREE_QUEEN_FEN)
    result = MaterialAlphaBetaAgent().select_action(
        state, NodeBudget(4), random.Random(0)
    )

    assert result.action in state.legal_actions()
    assert result.nodes == 4
    assert result.depth == 0


def test_capture_ordering_changes_only_the_tiny_budget_fallback_order() -> None:
    state = ChessState.from_fen(FREE_QUEEN_FEN)

    unordered = MaterialAlphaBetaAgent().select_action(
        state, NodeBudget(1), random.Random(0)
    )
    ordered = MaterialAlphaBetaAgent(capture_ordering=True).select_action(
        state, NodeBudget(1), random.Random(0)
    )

    assert unordered.action == chess.Move.from_uci("c1d2")
    assert ordered.action == chess.Move.from_uci("a1a7")
    assert state.is_capture(ordered.action)
    assert (unordered.nodes, ordered.nodes) == (1, 1)


def test_agent_rejects_terminal_state() -> None:
    with pytest.raises(ValueError, match="terminal state"):
        MaterialAlphaBetaAgent().select_action(
            ChessState.from_fen(CHECKMATE_FEN),
            DepthBudget(1),
            random.Random(0),
        )
