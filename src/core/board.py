from typing import List, Tuple, Optional, Set
from core.piece import Piece, PieceType

class ChessBoard:
    def __init__(self):
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self._initialize_board()

    def _initialize_board(self):
        # Initialize pawns (with special case for h2/h7)
        for col in range(8):
            if col != 7:  # Skip h2/h7 as those will have spies
                self.board[1][col] = Piece(PieceType.PAWN, False)
                self.board[6][col] = Piece(PieceType.PAWN, True)
        
        # Add the displaced h-pawns one row further
        self.board[2][7] = Piece(PieceType.PAWN, False)  # h3
        self.board[5][7] = Piece(PieceType.PAWN, True)   # h6

        # Initialize back rows
        back_row = [
            PieceType.ROOK,
            PieceType.KNIGHT,
            PieceType.BISHOP,
            PieceType.QUEEN,
            PieceType.KING,
            PieceType.BISHOP,
            PieceType.KNIGHT,
            PieceType.ROOK,
        ]

        for col, piece_type in enumerate(back_row):
            self.board[0][col] = Piece(piece_type, False)
            self.board[7][col] = Piece(piece_type, True)

        # Add spies at h2/h7
        self.board[1][7] = Piece(PieceType.SPY, False)  # h2
        self.board[6][7] = Piece(PieceType.SPY, True)   # h7

    def get_piece(self, pos: Tuple[int, int]) -> Optional[Piece]:
        row, col = pos
        if 0 <= row < 8 and 0 <= col < 8:
            return self.board[row][col]
        return None

    def move_piece(
        self, start: Tuple[int, int], end: Tuple[int, int], convert: bool = False
    ):
        piece = self.board[start[0]][start[1]]
        if piece:
            if convert:
                # For spy conversion
                target_piece = self.board[end[0]][end[1]]
                if target_piece:
                    target_piece.is_white = piece.is_white
            else:
                self.board[end[0]][end[1]] = piece
                self.board[start[0]][start[1]] = None
                piece.has_moved = True

    def get_moves(
        self, pos: Tuple[int, int], check_castling: bool = True
    ) -> Set[Tuple[int, int]]:
        piece = self.get_piece(pos)
        if not piece:
            return set()

        moves = set()

        if piece.type == PieceType.PAWN:
            moves.update(self._get_pawn_moves(pos))
        elif piece.type == PieceType.KNIGHT:
            moves.update(self._get_knight_moves(pos))
        elif piece.type == PieceType.BISHOP:
            moves.update(self._get_bishop_moves(pos))
        elif piece.type == PieceType.ROOK:
            moves.update(self._get_rook_moves(pos))
        elif piece.type == PieceType.QUEEN:
            moves.update(self._get_queen_moves(pos))
        elif piece.type == PieceType.KING:
            moves.update(self._get_king_moves(pos, check_castling))
        elif piece.type == PieceType.SPY:
            moves.update(self._get_spy_moves(pos))

        return moves

    def _get_pawn_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = pos
        piece = self.get_piece(pos)
        if not piece:
            return moves

        # Direction the pawn moves (up for white, down for black)
        forward = -1 if piece.is_white else 1

        # Forward moves and forward captures
        for dc in [-1, 0, 1]:  # Check diagonally left, straight, and diagonally right
            new_row, new_col = row + forward, col + dc
            if self._is_valid_position((new_row, new_col)):
                target = self.get_piece((new_row, new_col))
                # Allow both movement and capture in all forward directions
                if not target or target.is_white != piece.is_white:
                    moves.add((new_row, new_col))
        
        # Initial two-square forward move
        if (piece.is_white and row == 6) or (not piece.is_white and row == 1):
            two_forward = row + 2 * forward
            if not self.get_piece((two_forward, col)):
                moves.add((two_forward, col))

        return moves

    def _get_knight_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = pos
        piece = self.get_piece(pos)
        if not piece:
            return moves

        # L-shaped moves (traditional knight moves)
        l_moves = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]

        # 2-square orthogonal moves (new ability)
        straight_moves = [(-2, 0), (2, 0), (0, -2), (0, 2)]

        all_moves = l_moves + straight_moves

        for dr, dc in all_moves:
            new_row, new_col = row + dr, col + dc
            if self._is_valid_position((new_row, new_col)):
                target = self.get_piece((new_row, new_col))
                if not target or target.is_white != piece.is_white:
                    moves.add((new_row, new_col))

        return moves

    def _get_spy_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = pos
        piece = self.get_piece(pos)
        if not piece:
            return moves

        # L-shaped moves like a knight
        knight_moves = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]

        for dr, dc in knight_moves:
            new_row, new_col = row + dr, col + dc
            if self._is_valid_position((new_row, new_col)):
                target = self.get_piece((new_row, new_col))
                if not target or target.is_white != piece.is_white:
                    moves.add((new_row, new_col))

        return moves

    def _get_jumping_moves(
        self, pos: Tuple[int, int], distance: int
    ) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = pos
        piece = self.get_piece(pos)
        if not piece:
            return moves

        for dr in range(-distance, distance + 1):
            for dc in range(-distance, distance + 1):
                if abs(dr) + abs(dc) == distance:
                    new_row, new_col = row + dr, col + dc
                    if self._is_valid_position((new_row, new_col)):
                        target = self.get_piece((new_row, new_col))
                        if not target or target.is_white != piece.is_white:
                            moves.add((new_row, new_col))

        return moves

    def _get_bishop_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        moves = set()
        piece = self.get_piece(pos)
        if not piece:
            return moves

        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in directions:
            moves.update(self._get_sliding_moves(pos, dr, dc))

        # Remove queen captures for bishops
        moves = {
            move
            for move in moves
            if not (
                self.get_piece(move)
                and self.get_piece(move).type == PieceType.QUEEN
                and self.get_piece(move).is_white != piece.is_white
            )
        }

        return moves

    def _get_rook_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        moves = set()
        if not self.get_piece(pos):
            return moves

        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            moves.update(self._get_sliding_moves(pos, dr, dc))
        return moves

    def _get_queen_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        moves = set()
        piece = self.get_piece(pos)
        if not piece:
            return moves

        # Get diagonal moves (without bishop's queen-capture restriction)
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in directions:
            moves.update(self._get_sliding_moves(pos, dr, dc))

        # Add rook moves
        moves.update(self._get_rook_moves(pos))
        return moves

    def _get_king_moves(
        self, pos: Tuple[int, int], check_castling: bool
    ) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = pos
        piece = self.get_piece(pos)
        if not piece:
            return moves

        # Normal king moves
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_row, new_col = row + dr, col + dc
                if self._is_valid_position((new_row, new_col)):
                    target = self.get_piece((new_row, new_col))
                    if not target or target.is_white != piece.is_white:
                        moves.add((new_row, new_col))

        # Castling
        if check_castling and not piece.has_moved:
            moves.update(self._get_castling_moves(pos))

        return moves

    def _get_castling_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = pos
        piece = self.get_piece(pos)
        if not piece or piece.has_moved:
            return moves

        # Check kingside castling
        if (
            self._can_castle_kingside(piece.is_white)
            and not self._is_square_attacked((row, col + 1), not piece.is_white)
            and not self._is_square_attacked((row, col + 2), not piece.is_white)
        ):
            moves.add((row, col + 2))

        # Check queenside castling
        if (
            self._can_castle_queenside(piece.is_white)
            and not self._is_square_attacked((row, col - 1), not piece.is_white)
            and not self._is_square_attacked((row, col - 2), not piece.is_white)
        ):
            moves.add((row, col - 2))

        return moves

    def _can_castle_kingside(self, is_white: bool) -> bool:
        row = 7 if is_white else 0
        return (
            self.get_piece((row, 7))
            and self.get_piece((row, 7)).type == PieceType.ROOK
            and not self.get_piece((row, 7)).has_moved
            and not self.get_piece((row, 5))
            and not self.get_piece((row, 6))
        )

    def _can_castle_queenside(self, is_white: bool) -> bool:
        row = 7 if is_white else 0
        return (
            self.get_piece((row, 0))
            and self.get_piece((row, 0)).type == PieceType.ROOK
            and not self.get_piece((row, 0)).has_moved
            and not self.get_piece((row, 1))
            and not self.get_piece((row, 2))
            and not self.get_piece((row, 3))
        )

    def _is_square_attacked(self, pos: Tuple[int, int], by_white: bool) -> bool:
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if piece and piece.is_white == by_white:
                    if pos in self.get_moves((r, c), check_castling=False):
                        return True
        return False

    def _get_sliding_moves(
        self, pos: Tuple[int, int], dr: int, dc: int
    ) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = pos
        piece = self.get_piece(pos)
        if not piece:
            return moves

        new_row, new_col = row + dr, col + dc
        while self._is_valid_position((new_row, new_col)):
            target = self.get_piece((new_row, new_col))
            if not target:
                moves.add((new_row, new_col))
            else:
                if target.is_white != piece.is_white:
                    moves.add((new_row, new_col))
                break
            new_row += dr
            new_col += dc

        return moves

    def _is_valid_position(self, pos: Tuple[int, int]) -> bool:
        row, col = pos
        return 0 <= row < 8 and 0 <= col < 8

    def is_in_check(self, is_white: bool) -> bool:
        # Find king
        king_pos = None
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if (
                    piece
                    and piece.type == PieceType.KING
                    and piece.is_white == is_white
                ):
                    king_pos = (r, c)
                    break
            if king_pos:
                break

        if not king_pos:
            return False

        # Check if any enemy piece can capture the king
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if piece and piece.is_white != is_white:
                    if king_pos in self.get_moves((r, c)):
                        return True
        return False

    def has_legal_moves(self, is_white: bool) -> bool:
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if piece and piece.is_white == is_white:
                    possible_moves = self.get_moves((r, c))
                    for move in possible_moves:
                        # Try move and check if it leaves king in check
                        temp_piece = self.board[move[0]][move[1]]
                        self.board[move[0]][move[1]] = piece
                        self.board[r][c] = None

                        in_check = self.is_in_check(is_white)

                        # Restore board
                        self.board[r][c] = piece
                        self.board[move[0]][move[1]] = temp_piece

                        if not in_check:
                            return True
        return False