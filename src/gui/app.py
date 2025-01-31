import logging
from typing import Tuple
from core.piece import PieceType
import pygame
import sys
import random
from pygame.locals import *
from game.state import GameState
from gui.renderer import GUIRenderer
from utils import _resource_path


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ChessApp:
    def __init__(self, width: int = 800, height: int = 800):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Chess 2")
        self.clock = pygame.time.Clock()
        self.state = GameState()
        self.renderer = GUIRenderer(width, height)
        self.computer_thinking = False
        self.in_menu = True
        self.game_mode = "ai"  # or "local"
        self.human_turn = True  # White always starts
        self.sounds = {
            'move': pygame.mixer.Sound(_resource_path('assets/sounds/move.mp3')),
            'capture': pygame.mixer.Sound(_resource_path('assets/sounds/capture.mp3')),
            'castle': pygame.mixer.Sound(_resource_path('assets/sounds/castle.mp3')),
            'check': pygame.mixer.Sound(_resource_path('assets/sounds/check.mp3')),
            'checkmate': pygame.mixer.Sound(_resource_path('assets/sounds/checkmate.mp3')),
        }

    def run(self):
        logging.info("Starting Chess 2 app")
        while True:
            self._handle_events()
            self._update_display()
            self.clock.tick(60)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                logging.info("Received QUIT event. Exiting.")
                pygame.quit()
                sys.exit()

            if event.type == KEYDOWN and event.key == K_ESCAPE:
                logging.info("Escape key pressed. Resetting game.")
                self.state.reset()
                self.in_menu = True

            if self.in_menu:
                self._handle_menu_events(event)
            else:
                if not self.state.game_over and not self.computer_thinking:
                    self._handle_game_events(event)

                if event.type == USEREVENT and self.computer_thinking:
                    self._handle_computer_move()

    def _handle_menu_events(self, event: pygame.event.Event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            x, y = pygame.mouse.get_pos()
            button_width = 300
            center_x = self.screen.get_width() // 2

            # Match the Y positions with renderer.py's button centers
            ai_button_y = self.screen.get_height() // 2 - 80
            if (
                center_x - button_width // 2 <= x <= center_x + button_width // 2
                and ai_button_y - 30 <= y <= ai_button_y + 30
            ):
                self.game_mode = "ai"
                self.in_menu = False
                self.sounds['move'].play()

            mp_button_y = ai_button_y + 100
            if (
                center_x - button_width // 2 <= x <= center_x + button_width // 2
                and mp_button_y - 30 <= y <= mp_button_y + 30
            ):
                self.game_mode = "local"
                self.in_menu = False
                self.human_turn = True
                self.sounds['move'].play()

    def _handle_game_events(self, event: pygame.event.Event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            logging.debug(f"Mouse button down event at {pygame.mouse.get_pos()}")
            self._handle_mouse_down(pygame.mouse.get_pos())

        elif event.type == MOUSEMOTION and event.buttons[0]:
            logging.debug("Mouse dragging started")
            if self.state.selected_piece:
                self.state.dragging = True

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            logging.debug(f"Mouse button up event at {pygame.mouse.get_pos()}")
            self._handle_mouse_up(pygame.mouse.get_pos())

    def _handle_mouse_down(self, pos: Tuple[int, int]):
        if self.game_mode == "local" or (
            self.game_mode == "ai" and self.state.is_white_turn
        ):
            square = self._pos_to_square(pos)
            piece = self.state.board.get_piece(square)
            logging.debug(f"Clicked on square: {square}, piece: {piece}")

            # If a piece is already selected (two-click mode)
            if self.state.selected_piece is not None:
                # If clicking on a valid target square, make the move
                if square in self.state.possible_moves:
                    logging.info(
                        f"Making move from {self.state.selected_piece} to {square} (two-click)"
                    )
                    if self.state.make_move(self.state.selected_piece, square):
                        self._trigger_computer_move()
                        self._play_move_sound()
                # Reset selection
                self.state.selected_piece = None
                self.state.possible_moves = set()
                return

            # If clicking on a valid piece, select it (don't start dragging yet)
            if piece and piece.is_white == self.state.is_white_turn:
                logging.info(f"Selected piece at {square}")
                self.state.drag_start = square
                self.state.selected_piece = square
                self.state.possible_moves = self.state.get_legal_moves(square)
            else:
                self.state.selected_piece = None
                self.state.possible_moves = set()

    def _handle_mouse_up(self, pos: Tuple[int, int]):
        if not self.state.dragging:
            return

        end_square = self._pos_to_square(pos)
        logging.debug(f"Mouse up at {pos}, converted to square {end_square}")
        if self.state.selected_piece and end_square in self.state.possible_moves:
            logging.info(
                f"Making move from {self.state.selected_piece} to {end_square} (drag)"
            )
            if self.state.make_move(self.state.selected_piece, end_square):
                self._trigger_computer_move()
                self._play_move_sound()

        self.state.dragging = False
        self.state.drag_start = None
        self.state.selected_piece = None  # Reset selected piece after move
        self.state.possible_moves = set()  # Clear possible moves

    def _trigger_computer_move(self):
        if self.game_mode == "ai" and not self.state.is_white_turn:
            if not self.state.game_over and not self.state.is_white_turn:
                logging.info("Triggering computer move")
                self.computer_thinking = True
                pygame.time.set_timer(USEREVENT, 1000)
        else:
            self.computer_thinking = False

    def _handle_computer_move(self):
        logging.info("Computer is making a move")
        legal_moves = []
        for r in range(8):
            for c in range(8):
                piece = self.state.board.get_piece((r, c))
                if piece and not piece.is_white:
                    moves = self.state.get_legal_moves((r, c))
                    legal_moves.extend(((r, c), move) for move in moves)

        if legal_moves:
            start, end = random.choice(legal_moves)
            logging.info(f"Computer moving from {start} to {end}")
            self.state.make_move(start, end)
            self._play_move_sound()

        pygame.time.set_timer(USEREVENT, 0)
        self.computer_thinking = False

    def _update_display(self):
        self.screen.fill((255, 255, 255))
        if self.in_menu:
            self.renderer.render_menu(self.screen)
        else:
            self.renderer.render(self.screen, self.state)
        pygame.display.flip()

    def _pos_to_square(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        x, y = pos
        return (y // self.renderer.square_size, x // self.renderer.square_size)
    
    def _play_move_sound(self):
        """Determine and play appropriate sound effect for the last move"""
        if self.state.game_over:
            self.sounds['checkmate'].play()
            return
            
        in_check = self.state.board.is_in_check(self.state.is_white_turn)
        if in_check:
            self.sounds['check'].play()
            return
            
        # Check for special move types
        piece = self.state.board.get_piece(self.state.last_move[1])
        start, end = self.state.last_move
        
        # Check for castling
        if piece and piece.type == PieceType.KING and abs(end[1] - start[1]) == 2:
            self.sounds['castle'].play()
            return
            
        # Check for capture
        if self.state.last_capture:
            self.sounds['capture'].play()
            return
            
        # Default move sound
        self.sounds['move'].play()


def main():
    app = ChessApp()
    app.run()


if __name__ == "__main__":
    main()
