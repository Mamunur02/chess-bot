"""Immutable-looking chess state backed by :class:`chess.Board`."""

from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType
from typing import Self

import chess

from chesslab.games import Player, TerminalReturns

type ChessTranspositionKey = tuple[
    str,
    int,
    tuple[tuple[str, int], ...],
]


def _position_key(board: chess.Board) -> str:
    return " ".join(board.fen(en_passant="legal").split()[:4])


class ChessState:
    """A standard-chess state with private, exclusively owned board data.

    Claimable draws are not automatic terminal outcomes. Fivefold repetition
    and the seventy-five-move rule remain automatic through ``python-chess``.
    """

    __slots__ = ("__board",)

    def __init__(self) -> None:
        """Create the standard initial chess position."""
        self.__board = chess.Board()

    @classmethod
    def from_fen(cls, fen: str) -> Self:
        """Create a valid state from FEN without repetition history."""
        try:
            board = chess.Board(fen)
        except ValueError as error:
            raise ValueError(f"invalid FEN: {fen}") from error

        if not board.is_valid():
            raise ValueError(f"invalid chess position: {fen}")
        return cls._from_owned_board(board)

    @classmethod
    def _from_owned_board(cls, board: chess.Board) -> Self:
        state = cls.__new__(cls)
        state.__board = board
        return state

    @property
    def current_player(self) -> Player:
        """Return player 0 for White and player 1 for Black."""
        return 0 if self.__board.turn == chess.WHITE else 1

    def legal_actions(self) -> tuple[chess.Move, ...]:
        """Return all legal moves for the side to move."""
        if self.is_terminal():
            return ()
        return tuple(self.__board.legal_moves)

    def apply(self, action: chess.Move) -> Self:
        """Return the child state without mutating this state."""
        if self.is_terminal() or not self.__board.is_legal(action):
            raise ValueError(f"illegal move: {action.uci()}")

        child_board = self.__board.copy(stack=True)
        child_board.push(action)
        return type(self)._from_owned_board(child_board)

    def is_capture(self, action: chess.Move) -> bool:
        """Return whether a legal action captures, including en passant."""
        if self.is_terminal() or not self.__board.is_legal(action):
            raise ValueError(f"illegal move: {action.uci()}")
        return self.__board.is_capture(action)

    def is_in_check(self) -> bool:
        """Return whether the side to move is in check."""
        return self.__board.is_check()

    def is_terminal(self) -> bool:
        """Return whether an automatic standard-chess outcome exists."""
        return self.__board.outcome(claim_draw=False) is not None

    def returns(self) -> TerminalReturns:
        """Return terminal utilities ordered as ``(White, Black)``."""
        outcome = self.__board.outcome(claim_draw=False)
        if outcome is None:
            raise ValueError("returns are only defined for terminal states")
        if outcome.winner is None:
            return (0.0, 0.0)
        if outcome.winner == chess.WHITE:
            return (1.0, -1.0)
        return (-1.0, 1.0)

    def to_fen(self) -> str:
        """Serialize the position fields; repetition history is not included."""
        return self.__board.fen(en_passant="fen")

    def transposition_key(self) -> ChessTranspositionKey:
        """Return a conservative key including repetition-relevant history."""
        replay = self.__board.copy(stack=True)
        historical_positions = [_position_key(replay)]
        while replay.move_stack:
            move = replay.pop()
            if replay.is_irreversible(move):
                break
            historical_positions.append(_position_key(replay))
        position_counts = Counter(historical_positions)
        return (
            _position_key(self.__board),
            self.__board.halfmove_clock,
            tuple(sorted(position_counts.items())),
        )

    def piece_map(self) -> Mapping[chess.Square, chess.Piece]:
        """Return an immutable snapshot of the pieces by square."""
        return MappingProxyType(self.__board.piece_map())
