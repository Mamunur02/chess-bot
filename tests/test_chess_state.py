import chess
import pytest

from chesslab.games import GameState
from chesslab.games.chess import ChessState

CHECKMATE_FEN = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
STALEMATE_FEN = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
INSUFFICIENT_MATERIAL_FEN = "7k/8/8/8/8/8/8/K7 w - - 0 1"
CASTLING_FEN = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
EN_PASSANT_FEN = "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2"
PROMOTION_FEN = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
FIFTY_MOVE_FEN = "7k/8/8/8/8/8/8/KR6 w - - 100 51"
SEVENTY_FIVE_MOVE_FEN = "7k/8/8/8/8/8/8/KR6 w - - 150 76"
CHECK_FEN = "7k/8/8/8/8/8/7r/7K w - - 0 1"


def require_game_state(state: GameState[chess.Move]) -> GameState[chess.Move]:
    """Exercise structural protocol compatibility during test type-checking."""
    return state


def play_uci_moves(state: ChessState, moves: list[str]) -> ChessState:
    for move in moves:
        state = state.apply(chess.Move.from_uci(move))
    return state


def test_initial_position_implements_contract() -> None:
    state = ChessState()

    contract_state = require_game_state(state)

    assert contract_state.current_player == 0
    assert len(contract_state.legal_actions()) == 20
    assert chess.Move.from_uci("e2e4") in contract_state.legal_actions()
    assert not contract_state.is_terminal()


def test_black_maps_to_player_one() -> None:
    state = ChessState().apply(chess.Move.from_uci("e2e4"))

    assert state.current_player == 1


def test_check_status_is_exposed_without_changing_state() -> None:
    checked = ChessState.from_fen(CHECK_FEN)

    assert checked.is_in_check()
    assert not ChessState().is_in_check()


def test_apply_preserves_parent_and_move_history() -> None:
    parent = ChessState()
    parent_fen = parent.to_fen()

    child = parent.apply(chess.Move.from_uci("e2e4"))

    assert parent.to_fen() == parent_fen
    assert child.to_fen() != parent_fen
    assert child.current_player == 1
    child_board = chess.Board(child.to_fen())
    assert child_board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)


def test_illegal_move_fails_clearly() -> None:
    with pytest.raises(ValueError, match="illegal move: e2e5"):
        ChessState().apply(chess.Move.from_uci("e2e5"))


@pytest.mark.parametrize("fen", ["not a FEN", "8/8/8/8/8/8/8/8 w - - 0 1"])
def test_invalid_fen_fails_clearly(fen: str) -> None:
    with pytest.raises(ValueError, match="invalid"):
        ChessState.from_fen(fen)


def test_checkmate_returns_winner_by_stable_player_identity() -> None:
    state = ChessState.from_fen(CHECKMATE_FEN)

    assert state.current_player == 0
    assert state.is_terminal()
    assert state.legal_actions() == ()
    assert state.returns() == (-1.0, 1.0)


@pytest.mark.parametrize("fen", [STALEMATE_FEN, INSUFFICIENT_MATERIAL_FEN])
def test_automatic_draws_return_zero(fen: str) -> None:
    state = ChessState.from_fen(fen)

    assert state.is_terminal()
    assert state.legal_actions() == ()
    assert state.returns() == (0.0, 0.0)


def test_automatic_terminal_state_rejects_otherwise_legal_move() -> None:
    state = ChessState.from_fen(INSUFFICIENT_MATERIAL_FEN)

    with pytest.raises(ValueError, match="illegal move"):
        state.apply(chess.Move.from_uci("a1b2"))


def test_non_terminal_returns_fail_clearly() -> None:
    with pytest.raises(ValueError, match="terminal states"):
        ChessState().returns()


def test_castling_moves_and_piece_placement() -> None:
    state = ChessState.from_fen(CASTLING_FEN)
    kingside = chess.Move.from_uci("e1g1")
    queenside = chess.Move.from_uci("e1c1")

    assert kingside in state.legal_actions()
    assert queenside in state.legal_actions()

    board = chess.Board(state.apply(kingside).to_fen())
    assert board.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
    assert board.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)


def test_en_passant_capture() -> None:
    state = ChessState.from_fen(EN_PASSANT_FEN)
    move = chess.Move.from_uci("e5d6")

    assert move in state.legal_actions()

    board = chess.Board(state.apply(move).to_fen())
    assert board.piece_at(chess.D6) == chess.Piece(chess.PAWN, chess.WHITE)
    assert board.piece_at(chess.D5) is None


def test_capture_classification_includes_en_passant_and_rejects_illegal_moves() -> None:
    state = ChessState.from_fen(EN_PASSANT_FEN)

    assert state.is_capture(chess.Move.from_uci("e5d6"))
    assert not state.is_capture(chess.Move.from_uci("e5e6"))
    with pytest.raises(ValueError, match="illegal move"):
        state.is_capture(chess.Move.from_uci("e5e7"))


def test_promotion_actions_and_piece_placement() -> None:
    state = ChessState.from_fen(PROMOTION_FEN)
    promotions = {
        chess.Move.from_uci("a7a8q"),
        chess.Move.from_uci("a7a8r"),
        chess.Move.from_uci("a7a8b"),
        chess.Move.from_uci("a7a8n"),
    }

    assert promotions <= set(state.legal_actions())

    board = chess.Board(state.apply(chess.Move.from_uci("a7a8q")).to_fen())
    assert board.piece_at(chess.A8) == chess.Piece(chess.QUEEN, chess.WHITE)


def test_claimable_fifty_move_draw_is_not_automatic() -> None:
    state = ChessState.from_fen(FIFTY_MOVE_FEN)

    assert not state.is_terminal()
    with pytest.raises(ValueError, match="terminal states"):
        state.returns()


def test_seventy_five_move_draw_is_automatic() -> None:
    state = ChessState.from_fen(SEVENTY_FIVE_MOVE_FEN)

    assert state.is_terminal()
    assert state.returns() == (0.0, 0.0)


def test_threefold_claim_is_not_automatic_but_fivefold_is() -> None:
    cycle = ["g1f3", "g8f6", "f3g1", "f6g8"]

    threefold = play_uci_moves(ChessState(), cycle * 2)
    fivefold = play_uci_moves(threefold, cycle * 2)

    assert not threefold.is_terminal()
    assert fivefold.is_terminal()
    assert fivefold.returns() == (0.0, 0.0)


def test_fen_does_not_reconstruct_repetition_history() -> None:
    cycle = ["g1f3", "g8f6", "f3g1", "f6g8"]
    fivefold = play_uci_moves(ChessState(), cycle * 4)

    restored = ChessState.from_fen(fivefold.to_fen())

    assert fivefold.is_terminal()
    assert not restored.is_terminal()


def test_transposition_key_is_reproducible_and_includes_history() -> None:
    moves = ["e2e4", "e7e5", "g1f3"]
    first = play_uci_moves(ChessState(), moves)
    repeated = play_uci_moves(ChessState(), moves)
    restored_without_history = ChessState.from_fen(first.to_fen())

    assert first.transposition_key() == repeated.transposition_key()
    assert first.transposition_key() != restored_without_history.transposition_key()


def test_transposed_positions_with_different_histories_have_different_keys() -> None:
    knights_first = play_uci_moves(
        ChessState(),
        ["g1f3", "g8f6", "b1c3", "b8c6"],
    )
    queenside_first = play_uci_moves(
        ChessState(),
        ["b1c3", "b8c6", "g1f3", "g8f6"],
    )

    assert knights_first.to_fen() == queenside_first.to_fen()
    assert knights_first.transposition_key() != queenside_first.transposition_key()


def test_transposition_key_ignores_history_before_irreversible_move() -> None:
    kingside_cycle = play_uci_moves(
        ChessState(),
        ["g1f3", "g8f6", "f3g1", "f6g8", "e2e4"],
    )
    queenside_cycle = play_uci_moves(
        ChessState(),
        ["b1c3", "b8c6", "c3b1", "c6b8", "e2e4"],
    )

    assert kingside_cycle.to_fen() == queenside_cycle.to_fen()
    assert kingside_cycle.transposition_key() == queenside_cycle.transposition_key()
