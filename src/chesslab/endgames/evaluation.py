"""Fixed-start policy, value-prediction, and bounded game evaluation."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import chess

from chesslab.endgames.identity import canonical_position
from chesslab.endgames.interaction import MAX_GAME_PLIES, select_learner_move
from chesslab.endgames.opponent import choose_action
from chesslab.endgames.reference import SyzygyProbe
from chesslab.endgames.reference import evaluate as evaluate_reference
from chesslab.endgames.rules import child_board, terminal_reward
from chesslab.endgames.targets import Predictor


@dataclass(frozen=True, slots=True)
class ChoiceRecord:
    key: str
    learner: chess.Color
    selected_move: str
    selected_q: int
    best_q: int
    loss: bool
    categorical_loss: float


@dataclass(frozen=True, slots=True)
class ChoiceEvaluation:
    records: tuple[ChoiceRecord, ...]
    loss_rate: float
    mean_categorical_loss: float
    loss_rate_by_best_q: tuple[tuple[int, float], ...]


@dataclass(frozen=True, slots=True)
class PredictionEvaluation:
    count: int
    mse: float
    predictions: tuple[float, ...]
    targets: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class GameEvaluation:
    start_fen: str
    learner: chess.Color
    p: float
    reward: float | None
    truncated: bool
    truncation_reason: str | None
    failure: str | None
    plies: int
    moves: tuple[str, ...]
    learner_decisions: int
    reference_evaluated_decisions: int
    predictor_calls: int
    forward_evaluations: int
    learner_reference_errors: int
    reference_failures: int
    neural_work: int
    encountered_keys: tuple[str, ...]
    choice_records: tuple[ChoiceRecord, ...]


def evaluate_choices(
    boards: Sequence[chess.Board], predictor: Predictor, tablebase: SyzygyProbe
) -> ChoiceEvaluation:
    """Measure greedy epsilon-zero selection against all theoretical actions."""
    records: list[ChoiceRecord] = []
    for board in boards:
        if terminal_reward(board, board.turn) is not None:
            raise ValueError("choice starts must be live")
        learner = board.turn
        selected = select_learner_move(board, learner, predictor, random.Random(0), 0.0)
        values = {
            move: -evaluate_reference(child_board(board, move), tablebase).value
            for move in board.legal_moves
        }
        best_q = max(values.values())
        selected_q = values[selected.action]
        records.append(
            ChoiceRecord(
                canonical_position(board),
                learner,
                selected.action.uci(),
                selected_q,
                best_q,
                selected_q < best_q,
                (best_q - selected_q) / 2.0,
            )
        )
    if not records:
        raise ValueError("at least one board is required")
    strata = tuple(
        (
            q,
            sum(record.loss for record in records if record.best_q == q)
            / sum(record.best_q == q for record in records),
        )
        for q in (-1, 0, 1)
        if any(record.best_q == q for record in records)
    )
    return ChoiceEvaluation(
        tuple(records),
        sum(record.loss for record in records) / len(records),
        sum(record.categorical_loss for record in records) / len(records),
        strata,
    )


def evaluate_predictions(
    boards: Sequence[chess.Board], predictor: Predictor, tablebase: SyzygyProbe
) -> PredictionEvaluation:
    """Evaluate predictions with learner opposite the side to move."""
    if not boards:
        raise ValueError("at least one board is required")
    predictions: list[float] = []
    targets: list[float] = []
    for board in boards:
        learner = not board.turn
        target = -evaluate_reference(board, tablebase).value
        values = predictor([board.copy(stack=True)], learner)
        if len(values) != 1:
            raise ValueError("predictor must return one value per board")
        value = values[0]
        if (
            not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not -1 <= value <= 1
        ):
            raise ValueError("predictor values must be finite and in [-1, 1]")
        predictions.append(float(value))
        targets.append(float(target))
    mse = sum((p - t) ** 2 for p, t in zip(predictions, targets, strict=True)) / len(
        boards
    )
    return PredictionEvaluation(len(boards), mse, tuple(predictions), tuple(targets))


def play_fixed_game(
    board: chess.Board,
    learner: chess.Color,
    predictor: Predictor,
    tablebase: SyzygyProbe,
    rng_exploration: random.Random,
    rng_opponent: random.Random,
    p: float,
    *,
    deadline_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[GameEvaluation], None] | None = None,
) -> GameEvaluation:
    """Play one history-preserving game; errors return incremental audit data.

    Neural counters cover completed selections, not work inside failed calls.
    Progress callback failures propagate to the caller, which owns persistence.
    """
    if learner not in chess.COLORS or not 0 <= p <= 1 or not math.isfinite(p):
        raise ValueError("invalid learner color or p")
    start_fen = board.fen()
    moves: list[str] = []
    keys = {canonical_position(board)}
    decisions = calls = forwards = ref_errors = reference_failures = neural_work = 0
    reference_evaluated = 0
    choice_records: list[ChoiceRecord] = []
    reward = terminal_reward(board, learner)
    truncated = False
    reason = failure = None

    def snapshot() -> GameEvaluation:
        return GameEvaluation(
            start_fen,
            learner,
            float(p),
            reward,
            truncated,
            reason,
            failure,
            len(moves),
            tuple(moves),
            decisions,
            reference_evaluated,
            calls,
            forwards,
            ref_errors,
            reference_failures,
            neural_work,
            tuple(sorted(keys)),
            tuple(choice_records),
        )

    while reward is None:
        try:
            if deadline_check is not None and deadline_check():
                truncated, reason = True, "deadline"
                break
            if len(moves) >= MAX_GAME_PLIES:
                truncated, reason = True, "ply_cap"
                break
            if board.turn == learner:
                decision = select_learner_move(
                    board, learner, predictor, rng_exploration, 0.0
                )
                decisions += 1
                calls += decision.predictor_calls
                forwards += decision.forward_evaluations
                neural_work += decision.forward_evaluations
                move = decision.action
                try:
                    action_values = {
                        candidate: -evaluate_reference(
                            child_board(board, candidate), tablebase
                        ).value
                        for candidate in board.legal_moves
                    }
                except Exception:
                    reference_failures += 1
                    raise
                best_q = max(action_values.values())
                selected_q = action_values[move]
                reference_evaluated += 1
                ref_errors += int(selected_q < best_q)
                choice_records.append(
                    ChoiceRecord(
                        canonical_position(board),
                        learner,
                        move.uci(),
                        selected_q,
                        best_q,
                        selected_q < best_q,
                        (best_q - selected_q) / 2.0,
                    )
                )
            else:
                try:
                    decision2 = choose_action(board, tablebase, rng_opponent, p)
                except Exception:
                    reference_failures += 1
                    raise
                move = decision2.action
            board = child_board(board, move)
            moves.append(move.uci())
            keys.add(canonical_position(board))
            reward = terminal_reward(board, learner)
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
            break
        finally:
            if progress_callback is not None:
                progress_callback(snapshot())
    result = snapshot()
    if progress_callback is not None:
        progress_callback(result)
    return result
