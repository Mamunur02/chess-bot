import random
from io import StringIO

import chess

from chesslab.games import GameState
from chesslab.games.chess import ChessState
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget
from chesslab.search.classical import MATE_SCORE
from chesslab.search.results import SearchResult
from chesslab.uci import ENGINE_AUTHOR, ENGINE_NAME, UciSession, run_uci


class RecordingSearchAgent:
    def __init__(self, value: int = 25) -> None:
        self.value = value
        self.calls: list[tuple[str, SearchBudget]] = []

    def select_action(
        self,
        state: GameState[chess.Move],
        budget: SearchBudget,
        rng: random.Random,
    ) -> SearchResult[chess.Move]:
        del rng
        if not isinstance(state, ChessState):
            raise TypeError("test agent requires ChessState")
        self.calls.append((state.to_fen(), budget))
        action = state.legal_actions()[0]
        return SearchResult(
            action=action,
            value=self.value,
            nodes=7,
            depth=1,
            principal_variation=(action,),
        )


class ExplodingSearchAgent:
    def select_action(
        self,
        state: GameState[chess.Move],
        budget: SearchBudget,
        rng: random.Random,
    ) -> SearchResult[chess.Move]:
        del state, budget, rng
        raise RuntimeError("search failed")


def make_session(
    agent: RecordingSearchAgent | None = None,
) -> tuple[UciSession, RecordingSearchAgent]:
    search_agent = agent if agent is not None else RecordingSearchAgent()
    return UciSession(search_agent, random.Random(0)), search_agent


def test_handshake_readiness_stop_and_quit() -> None:
    session, _ = make_session()

    assert session.handle("uci") == (
        (
            f"id name {ENGINE_NAME}",
            f"id author {ENGINE_AUTHOR}",
            "uciok",
        ),
        True,
    )
    assert session.handle("isready") == (("readyok",), True)
    assert session.handle("stop") == ((), True)
    assert session.handle("quit") == ((), False)


def test_startpos_moves_and_depth_go_are_forwarded() -> None:
    session, agent = make_session()

    assert session.handle("position startpos moves e2e4 e7e5") == ((), True)
    responses, should_continue = session.handle("go depth 1")

    expected = ChessState().apply(chess.Move.from_uci("e2e4"))
    expected = expected.apply(chess.Move.from_uci("e7e5"))
    assert agent.calls == [(expected.to_fen(), DepthBudget(1))]
    assert should_continue
    assert responses[0].startswith("info depth 1 seldepth 1 score cp 25 nodes 7 pv ")
    assert responses[1].startswith("bestmove ")


def test_fen_position_and_node_budget_are_forwarded() -> None:
    session, agent = make_session()
    fen = "7k/q7/8/8/8/8/8/R1K5 w - - 0 1"

    assert session.handle(f"position fen {fen}") == ((), True)
    session.handle("go nodes 9")

    assert agent.calls == [(ChessState.from_fen(fen).to_fen(), NodeBudget(9))]


def test_movetime_maps_to_millisecond_budget() -> None:
    session, agent = make_session()

    session.handle("go movetime 15")

    assert isinstance(agent.calls[0][1], TimeBudget)
    assert agent.calls[0][1].milliseconds == 15


def test_invalid_position_does_not_replace_the_current_state() -> None:
    session, agent = make_session()
    session.handle("position startpos moves e2e4")

    responses, _ = session.handle("position startpos moves e2e5")
    session.handle("go depth 1")

    expected = ChessState().apply(chess.Move.from_uci("e2e4"))
    assert responses[0].startswith("info string error illegal move")
    assert agent.calls[0][0] == expected.to_fen()


def test_invalid_go_returns_null_move_without_calling_agent() -> None:
    session, agent = make_session()

    responses, should_continue = session.handle("go infinite")

    assert should_continue
    assert responses[0].startswith("info string error")
    assert responses[1] == "bestmove 0000"
    assert agent.calls == []


def test_invalid_and_unsupported_commands_report_errors() -> None:
    session, _ = make_session()

    malformed_position, _ = session.handle("position fen invalid")
    unsupported, _ = session.handle("setoption name Hash value 16")
    blank, _ = session.handle("   ")

    assert malformed_position[0].startswith("info string error")
    assert unsupported == ("info string error unsupported command: setoption",)
    assert blank == ()


def test_agent_failure_is_reported_without_crashing_session() -> None:
    session = UciSession(ExplodingSearchAgent(), random.Random(0))

    responses, should_continue = session.handle("go depth 1")

    assert should_continue
    assert responses == (
        "info string error search failed",
        "bestmove 0000",
    )


def test_mate_score_is_emitted_in_uci_mate_form() -> None:
    session, _ = make_session(RecordingSearchAgent(MATE_SCORE))

    responses, _ = session.handle("go depth 1")

    assert "score mate 1" in responses[0]


def test_new_game_restores_the_initial_position() -> None:
    session, agent = make_session()
    session.handle("position startpos moves e2e4")

    session.handle("ucinewgame")
    session.handle("go depth 1")

    assert agent.calls[0][0] == ChessState().to_fen()


def test_run_uci_writes_responses_and_stops_after_quit() -> None:
    session, agent = make_session()
    input_stream = StringIO("uci\nisready\nquit\ngo depth 1\n")
    output_stream = StringIO()

    run_uci(input_stream, output_stream, session)

    assert output_stream.getvalue().splitlines() == [
        f"id name {ENGINE_NAME}",
        f"id author {ENGINE_AUTHOR}",
        "uciok",
        "readyok",
    ]
    assert agent.calls == []
