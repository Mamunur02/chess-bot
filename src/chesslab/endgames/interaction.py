"""History-aware simulator for learner/opponent endgame interaction."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import chess

from chesslab.endgames.identity import canonical_position
from chesslab.endgames.opponent import OpponentDecision, choose_action
from chesslab.endgames.reference import SyzygyProbe
from chesslab.endgames.replay import ReplayTransition
from chesslab.endgames.rules import child_board, terminal_reward
from chesslab.endgames.targets import Predictor

MAX_GAME_PLIES = 400


@dataclass(frozen=True, slots=True)
class LearnerDecision:
    """Selected move and predictor work used for that decision."""

    action: chess.Move
    forward_evaluations: int
    predictor_calls: int


@dataclass(frozen=True, slots=True)
class EpisodeRecord:
    """Outcome or explicit truncation record for one started episode."""

    start_fen: str
    learner: chess.Color
    reward: float | None
    truncated: bool
    truncation_reason: str | None
    plies: int
    learner_decisions: int
    recorded_transitions: int


@dataclass(frozen=True, slots=True)
class InteractionResult:
    """Aggregate simulator accounting; truncated episodes have no reward."""

    decisions: int
    transitions: int
    unrecorded_decisions: int
    predictor_calls: int
    forward_evaluations: int
    opponent_opportunities: int
    opponent_worsenings: int
    opponent_category_loss: int
    learner_wins: int
    learner_draws: int
    learner_losses: int
    truncated_episodes: int
    episodes: tuple[EpisodeRecord, ...]
    encountered_keys: tuple[str, ...]


def _validate_probability(value: float, name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise ValueError(f"{name} must be finite and in [0, 1]")


def _checked_predictions(
    boards: Sequence[chess.Board], learner: chess.Color, predictor: Predictor
) -> tuple[float, ...]:
    values = predictor([board.copy(stack=True) for board in boards], learner)
    if len(values) != len(boards):
        raise ValueError("predictor returned a different number of values than boards")
    checked: list[float] = []
    for value in values:
        if (
            not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not -1.0 <= value <= 1.0
        ):
            raise ValueError("predictor values must be finite numbers in [-1, 1]")
        checked.append(float(value))
    return tuple(checked)


def select_learner_move(
    board: chess.Board,
    learner: chess.Color,
    predictor: Predictor,
    rng: random.Random,
    epsilon: float,
) -> LearnerDecision:
    """Select uniformly with epsilon, otherwise maximize afterstate utility."""

    _validate_probability(epsilon, "epsilon")
    if board.outcome(claim_draw=True) is not None:
        raise ValueError("cannot choose an action on a terminal board")
    if learner not in chess.COLORS or board.turn != learner:
        raise ValueError("learner must be the side to move")
    moves = tuple(board.legal_moves)
    if not moves:
        raise ValueError("cannot choose an action without legal moves")
    if epsilon > 0 and (epsilon == 1 or rng.random() < epsilon):
        return LearnerDecision(rng.choice(moves), 0, 0)

    candidates: list[tuple[chess.Move, float]] = []
    nonterminal_boards: list[chess.Board] = []
    nonterminal_moves: list[chess.Move] = []
    for move in moves:
        afterstate = child_board(board, move)
        reward = terminal_reward(afterstate, learner)
        if reward is not None:
            candidates.append((move, reward))
        else:
            nonterminal_moves.append(move)
            nonterminal_boards.append(afterstate)

    values = _checked_predictions(nonterminal_boards, learner, predictor)
    candidates.extend(zip(nonterminal_moves, values, strict=True))
    best_value = max(value for _, value in candidates)
    best_move = min(
        (move for move, value in candidates if value == best_value),
        key=lambda move: move.uci(),
    )
    return LearnerDecision(
        best_move,
        len(nonterminal_boards),
        int(bool(nonterminal_boards)),
    )


def _validated_starts(start_fens: Sequence[str]) -> tuple[chess.Board, ...]:
    if not start_fens:
        raise ValueError("at least one start FEN is required")
    boards: list[chess.Board] = []
    for fen in start_fens:
        try:
            board = chess.Board(fen)
        except ValueError as exc:
            raise ValueError(f"invalid start FEN: {fen}") from exc
        if (
            not board.is_valid()
            or board.chess960
            or board.halfmove_clock != 0
            or board.fullmove_number != 1
            or board.move_stack
            or board.outcome(claim_draw=True) is not None
        ):
            raise ValueError(
                "starts must be valid, live, historyless boards at zero clocks"
            )
        canonical_position(board)
        boards.append(board)
    return tuple(boards)


def run_interaction(
    start_fens: Sequence[str],
    decision_budget: int,
    predictor: Predictor,
    tablebase: SyzygyProbe,
    rng_starts: random.Random,
    rng_exploration: random.Random,
    rng_opponent: random.Random,
    initial_learner_color: chess.Color,
    epsilon: float,
    p: float,
    transition_callback: Callable[[ReplayTransition], None] | None = None,
) -> InteractionResult:
    """Run complete games until exactly ``decision_budget`` learner actions.

    Start positions are sampled with replacement. Episode learner colours
    alternate from ``initial_learner_color``. The last nonterminal learner
    afterstate receives its actual opponent reply even after the decision
    budget is consumed; no subsequent learner action is taken.
    """

    if (
        not isinstance(decision_budget, int)
        or isinstance(decision_budget, bool)
        or decision_budget <= 0
    ):
        raise ValueError("decision_budget must be a positive integer")
    _validate_probability(epsilon, "epsilon")
    _validate_probability(p, "p")
    if initial_learner_color not in chess.COLORS:
        raise ValueError("initial_learner_color must be chess.WHITE or chess.BLACK")
    starts = _validated_starts(start_fens)

    episodes: list[EpisodeRecord] = []
    encountered: set[str] = set()
    decisions = transitions = unrecorded = 0
    predictor_calls = forward_evaluations = 0
    opportunities = worsenings = category_loss = 0
    episode_index = 0

    while decisions < decision_budget:
        start_board = rng_starts.choice(starts).copy(stack=True)
        learner = (
            initial_learner_color
            if episode_index % 2 == 0
            else not initial_learner_color
        )
        episode_index += 1
        start_fen = start_board.fen()
        board = start_board
        plies = episode_decisions = episode_transitions = 0
        encountered.add(canonical_position(board))
        reward: float | None = None
        truncated = False
        truncation_reason: str | None = None

        while True:
            reward = terminal_reward(board, learner)
            if reward is not None:
                break
            if plies >= MAX_GAME_PLIES:
                truncated = True
                truncation_reason = "ply_cap"
                reward = None
                break

            if board.turn == learner:
                selected = select_learner_move(
                    board, learner, predictor, rng_exploration, epsilon
                )
                decisions += 1
                episode_decisions += 1
                predictor_calls += selected.predictor_calls
                forward_evaluations += selected.forward_evaluations
                afterstate = child_board(board, selected.action)
                plies += 1
                encountered.add(canonical_position(afterstate))

                afterstate_reward = terminal_reward(afterstate, learner)
                if afterstate_reward is not None:
                    transition = ReplayTransition(
                        afterstate.copy(stack=True), learner, None
                    )
                    if transition_callback is not None:
                        transition_callback(transition)
                    transitions += 1
                    episode_transitions += 1
                    reward = afterstate_reward
                    break
                if plies >= MAX_GAME_PLIES:
                    unrecorded += 1
                    truncated = True
                    truncation_reason = "ply_cap"
                    reward = None
                    break

                opponent: OpponentDecision = choose_action(
                    afterstate, tablebase, rng_opponent, p
                )
                opportunities += int(opponent.opportunity)
                worsenings += int(opponent.realized_worsening)
                category_loss += opponent.category_loss
                reply_board = child_board(afterstate, opponent.action)
                plies += 1
                encountered.add(canonical_position(reply_board))
                transition = ReplayTransition(
                    afterstate.copy(stack=True), learner, opponent.action
                )
                if transition_callback is not None:
                    transition_callback(transition)
                transitions += 1
                episode_transitions += 1
                board = reply_board
                reward = terminal_reward(board, learner)
                if reward is not None:
                    break
                if plies >= MAX_GAME_PLIES:
                    truncated = True
                    truncation_reason = "ply_cap"
                    reward = None
                    break
                if decisions == decision_budget:
                    truncated = True
                    truncation_reason = "decision_budget"
                    reward = None
                    break
            else:
                opponent = choose_action(board, tablebase, rng_opponent, p)
                opportunities += int(opponent.opportunity)
                worsenings += int(opponent.realized_worsening)
                category_loss += opponent.category_loss
                board = child_board(board, opponent.action)
                plies += 1
                encountered.add(canonical_position(board))

        episodes.append(
            EpisodeRecord(
                start_fen=start_fen,
                learner=learner,
                reward=reward,
                truncated=truncated,
                truncation_reason=truncation_reason,
                plies=plies,
                learner_decisions=episode_decisions,
                recorded_transitions=episode_transitions,
            )
        )

    return InteractionResult(
        decisions=decisions,
        transitions=transitions,
        unrecorded_decisions=unrecorded,
        predictor_calls=predictor_calls,
        forward_evaluations=forward_evaluations,
        opponent_opportunities=opportunities,
        opponent_worsenings=worsenings,
        opponent_category_loss=category_loss,
        learner_wins=sum(episode.reward == 1.0 for episode in episodes),
        learner_draws=sum(episode.reward == 0.0 for episode in episodes),
        learner_losses=sum(episode.reward == -1.0 for episode in episodes),
        truncated_episodes=sum(episode.truncated for episode in episodes),
        episodes=tuple(episodes),
        encountered_keys=tuple(sorted(encountered)),
    )
