import pytest
from game.state import GameState
from core.piece import Piece, PieceType


@pytest.fixture
def fresh_state():
    return GameState()


def test_black_checkmate(fresh_state):  # Adapted fool's mate
    """Test checkmate by black ends game with correct result"""
    state = fresh_state

    # White pawn to f3
    assert state.make_move((6, 5), (5, 5))
    # Black pawn to e6 (opens diagonal for queen and bishop)
    assert state.make_move((1, 4), (2, 4))
    # White pawn to g4
    assert state.make_move((6, 6), (4, 6))
    # Black bishop to d6
    assert state.make_move((0, 5), (2, 3))
    # White pawn to h4
    assert state.make_move((5, 7), (4, 7))
    # Black queen to h4
    assert state.make_move((0, 3), (4, 7))
    # White knight to g3 (only move to block the check)
    assert state.make_move((7, 6), (5, 6))
    # Black queen to g3 (checkmate)
    assert state.make_move((4, 7), (5, 6))

    assert state.is_white_turn
    assert state.game_over
    assert state.game_result == "black_wins"


def test_threefold_repetition(fresh_state):
    """Test that threefold repetition ends game with draw"""
    state = fresh_state

    for _ in range(3):
        assert state.is_white_turn
        assert not state.game_over

        # White knight to g3
        assert state.make_move((7, 6), (5, 6))
        # Black knight to g6
        assert state.make_move((0, 6), (2, 6))
        # White knight back to g1
        assert state.make_move((5, 6), (7, 6))
        # Black knight back to g8
        assert state.make_move((2, 6), (0, 6))

    assert state.game_result == "draw"
    assert state.game_over


def test_bishop_cannot_capture_queen():
    """Test bishops can't capture queens"""
    state = GameState()
    board = state.board
    # Place white bishop and black queen diagonally
    board.board[3][3] = Piece(PieceType.BISHOP, True)
    board.board[4][4] = Piece(PieceType.QUEEN, False)

    moves = state.get_legal_moves((3, 3))
    assert (4, 4) not in moves  # Bishop shouldn't be able to capture queen


def test_stalemate_switches_turn(fresh_state):
    """Test stalemate switches turn instead of ending game"""
    state = fresh_state
    board = state.board
    
    # Clear board and set up stalemate position
    for row in range(8):
        for col in range(8):
            board.board[row][col] = None
    
    # Black king in corner
    board.board[0][0] = Piece(PieceType.KING, False)
    # White pieces surrounding but not attacking
    board.board[2][0] = Piece(PieceType.KING, True)
    board.board[1][2] = Piece(PieceType.QUEEN, True)
    
    # White makes a move that doesn't resolve the stalemate
    assert state.make_move((2, 0), (2, 1))  # White king moves right
    
    # Should switch turn to black, then back to white due to stalemate
    assert state.is_white_turn
    assert not state.game_over
    assert state.game_result is None
