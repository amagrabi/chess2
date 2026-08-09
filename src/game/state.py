import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from core.board import ChessBoard
from core.piece import Piece, PieceType

PIECE_LETTERS = {
    PieceType.KING: "K",
    PieceType.QUEEN: "Q",
    PieceType.ROOK: "R",
    PieceType.BISHOP: "B",
    PieceType.KNIGHT: "N",
    PieceType.SPY: "S",
    PieceType.PAWN: "",
}

PROMOTION_CHOICES = (
    PieceType.QUEEN,
    PieceType.ROOK,
    PieceType.BISHOP,
    PieceType.KNIGHT,
)


def square_name(pos: Tuple[int, int]) -> str:
    """(row, col) -> algebraic square, e.g. (6, 4) -> 'e2'."""
    row, col = pos
    return f"{'abcdefgh'[col]}{8 - row}"


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
        self.last_capture = False
        self.move_log: List[str] = []
        self._undo_stack: List[dict] = []

    # ------------------------------------------------------------------ moves

    def is_promotion(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Would moving start -> end promote a pawn?"""
        piece = self.board.get_piece(start)
        return (
            piece is not None
            and piece.type == PieceType.PAWN
            and end[0] in (0, 7)
            and end in self.get_legal_moves(start)
        )

    def make_move(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        promotion: PieceType = PieceType.QUEEN,
    ) -> bool:
        piece = self.board.get_piece(start)
        if not piece:
            logging.warning(f"Attempted to move a non-existent piece at {start}")
            return False

        if end not in self.get_legal_moves(start):
            logging.warning(f"Illegal move attempted from {start} to {end}")
            return False

        self._push_undo()

        target_piece = self.board.get_piece(end)
        is_enemy_target = (
            target_piece is not None and target_piece.is_white != piece.is_white
        )
        # A spy converts rather than captures, and dies doing it.
        converted = piece.type == PieceType.SPY and is_enemy_target
        self.last_capture = is_enemy_target and not converted

        piece_type = piece.type
        promoted = piece_type == PieceType.PAWN and end[0] in (0, 7)

        logging.debug(f"Making move from {start} to {end}")
        self.board.apply_move(start, end, promotion)
        self.last_move = (start, end)
        self._update_game_status(piece)
        self.is_white_turn = not self.is_white_turn

        self.move_log.append(
            self._notate(
                piece_type,
                start,
                end,
                captured=self.last_capture,
                converted=converted,
                promotion=promotion if promoted else None,
            )
        )
        return True

    def _notate(
        self,
        piece_type: PieceType,
        start: Tuple[int, int],
        end: Tuple[int, int],
        captured: bool,
        converted: bool,
        promotion: Optional[PieceType],
    ) -> str:
        separator = "~" if converted else ("x" if captured else "-")
        text = (
            f"{PIECE_LETTERS[piece_type]}{square_name(start)}"
            f"{separator}{square_name(end)}"
        )
        if promotion is not None:
            text += f"={PIECE_LETTERS[promotion]}"

        # is_white_turn has already flipped, so it now names the side to move.
        if self.game_over and self.game_result in ("white_wins", "black_wins"):
            text += "#"
        elif self.board.is_in_check(self.is_white_turn):
            text += "+"
        return text

    # ------------------------------------------------------------------- undo

    def _push_undo(self):
        self._undo_stack.append(
            {
                "board": self.board.snapshot(),
                "is_white_turn": self.is_white_turn,
                "game_over": self.game_over,
                "game_result": self.game_result,
                "last_move": self.last_move,
                "last_capture": self.last_capture,
                "position_history": dict(self.position_history),
                "move_count": len(self.move_log),
            }
        )

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def undo(self) -> bool:
        """Take back a single ply."""
        if not self._undo_stack:
            return False

        snap = self._undo_stack.pop()
        self.board.restore(snap["board"])
        self.is_white_turn = snap["is_white_turn"]
        self.game_over = snap["game_over"]
        self.game_result = snap["game_result"]
        self.last_move = snap["last_move"]
        self.last_capture = snap["last_capture"]
        self.position_history = defaultdict(int, snap["position_history"])
        del self.move_log[snap["move_count"] :]

        self.selected_piece = None
        self.possible_moves = set()
        self.dragging = False
        self.drag_start = None
        return True

    # ----------------------------------------------------------------- status

    def _update_game_status(self, moved_piece: Piece):
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
                # Stalemate - continue game without ending
                self.is_white_turn = not self.is_white_turn

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
