import chess

from chesslab.agents import RandomAgent
from chesslab.eval import MatchResult, MatchStatus, run_match
from chesslab.games.chess import ChessState
from chesslab.search import NodeBudget


def run_bounded_chess_match() -> MatchResult:
    return run_match(
        ChessState(),
        (RandomAgent[chess.Move](), RandomAgent[chess.Move]()),
        NodeBudget(1),
        seed=2026,
        max_plies=12,
        encode_action=chess.Move.uci,
    )


def test_seeded_chess_match_is_reproducible_and_legal() -> None:
    first = run_bounded_chess_match()
    repeated = run_bounded_chess_match()

    assert first == repeated
    assert first.status in (MatchStatus.COMPLETED, MatchStatus.INTERRUPTED)

    replayed_state = ChessState()
    for record in first.moves:
        move = chess.Move.from_uci(record.action)
        assert record.player == replayed_state.current_player
        assert move in replayed_state.legal_actions()
        replayed_state = replayed_state.apply(move)

    if first.status is MatchStatus.INTERRUPTED:
        assert first.terminal_returns is None
