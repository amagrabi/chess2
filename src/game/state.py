from collections import defaultdict
from typing import Tuple, Optional, Dict, Set
from core.board import ChessBoard
from core.piece import Piece, PieceType
import logging


class GameState:
    def __init__(self):
        self.board = ChessBoard()
        self.selected_piece: Optional[Tuple[int, int]] = None
        self.possible_moves: Set[Tuple[int, int]] = set()
        self.is_white_turn = True
        self.game_over = False
        self.game_result: Optional[str] = None
        self.last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
        self.position_history: Dict[str, int] = defaultdict(int)
        self.dragging = False
        self.drag_start: Optional[Tuple[int, int]] = None

    def make_move(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        piece = self.board.get_piece(start)
        if not piece:
            logging.warning(f"Attempted to move a non-existent piece at {start}")
            return False

        if end not in self.get_legal_moves(start):
            logging.warning(f"Illegal move attempted from {start} to {end}")
            return False

        logging.debug(f"Making move from {start} to {end}")
        self._handle_special_moves(start, end, piece)
        self.last_move = (start, end)
        self._update_game_status(piece)
        self.is_white_turn = not self.is_white_turn
        return True

    def _handle_special_moves(
        self, start: Tuple[int, int], end: Tuple[int, int], piece: Piece
    ):
        # Spy conversion
        if piece.type == PieceType.SPY:
            target = self.board.get_piece(end)
            if target and target.is_white != piece.is_white:
                logging.info(f"Spy converted piece at {end}")
                target.is_white = piece.is_white
                self.board.board[start[0]][start[1]] = None
                return

        # Regular move
        self.board.move_piece(start, end)

        # Castling
        if piece.type == PieceType.KING and abs(end[1] - start[1]) == 2:
            row = start[0]
            if end[1] > start[1]:  # Kingside
                logging.info(f"Kingside castling from {start} to {end}")
                self.board.move_piece((row, 7), (row, end[1] - 1))
            else:  # Queenside
                logging.info(f"Queenside castling from {start} to {end}")
                self.board.move_piece((row, 0), (row, end[1] + 1))

        # Pawn promotion
        if piece.type == PieceType.PAWN and end[0] in [0, 7]:
            logging.info(f"Pawn promoted to queen at {end}")
            self.board.board[end[0]][end[1]] = Piece(PieceType.QUEEN, piece.is_white)

    def _update_game_status(self, moved_piece: Piece):
        # Check checkmate
        opponent_color = not moved_piece.is_white
        if not self.board.has_legal_moves(opponent_color):
            if self.board.is_in_check(opponent_color):
                logging.info(
                    f"{'White' if moved_piece.is_white else 'Black'} wins by checkmate"
                )
                self.game_over = True
                self.game_result = (
                    "white_wins" if moved_piece.is_white else "black_wins"
                )
            else:
                logging.info("Stalemate. Game is a draw")
                self.game_over = True
                self.game_result = "draw"

        # Threefold repetition
        new_position = self._get_position_string()
        self.position_history[new_position] += 1
        if self.position_history[new_position] >= 3 and not self.game_over:
            logging.info("Threefold repetition. Game is a draw")
            self.game_over = True
            self.game_result = "draw"

    def get_legal_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        piece = self.board.get_piece(pos)
        if not piece or piece.is_white != self.is_white_turn:
            return set()

        legal_moves = set()
        potential_moves = self.board.get_moves(pos)

        for move in potential_moves:
            # Simulate move
            original_piece = self.board.board[move[0]][move[1]]
            self.board.board[move[0]][move[1]] = piece
            self.board.board[pos[0]][pos[1]] = None

            if not self.board.is_in_check(piece.is_white):
                legal_moves.add(move)

            # Restore board
            self.board.board[pos[0]][pos[1]] = piece
            self.board.board[move[0]][move[1]] = original_piece

        return legal_moves

    def _get_position_string(self) -> str:
        position = []
        for row in range(8):
            for col in range(8):
                piece = self.board.get_piece((row, col))
                if piece:
                    position.append(f"{row},{col},{piece.type.name},{piece.is_white}")
        return ";".join(sorted(position))

    def reset(self):
        self.__init__()
