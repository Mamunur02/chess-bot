"""Minimal synchronous UCI interface for the material alpha-beta baseline."""

import random
import sys
from collections.abc import Sequence
from typing import Protocol, TextIO

import chess

from chesslab.agents.material_alpha_beta import MaterialAlphaBetaAgent
from chesslab.games import GameState
from chesslab.games.chess import ChessState
from chesslab.search import DepthBudget, NodeBudget, SearchBudget, TimeBudget
from chesslab.search.classical import MATE_SCORE
from chesslab.search.results import SearchResult

ENGINE_NAME = "Chess AI Lab"
ENGINE_AUTHOR = "Chess AI Lab contributors"


class UciSearchAgent(Protocol):
    """Agent contract required to emit UCI search information."""

    def select_action(
        self,
        state: GameState[chess.Move],
        budget: SearchBudget,
        rng: random.Random,
    ) -> SearchResult[chess.Move]:
        """Return a searched move and its measured statistics."""
        ...


def _parse_positive_integer(token: str, label: str) -> int:
    try:
        value = int(token)
    except ValueError as error:
        raise ValueError(f"{label} must be a positive integer") from error
    if value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _split_position_arguments(
    tokens: Sequence[str],
) -> tuple[ChessState, Sequence[str]]:
    if not tokens:
        raise ValueError("position requires startpos or fen")

    if tokens[0] == "startpos":
        state = ChessState()
        remainder = tokens[1:]
    elif tokens[0] == "fen":
        try:
            moves_index = tokens.index("moves")
        except ValueError:
            moves_index = len(tokens)
        fen_tokens = tokens[1:moves_index]
        if len(fen_tokens) != 6:
            raise ValueError("position fen requires exactly six FEN fields")
        state = ChessState.from_fen(" ".join(fen_tokens))
        remainder = tokens[moves_index:]
    else:
        raise ValueError("position requires startpos or fen")

    if not remainder:
        return state, ()
    if remainder[0] != "moves":
        raise ValueError("unexpected position arguments")
    return state, remainder[1:]


def _position_from_tokens(tokens: Sequence[str]) -> ChessState:
    state, move_tokens = _split_position_arguments(tokens)
    for token in move_tokens:
        try:
            move = chess.Move.from_uci(token)
        except ValueError as error:
            raise ValueError(f"invalid UCI move: {token}") from error
        state = state.apply(move)
    return state


def _budget_from_go(tokens: Sequence[str]) -> SearchBudget:
    if len(tokens) != 2:
        raise ValueError("go requires exactly one of depth, nodes, or movetime")
    kind, raw_value = tokens
    value = _parse_positive_integer(raw_value, kind)
    if kind == "depth":
        return DepthBudget(value)
    if kind == "nodes":
        return NodeBudget(value)
    if kind == "movetime":
        return TimeBudget(value)
    raise ValueError("go supports only depth, nodes, or movetime")


def _score_fields(result: SearchResult[chess.Move]) -> tuple[str, str]:
    if abs(result.value) < MATE_SCORE:
        return ("cp", str(result.value))
    moves_to_mate = max(1, (len(result.principal_variation) + 1) // 2)
    if result.value < 0:
        moves_to_mate = -moves_to_mate
    return ("mate", str(moves_to_mate))


def _info_line(result: SearchResult[chess.Move]) -> str:
    score_kind, score_value = _score_fields(result)
    fields = [
        "info",
        "depth",
        str(result.depth),
        "seldepth",
        str(len(result.principal_variation)),
        "score",
        score_kind,
        score_value,
        "nodes",
        str(result.nodes),
    ]
    if result.elapsed_seconds is not None:
        fields.extend(("time", str(round(result.elapsed_seconds * 1000))))
    if result.principal_variation:
        fields.append("pv")
        fields.extend(move.uci() for move in result.principal_variation)
    return " ".join(fields)


class UciSession:
    """Stateful command handler for one synchronous UCI session."""

    def __init__(
        self,
        agent: UciSearchAgent,
        rng: random.Random,
    ) -> None:
        self._agent = agent
        self._rng = rng
        self._state = ChessState()

    def handle(self, command: str) -> tuple[tuple[str, ...], bool]:
        """Handle one command and return output lines plus continuation state."""
        tokens = command.strip().split()
        if not tokens:
            return ((), True)
        name, arguments = tokens[0], tokens[1:]

        if name == "uci":
            return (
                (
                    f"id name {ENGINE_NAME}",
                    f"id author {ENGINE_AUTHOR}",
                    "uciok",
                ),
                True,
            )
        if name == "isready":
            return (("readyok",), True)
        if name == "ucinewgame":
            self._state = ChessState()
            return ((), True)
        if name == "position":
            try:
                state = _position_from_tokens(arguments)
            except ValueError as error:
                return ((f"info string error {error}",), True)
            self._state = state
            return ((), True)
        if name == "go":
            try:
                budget = _budget_from_go(arguments)
                result = self._agent.select_action(self._state, budget, self._rng)
            except Exception as error:
                return (
                    (f"info string error {error}", "bestmove 0000"),
                    True,
                )
            return (
                (_info_line(result), f"bestmove {result.action.uci()}"),
                True,
            )
        if name == "stop":
            return ((), True)
        if name == "quit":
            return ((), False)
        return ((f"info string error unsupported command: {name}",), True)


def run_uci(
    input_stream: TextIO,
    output_stream: TextIO,
    session: UciSession,
) -> None:
    """Process UCI commands synchronously until quit or end of input."""
    for line in input_stream:
        responses, should_continue = session.handle(line)
        for response in responses:
            print(response, file=output_stream, flush=True)
        if not should_continue:
            break


def main() -> None:
    """Run the baseline engine over standard input and output."""
    session = UciSession(MaterialAlphaBetaAgent(), random.Random(0))
    run_uci(sys.stdin, sys.stdout, session)
