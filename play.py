import pygame
import random
from sys import exit
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
from collections import defaultdict

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 900, 800  # Increased width for the extra column
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess 2")
clock = pygame.time.Clock()

# Colors
DARK_BROWN = (181, 136, 99)
HIGHLIGHT_COLOR = (169, 169, 169)
LAST_MOVE_COLOR = (128, 128, 128)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LIGHT_SQUARE_WHITE = (240, 217, 181)


class PieceType(Enum):
    PAWN = auto()
    KNIGHT = auto()
    BISHOP = auto()
    ROOK = auto()
    QUEEN = auto()
    KING = auto()
    SPY = auto()


@dataclass
class Piece:
    type: PieceType
    is_white: bool
    has_moved: bool = False

    @property
    def symbol(self) -> str:
        symbols = {
            (PieceType.PAWN, True): "♙",
            (PieceType.KNIGHT, True): "♘",
            (PieceType.BISHOP, True): "♗",
            (PieceType.ROOK, True): "♖",
            (PieceType.QUEEN, True): "♕",
            (PieceType.KING, True): "♔",
            (PieceType.SPY, True): "⌖",
            (PieceType.PAWN, False): "♟",
            (PieceType.KNIGHT, False): "♞",
            (PieceType.BISHOP, False): "♝",
            (PieceType.ROOK, False): "♜",
            (PieceType.QUEEN, False): "♛",
            (PieceType.KING, False): "♚",
            (PieceType.SPY, False): "⌖",
        }
        return symbols[(self.type, self.is_white)]


class ChessBoard:
    def __init__(self):
        self.board = [[None for _ in range(9)] for _ in range(8)]
        self._initialize_board()

    def _initialize_board(self):
        # Initialize pawns
        for col in range(9):
            self.board[1][col] = Piece(PieceType.PAWN, False)
            self.board[6][col] = Piece(PieceType.PAWN, True)

        # Initialize back rows
        back_row = [
            PieceType.ROOK,
            PieceType.KNIGHT,
            PieceType.BISHOP,
            PieceType.QUEEN,
            PieceType.KING,
            PieceType.SPY,
            PieceType.BISHOP,
            PieceType.KNIGHT,
            PieceType.ROOK,
        ]

        for col, piece_type in enumerate(back_row):
            self.board[0][col] = Piece(piece_type, False)
            self.board[7][col] = Piece(piece_type, True)

    def get_piece(self, pos: Tuple[int, int]) -> Optional[Piece]:
        row, col = pos
        if 0 <= row < 8 and 0 <= col < 9:
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
            return set()  # Return empty set instead of None

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

        directions = [
            (0, 1),
            (1, 1),
            (1, 0),
            (1, -1),
            (0, -1),
            (-1, -1),
            (-1, 0),
            (-1, 1),
        ]
        forward = -1 if piece.is_white else 1

        for dr, dc in directions:
            # Skip backward movement
            if (piece.is_white and dr == 1) or (not piece.is_white and dr == -1):
                continue

            new_row, new_col = row + dr, col + dc
            if self._is_valid_position((new_row, new_col)):
                target = self.get_piece((new_row, new_col))
                # Can move to empty squares or capture enemy pieces
                if not target or target.is_white != piece.is_white:
                    moves.add((new_row, new_col))

        # Initial two-square forward move
        if (piece.is_white and row == 6) or (not piece.is_white and row == 1):
            two_forward = row + 2 * forward
            if not self.get_piece((row + forward, col)) and not self.get_piece(
                (two_forward, col)
            ):
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
        return self._get_bishop_moves(pos).union(self._get_rook_moves(pos))

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
            for c in range(9):
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
        return 0 <= row < 8 and 0 <= col < 9

    def is_in_check(self, is_white: bool) -> bool:
        # Find king
        king_pos = None
        for r in range(8):
            for c in range(9):
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
            for c in range(9):
                piece = self.get_piece((r, c))
                if piece and piece.is_white != is_white:
                    if king_pos in self.get_moves((r, c)):
                        return True
        return False

    def has_legal_moves(self, is_white: bool) -> bool:
        for r in range(8):
            for c in range(9):
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


class ChessGame:
    def __init__(self):
        self.board = ChessBoard()
        self.selected_piece = None
        self.possible_moves = set()
        self.is_white_turn = True
        self.game_over = False
        self.game_result = None  # Can be "white_wins", "black_wins", or "draw"
        self.dragging = False
        self.last_move = None
        self.computer_thinking = False
        self.position_history = defaultdict(int)  # Track position repetitions

        try:
            self.font = pygame.font.Font("assets/FreeSerif.ttf", 64)
        except FileNotFoundError:
            print("Chess font not found! Using default font.")
            self.font = pygame.font.Font(None, 64)

    def _make_move(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        piece = self.board.get_piece(start)
        if not piece:
            return False

        # Store current position before move
        current_position = self._get_position_string()
        self.position_history[current_position] += 1

        # Handle spy conversion
        if piece.type == PieceType.SPY:
            target = self.board.get_piece(end)
            if target and target.is_white != piece.is_white:
                self.board.move_piece(start, end, convert=True)
            else:
                self.board.move_piece(start, end)
        else:
            self.board.move_piece(start, end)

        # Handle castling
        if piece.type == PieceType.KING and abs(end[1] - start[1]) == 2:
            row = start[0]
            if end[1] > start[1]:  # Kingside
                self.board.move_piece((row, 8), (row, end[1] - 1))
            else:  # Queenside
                self.board.move_piece((row, 0), (row, end[1] + 1))

        # Handle pawn promotion
        if piece.type == PieceType.PAWN and end[0] in [0, 7]:
            promoted_piece = Piece(PieceType.QUEEN, piece.is_white)
            self.board.board[end[0]][end[1]] = promoted_piece

        self.last_move = (start, end)
        self.selected_piece = None
        self.possible_moves = set()
        self.is_white_turn = not self.is_white_turn

        # Check for threefold repetition
        new_position = self._get_position_string()
        self.position_history[new_position] += 1

        if self.position_history[new_position] >= 3:
            self.game_over = True
            self.game_result = "draw"
            return True

        # Check for game over
        if not self.board.has_legal_moves(not piece.is_white):
            if self.board.is_in_check(not piece.is_white):
                self.game_over = True
                self.game_result = "white_wins" if piece.is_white else "black_wins"
            else:
                # No legal moves but not in check - skip the turn as per rules
                self.is_white_turn = not self.is_white_turn

        return True

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        square = self._pos_to_square(pos)
        if not self._is_valid_square(square):
            return False

        piece = self.board.get_piece(square)

        if self.selected_piece:
            # Trying to move
            if square in self.possible_moves:
                return self._make_move(self.selected_piece, square)
            # Selecting a different piece
            elif piece and piece.is_white == self.is_white_turn:
                self.selected_piece = square
                self.possible_moves = self._get_legal_moves(square)
            else:
                self.selected_piece = None
                self.possible_moves = set()
        elif piece and piece.is_white == self.is_white_turn:
            self.selected_piece = square
            self.possible_moves = self._get_legal_moves(square)

        return False

    def _get_legal_moves(self, pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        piece = self.board.get_piece(pos)
        if not piece:
            return set()

        legal_moves = set()
        potential_moves = self.board.get_moves(pos)

        for move in potential_moves:
            # Try move
            temp_piece = self.board.board[move[0]][move[1]]
            self.board.board[move[0]][move[1]] = piece
            self.board.board[pos[0]][pos[1]] = None

            if not self.board.is_in_check(piece.is_white):
                legal_moves.add(move)

            # Restore board
            self.board.board[pos[0]][pos[1]] = piece
            self.board.board[move[0]][move[1]] = temp_piece

        return legal_moves

    def computer_move(self):
        if self.game_over or self.is_white_turn:
            return

        legal_moves = []
        for r in range(8):
            for c in range(9):
                piece = self.board.get_piece((r, c))
                if piece and not piece.is_white:
                    moves = self._get_legal_moves((r, c))
                    legal_moves.extend(((r, c), move) for move in moves)

        if legal_moves:
            start, end = random.choice(legal_moves)
            self._make_move(start, end)

    def draw(self):
        self._draw_board()
        self._draw_highlights()
        self._draw_pieces()
        if self.game_over:
            self._draw_game_over()

    def _draw_board(self):
        square_size = WIDTH // 9
        for row in range(8):
            for col in range(9):
                color = LIGHT_SQUARE_WHITE if (row + col) % 2 == 0 else DARK_BROWN
                pygame.draw.rect(
                    screen,
                    color,
                    (col * square_size, row * square_size, square_size, square_size),
                )

    def _draw_highlights(self):
        square_size = WIDTH // 9
        if self.selected_piece:
            # Highlight selected square
            surface = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
            surface.fill((*HIGHLIGHT_COLOR, 100))
            screen.blit(
                surface,
                (
                    self.selected_piece[1] * square_size,
                    self.selected_piece[0] * square_size,
                ),
            )

            # Highlight possible moves
            for move in self.possible_moves:
                center = (
                    move[1] * square_size + square_size // 2,
                    move[0] * square_size + square_size // 2,
                )
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, center, square_size // 6)

        # Highlight last move
        if self.last_move:
            for pos in self.last_move:
                surface = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
                surface.fill((*LAST_MOVE_COLOR, 100))
                screen.blit(surface, (pos[1] * square_size, pos[0] * square_size))

    def _draw_pieces(self):
        square_size = WIDTH // 9
        for row in range(8):
            for col in range(9):
                piece = self.board.get_piece((row, col))
                if piece and (not self.dragging or (row, col) != self.selected_piece):
                    text_color = WHITE if piece.is_white else BLACK
                    text_surface = self.font.render(piece.symbol, True, text_color)
                    text_rect = text_surface.get_rect(
                        center=(
                            col * square_size + square_size // 2,
                            row * square_size + square_size // 2,
                        )
                    )

                    # Draw shadow
                    shadow_surface = self.font.render(piece.symbol, True, (80, 80, 80))
                    screen.blit(shadow_surface, text_rect.move(1.5, 1.5))
                    screen.blit(text_surface, text_rect)

        # Draw dragged piece
        if self.selected_piece and self.dragging:
            piece = self.board.get_piece(self.selected_piece)
            if piece:
                text_color = WHITE if piece.is_white else BLACK
                text_surface = self.font.render(piece.symbol, True, text_color)
                mouse_pos = pygame.mouse.get_pos()
                text_rect = text_surface.get_rect(center=mouse_pos)
                screen.blit(text_surface, text_rect)

    def _draw_game_over(self):
        text_font = pygame.font.Font(None, 74)
        if self.is_white_turn:
            text = text_font.render("Black wins!", True, BLACK)
        else:
            text = text_font.render("White wins!", True, BLACK)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)

        play_again_font = pygame.font.Font(None, 36)
        play_again_text = play_again_font.render("Click to play again", True, BLACK)
        play_again_rect = play_again_text.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 + 100)
        )
        screen.blit(play_again_text, play_again_rect)

    def _pos_to_square(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        x, y = pos
        square_size = WIDTH // 9
        return (y // square_size, x // square_size)

    def _is_valid_square(self, square: Tuple[int, int]) -> bool:
        row, col = square
        return 0 <= row < 8 and 0 <= col < 9

    def _get_position_string(self) -> str:
        """Convert current board position to a string for repetition checking."""
        position = []
        for row in range(8):
            for col in range(9):
                piece = self.board.get_piece((row, col))
                if piece:
                    position.append(f"{row},{col},{piece.type.name},{piece.is_white}")
        return ";".join(sorted(position))

    def _draw_game_over(self):
        text_font = pygame.font.Font(None, 74)

        if self.game_result == "draw":
            text = text_font.render("Draw!", True, BLACK)
        elif self.game_result == "white_wins":
            text = text_font.render("Checkmate, you win!", True, BLACK)
        else:  # black_wins
            text = text_font.render("Checkmate, you lose!", True, BLACK)

        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)

        play_again_font = pygame.font.Font(None, 36)
        play_again_text = play_again_font.render("Press ESC to play again", True, BLACK)
        play_again_rect = play_again_text.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 + 100)
        )
        screen.blit(play_again_text, play_again_rect)

    def reset(self):
        self.__init__()


def main():
    game = ChessGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game.reset()
                continue

            if not game.game_over and not game.computer_thinking:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if game.handle_click(pygame.mouse.get_pos()):
                        game.computer_thinking = True
                        pygame.time.set_timer(pygame.USEREVENT, 1000)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if game.dragging:
                        if game.selected_piece:
                            end_square = game._pos_to_square(pygame.mouse.get_pos())
                            if (
                                game._is_valid_square(end_square)
                                and end_square in game.possible_moves
                            ):
                                if game._make_move(game.selected_piece, end_square):
                                    game.computer_thinking = True
                                    pygame.time.set_timer(pygame.USEREVENT, 1000)
                        game.dragging = False

            if event.type == pygame.USEREVENT and game.computer_thinking:
                game.computer_move()
                pygame.time.set_timer(pygame.USEREVENT, 0)
                game.computer_thinking = False

        screen.fill(WHITE)
        game.draw()
        pygame.display.update()
        clock.tick(60)


if __name__ == "__main__":
    main()
