import pygame
from typing import Tuple, Set
from core.piece import Piece
from game.state import GameState
from utils import _resource_path


class GUIRenderer:
    COLORS = {
        "background": (255, 255, 255),
        "dark_square": (181, 136, 99),
        "light_square": (230, 207, 171),
        "legal_moves": (100, 150, 100),
        "last_move": (130, 170, 130),
        "white_piece": (255, 255, 255),
        "black_piece": (0, 0, 0),
        "text": (0, 0, 0),
    }

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.square_size = screen_width // 8

        try:
            self.font = pygame.font.Font(_resource_path("assets/FreeSerif.ttf"), 64)
        except FileNotFoundError:
            print("Chess font not found! Using default font.")
            self.font = pygame.font.Font(None, 64)

        self.game_over_font = pygame.font.Font(None, 74)
        self.info_font = pygame.font.Font(None, 36)

    def render(self, screen: pygame.Surface, state: GameState):
        self._draw_board(screen)
        self._draw_highlights(screen, state)
        self._draw_pieces(screen, state)
        if state.game_over:
            self._draw_game_over(screen, state)

    def _draw_board(self, screen: pygame.Surface):
        for row in range(8):
            for col in range(8):
                color = (
                    self.COLORS["light_square"]
                    if (row + col) % 2 == 0
                    else self.COLORS["dark_square"]
                )
                pygame.draw.rect(
                    screen,
                    color,
                    (
                        col * self.square_size,
                        row * self.square_size,
                        self.square_size,
                        self.square_size,
                    ),
                )

    def _draw_highlights(self, screen: pygame.Surface, state: GameState):
        if state.selected_piece:
            self._draw_selected_highlight(screen, state.selected_piece)
            self._draw_legal_moves(screen, state.possible_moves)

        if state.last_move:
            self._draw_last_move_highlight(screen, state.last_move)

    def _draw_selected_highlight(self, screen: pygame.Surface, pos: Tuple[int, int]):
        surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        surface.fill((*self.COLORS["legal_moves"], 100))
        screen.blit(surface, (pos[1] * self.square_size, pos[0] * self.square_size))

    def _draw_legal_moves(self, screen: pygame.Surface, moves: Set[Tuple[int, int]]):
        for move in moves:
            center = (
                move[1] * self.square_size + self.square_size // 2,
                move[0] * self.square_size + self.square_size // 2,
            )
            pygame.draw.circle(
                screen, self.COLORS["legal_moves"], center, self.square_size // 8
            )

    def _draw_last_move_highlight(
        self, screen: pygame.Surface, last_move: Tuple[Tuple[int, int], Tuple[int, int]]
    ):
        for pos in last_move:
            surface = pygame.Surface(
                (self.square_size, self.square_size), pygame.SRCALPHA
            )
            surface.fill((*self.COLORS["last_move"], 100))
            screen.blit(surface, (pos[1] * self.square_size, pos[0] * self.square_size))

    def _draw_pieces(self, screen: pygame.Surface, state: GameState):
        for row in range(8):
            for col in range(8):
                piece = state.board.get_piece((row, col))
                if piece and (not state.dragging or (row, col) != state.selected_piece):
                    self._draw_piece(screen, piece, (row, col))

        if state.dragging and state.selected_piece:
            self._draw_dragged_piece(screen, state)

    def _draw_piece(self, screen: pygame.Surface, piece: Piece, pos: Tuple[int, int]):
        text_color = (
            self.COLORS["white_piece"] if piece.is_white else self.COLORS["black_piece"]
        )
        text_surface = self.font.render(piece.symbol, True, text_color)
        text_rect = text_surface.get_rect(
            center=(
                pos[1] * self.square_size + self.square_size // 2,
                pos[0] * self.square_size + self.square_size // 2,
            )
        )

        # Draw shadow
        shadow_surface = self.font.render(piece.symbol, True, (80, 80, 80))
        screen.blit(shadow_surface, text_rect.move(1.5, 1.5))
        screen.blit(text_surface, text_rect)

    def _draw_dragged_piece(self, screen: pygame.Surface, state: GameState):
        if not state.selected_piece:
            return

        piece = state.board.get_piece(state.selected_piece)
        if not piece:
            return

        text_color = (
            self.COLORS["white_piece"] if piece.is_white else self.COLORS["black_piece"]
        )
        text_surface = self.font.render(piece.symbol, True, text_color)
        mouse_pos = pygame.mouse.get_pos()
        text_rect = text_surface.get_rect(center=mouse_pos)
        screen.blit(text_surface, text_rect)

    def _draw_game_over(self, screen: pygame.Surface, state: GameState):
        if not state.game_result:
            return

        # Game result text
        texts = {
            "white_wins": "Checkmate, you win!",
            "black_wins": "Checkmate, you lose!",
            "draw": "Draw!",
        }
        text = self.game_over_font.render(
            texts[state.game_result], True, self.COLORS["text"]
        )
        text_rect = text.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2)
        )
        screen.blit(text, text_rect)

        # Play again prompt
        prompt = self.info_font.render(
            "Press ESC to play again", True, self.COLORS["text"]
        )
        prompt_rect = prompt.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2 + 100)
        )
        screen.blit(prompt, prompt_rect)
