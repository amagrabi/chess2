import pytest
from game.state import GameState
from core.piece import Piece, PieceType


@pytest.fixture
def fresh_state():
    return GameState()


def test_black_checkmate(fresh_state):  # Modified fools mate
    """Test checkmate by black ends game with correct result"""
    state = fresh_state
    board = state.board

    # White pawn to f3
    assert state.make_move((6, 5), (5, 5))
    # Black pawn to e6 (opens diagonal for queen)
    assert state.make_move((1, 4), (2, 4))
    # White pawn to g4
    assert state.make_move((6, 6), (4, 6))
    # Black pawn to e5 (waste a move)
    assert state.make_move((2, 4), (3, 4))
    # White pawn to h4
    assert state.make_move((5, 7), (4, 7))
    # Black queen to h4 (checkmate)
    assert state.make_move((0, 3), (4, 7))

    assert state.is_white_turn, "Should be white's turn"
    assert state.game_over, "Game should be over"
    assert state.game_result == "black_wins"


def test_stalemate_continues(fresh_state):
    """Test stalemate doesn't result in draw (per README rules)"""
    board = fresh_state.board
    # Clear all pieces
    board.board = [[None for _ in range(8)] for _ in range(8)]
    # Set up stalemate position
    board.board[0][0] = Piece(PieceType.KING, True)
    board.board[2][1] = Piece(PieceType.QUEEN, False)
    board.board[1][2] = Piece(PieceType.ROOK, False)

    fresh_state.is_white_turn = True
    assert not fresh_state.board.has_legal_moves(True)
    assert not fresh_state.game_over


def test_threefold_repetition(fresh_state):
    """Test threefold repetition results in draw"""
    # Clear pawns first
    fresh_state.board.board[6] = [None] * 8  # Clear white pawns
    fresh_state.board.board[1] = [None] * 8  # Clear black pawns

    # Perform 3 complete cycles
    for _ in range(3):
        # White knight moves
        assert fresh_state.make_move((7, 1), (5, 2)), "White knight move failed"
        # Black knight moves
        assert fresh_state.make_move((0, 1), (2, 2)), "Black knight move failed"
        # White knight returns
        assert fresh_state.make_move((5, 2), (7, 1)), "White knight return failed"
        # Black knight returns
        assert fresh_state.make_move((2, 2), (0, 1)), "Black knight return failed"

    assert fresh_state.game_over, "Game should end in draw"
    assert fresh_state.game_result == "draw"


def test_bishop_cannot_capture_queen():
    """Test bishops can't capture queens"""
    state = GameState()
    board = state.board
    # Place white bishop and black queen diagonally
    board.board[3][3] = Piece(PieceType.BISHOP, True)
    board.board[4][4] = Piece(PieceType.QUEEN, False)

    moves = state.get_legal_moves((3, 3))
    assert (4, 4) not in moves  # Bishop shouldn't be able to capture queen
