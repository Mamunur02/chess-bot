"""A reproducible, fallible opponent for pawnless endgame experiments."""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass

import chess

from chesslab.endgames.reference import ReferenceValue, SyzygyProbe, evaluate


@dataclass(frozen=True, slots=True)
class ActionAudit:
    """Reference and selection diagnostics for one legal opponent action."""

    move: chess.Move
    q: int
    raw_wdl: int | None
    raw_dtz: int | None
    history_occurrences: int
    immediate_mate: bool


@dataclass(frozen=True, slots=True)
class OpponentDecision:
    """A selected move and per-decision counters for experiment aggregation."""

    action: chess.Move
    selected_q: int
    actions: tuple[ActionAudit, ...]
    category_loss: int
    opportunity: bool
    realized_worsening: bool
    requested_p: float


def _position_identity(board: chess.Board) -> tuple[str, chess.Color, int, int | None]:
    """Return actual repetition identity, excluding clocks and move counters."""

    legal_ep = board.ep_square if board.has_legal_en_passant() else None
    return board.board_fen(), board.turn, board.castling_rights, legal_ep


def _history_occurrences(
    board: chess.Board,
) -> Counter[tuple[str, chess.Color, int, int | None]]:
    """Count identities in actual history, including the current parent board."""

    history = board.root()
    occurrences: Counter[tuple[str, chess.Color, int, int | None]] = Counter()
    occurrences[_position_identity(history)] += 1
    for move in board.move_stack:
        history.push(move)
        occurrences[_position_identity(history)] += 1
    return occurrences


def _tie_key(action: ActionAudit) -> tuple[int, int, int, str]:
    """Order best moves by protocol progress rules without changing q class."""

    dtz = abs(action.raw_dtz) if action.raw_dtz is not None else 0
    if action.q > 0:
        dtz_key = dtz
    elif action.q < 0:
        dtz_key = -dtz
    else:
        dtz_key = 0
    return (
        -int(action.immediate_mate),
        action.history_occurrences,
        dtz_key,
        action.move.uci(),
    )


def choose_action(
    board: chess.Board,
    tablebase: SyzygyProbe,
    rng: random.Random,
    p: float,
) -> OpponentDecision:
    """Choose a legal move, sometimes uniformly worsening theoretical WDL.

    The input board is never modified. Live termination follows
    ``outcome(claim_draw=True)``; reference labels deliberately ignore claims,
    clocks, and prior history. The caller owns the RNG and aggregates returned
    counters across decisions.
    """

    if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p):
        raise ValueError("p must be finite and between 0 and 1 inclusive")
    if not 0 <= p <= 1:
        raise ValueError("p must be finite and between 0 and 1 inclusive")
    if board.outcome(claim_draw=True) is not None:
        raise ValueError("cannot choose an action on a terminal board")

    moves = tuple(board.legal_moves)
    if not moves:
        raise ValueError("cannot choose an action without legal moves")

    occurrences = _history_occurrences(board)
    audits: list[ActionAudit] = []
    for move in moves:
        child = board.copy(stack=True)
        child.push(move)
        reference: ReferenceValue = evaluate(child, tablebase)
        audits.append(
            ActionAudit(
                move=move,
                q=-reference.value,
                raw_wdl=reference.raw_wdl,
                raw_dtz=reference.raw_dtz,
                history_occurrences=occurrences[_position_identity(child)],
                immediate_mate=child.is_checkmate(),
            )
        )

    best_q = max(action.q for action in audits)
    best_actions = [action for action in audits if action.q == best_q]
    worsening = [action for action in audits if action.q < best_q]
    best_action = min(best_actions, key=_tie_key)

    selected = best_action
    if worsening and p > 0 and (p == 1 or rng.random() < p):
        selected = rng.choice(worsening)

    realized_worsening = selected.q < best_q
    return OpponentDecision(
        action=selected.move,
        selected_q=selected.q,
        actions=tuple(audits),
        category_loss=best_q - selected.q,
        opportunity=bool(worsening),
        realized_worsening=realized_worsening,
        requested_p=float(p),
    )
