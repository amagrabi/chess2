import asyncio
import logging
import sys
from typing import Optional, Tuple

import pygame
from pygame.locals import (
    K_ESCAPE,
    K_r,
    K_u,
    KEYDOWN,
    MOUSEBUTTONDOWN,
    MOUSEBUTTONUP,
    MOUSEMOTION,
    QUIT,
)

from core.piece import Piece, PieceType
from game import ai
from game.state import GameState
from gui.renderer import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    GUIRenderer,
    MoveAnimation,
    Notice,
    SquareEffect,
)
from utils import _resource_path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ChessApp:
    def __init__(self, width: int = WINDOW_WIDTH, height: int = WINDOW_HEIGHT):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception as e:
            # No audio device (common in browsers before a user gesture).
            logging.warning(f"Audio unavailable, continuing without sound: {e}")
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Chess 2")
        self.clock = pygame.time.Clock()
        self.state = GameState()
        self.renderer = GUIRenderer(width, height)
        self.computer_thinking = False
        self.in_menu = True
        self.in_rules = False
        self.game_mode = "ai"  # or "local"
        self.difficulty = ai.MEDIUM
        self.sounds = {}
        self.assets_loaded = False
        # Set while waiting for the player to choose a promotion piece.
        self.pending_promotion: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
        # House-rules overlay shown over the board, without leaving the game.
        self.rules_overlay = False
        # Pieces currently sliding to their new squares, and the burst that
        # marks a spy conversion.
        self.anim: Optional[MoveAnimation] = None
        self.effect: Optional[SquareEffect] = None
        # Brief banner over the board when a house rule fires on its own.
        self.notice: Optional[Notice] = None
        # Move sounds wait for the slide to land, so the thud matches the piece
        # arriving rather than leading it.
        self.pending_sound: Optional[str] = None
        self._hand_cursor = False

    def _load_assets(self):
        """Load audio assets. Called after first event loop yield so pygbag VFS is ready."""
        for name in ("move", "capture", "castle", "check", "checkmate", "promote"):
            last_error = None
            # pygbag transcodes .ogg to .mp3 when packaging for the web, so try both.
            for ext in ("ogg", "mp3"):
                try:
                    path = _resource_path(f"assets/sounds/{name}.{ext}")
                    self.sounds[name] = pygame.mixer.Sound(path)
                    break
                except Exception as e:
                    # Keep the first failure: it names the format we actually
                    # ship, so the log says why that one could not be decoded.
                    last_error = last_error or e
            else:
                logging.warning(f"Could not load sound '{name}': {last_error}")
        self.assets_loaded = True

    def _play(self, name: str):
        """Play a sound effect if it loaded successfully."""
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    async def run(self):
        logging.info("Starting Chess 2 app")
        # Yield once first so pygbag's virtual filesystem is fully mounted
        await asyncio.sleep(0)
        self._load_assets()
        while True:
            self._handle_events()
            self._tick_animation()
            self._update_cursor()
            self._update_display()

            if self._computer_to_move():
                await self._make_computer_move()

            self.clock.tick(60)
            await asyncio.sleep(0)

    def _tick_animation(self):
        """Retire finished animations and release the sound they were holding."""
        if self.anim is not None and self.anim.done:
            self.anim = None
            if self.pending_sound:
                self._play(self.pending_sound)
                self.pending_sound = None
        if self.effect is not None and self.effect.done:
            self.effect = None
        if self.notice is not None and self.notice.done:
            self.notice = None

    def _animating(self) -> bool:
        return self.anim is not None and not self.anim.done

    def _clickable_rects(self) -> list:
        """Every button on the screen right now, for the pointer cursor."""
        renderer = self.renderer
        if self.in_menu:
            return list(renderer.menu_rects().values())
        if self.in_rules:
            return [renderer.rules_back_rect()]
        if self.rules_overlay:
            return [renderer.rules_overlay_close_rect()]
        if self.pending_promotion:
            return [rect for _, rect in renderer.promotion_rects()]

        rects = list(renderer.panel_button_rects().values())
        if self.state.game_over:
            rects += list(renderer.game_over_rects().values())
        return rects

    def _update_cursor(self):
        """Show a hand over anything clickable."""
        pos = pygame.mouse.get_pos()
        hand = any(rect.collidepoint(pos) for rect in self._clickable_rects())
        if hand == self._hand_cursor:
            return
        self._hand_cursor = hand
        try:
            pygame.mouse.set_cursor(
                pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
            )
        except Exception as e:
            # Some SDL builds ship without system cursors; the game is fine
            # without them, so stop asking.
            logging.warning(f"System cursors unavailable: {e}")
            self._update_cursor = lambda: None

    # ---------------------------------------------------------------- events

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                logging.info("Received QUIT event. Exiting.")
                pygame.quit()
                sys.exit()

            if event.type == KEYDOWN and event.key == K_ESCAPE:
                # Escape backs out of the rules overlay first, then to the menu.
                if self.rules_overlay:
                    self.rules_overlay = False
                else:
                    self._return_to_menu()
                continue

            in_game = not self.in_menu and not self.in_rules

            if event.type == KEYDOWN and event.key == K_u and in_game:
                self._undo()
                continue

            if (
                event.type == KEYDOWN
                and event.key == K_r
                and in_game
                and self.state.game_over
            ):
                self._rematch()
                continue

            if self.in_menu:
                self._handle_menu_events(event)
            elif self.in_rules:
                self._handle_rules_events(event)
            elif self.rules_overlay:
                self._handle_rules_overlay_events(event)
            elif self.pending_promotion:
                self._handle_promotion_events(event)
            else:
                if self.state.game_over:
                    self._handle_game_over_events(event)
                if not self.computer_thinking:
                    self._handle_panel_events(event)
                if not self.state.game_over and not self.computer_thinking:
                    self._handle_game_events(event)

    def _return_to_menu(self):
        logging.info("Returning to menu")
        self._new_game()
        self.in_menu = True
        self.in_rules = False

    def _new_game(self):
        """Clear the board and everything in flight, keeping mode and difficulty."""
        self.state.reset()
        self.pending_promotion = None
        self.rules_overlay = False
        self.anim = None
        self.effect = None
        self.notice = None
        self.pending_sound = None

    def _rematch(self):
        if self.computer_thinking:
            return
        logging.info("Starting a rematch")
        self._new_game()
        self._play("move")

    def _handle_menu_events(self, event: pygame.event.Event):
        if event.type != MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = event.pos
        rects = self.renderer.menu_rects()

        for key in (ai.EASY, ai.MEDIUM, ai.HARD):
            if rects[key].collidepoint(pos):
                self.difficulty = key
                self._play("move")
                return

        if rects["ai"].collidepoint(pos):
            self.game_mode = "ai"
            self.in_menu = False
            self._play("move")
        elif rects["local"].collidepoint(pos):
            self.game_mode = "local"
            self.in_menu = False
            self._play("move")
        elif rects["rules"].collidepoint(pos):
            self.in_menu = False
            self.in_rules = True
            self._play("move")

    def _handle_rules_events(self, event: pygame.event.Event):
        if event.type != MOUSEBUTTONDOWN or event.button != 1:
            return
        if self.renderer.rules_back_rect().collidepoint(event.pos):
            self.in_rules = False
            self.in_menu = True
            self._play("move")

    def _handle_rules_overlay_events(self, event: pygame.event.Event):
        # Only the button (or Escape) closes it. Dismissing on any click meant
        # the paired down/up events the runtime delivers could shut it again
        # immediately.
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.renderer.rules_overlay_close_rect().collidepoint(event.pos):
                self.rules_overlay = False
                self._play("move")

    def _handle_game_over_events(self, event: pygame.event.Event):
        """Rematch or leave, without having to guess at a keyboard shortcut."""
        if event.type != MOUSEBUTTONDOWN or event.button != 1:
            return
        buttons = self.renderer.game_over_rects()
        if buttons["rematch"].collidepoint(event.pos):
            self._rematch()
        elif buttons["menu"].collidepoint(event.pos):
            self._return_to_menu()

    def _handle_panel_events(self, event: pygame.event.Event):
        if event.type != MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = event.pos
        buttons = self.renderer.panel_button_rects()
        if buttons["rules"].collidepoint(pos):
            self.rules_overlay = True
            self._play("move")
        elif buttons["undo"].collidepoint(pos):
            self._undo()
        elif buttons["menu"].collidepoint(pos):
            self._return_to_menu()

    def _handle_promotion_events(self, event: pygame.event.Event):
        if event.type != MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = event.pos
        for piece_type, rect in self.renderer.promotion_rects():
            if rect.collidepoint(pos):
                start, end = self.pending_promotion
                self.pending_promotion = None
                self._play_move(start, end, promotion=piece_type)
                return

    def _undo(self):
        """Take back the last move; in AI mode take back the reply too."""
        if self.computer_thinking or not self.state.can_undo():
            return

        self.pending_promotion = None
        self.anim = None
        self.effect = None
        self.notice = None
        self.pending_sound = None
        self.state.undo()
        # Undo the computer's reply as well, so it stays the player's turn.
        if self.game_mode == "ai" and not self.state.is_white_turn:
            self.state.undo()
        self._play("move")

    def _handle_game_events(self, event: pygame.event.Event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_down(event.pos)

        elif event.type == MOUSEMOTION and event.buttons[0]:
            # Only count as a drag once the pointer actually leaves the square
            # it started on. Otherwise the jitter of an ordinary click (and any
            # touch) starts a "drag" that ends where it began and cancels the
            # selection.
            if (
                self.state.selected_piece
                and self.renderer.square_at(event.pos) != self.state.drag_start
            ):
                self.state.dragging = True

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            self._handle_mouse_up(event.pos)

    def _human_to_move(self) -> bool:
        return self.game_mode == "local" or self.state.is_white_turn

    def _handle_mouse_down(self, pos: Tuple[int, int]):
        if not self._human_to_move():
            return

        square = self.renderer.square_at(pos)
        if square is None:
            return

        piece = self.state.board.get_piece(square)

        # Second click of a click-click move.
        if self.state.selected_piece is not None:
            if square in self.state.possible_moves:
                self._attempt_move(self.state.selected_piece, square)
            self.state.selected_piece = None
            self.state.possible_moves = set()
            return

        if piece and piece.is_white == self.state.is_white_turn:
            self.state.drag_start = square
            self.state.selected_piece = square
            self.state.possible_moves = self.state.get_legal_moves(square)
        else:
            self.state.selected_piece = None
            self.state.possible_moves = set()

    def _handle_mouse_up(self, pos: Tuple[int, int]):
        if not self.state.dragging:
            return

        end_square = self.renderer.square_at(pos)

        # Released back where it started: keep the piece selected so the player
        # can finish the move with a second click.
        if end_square is not None and end_square == self.state.selected_piece:
            self.state.dragging = False
            return

        if (
            end_square is not None
            and self.state.selected_piece
            and end_square in self.state.possible_moves
        ):
            # The player has already dragged the piece there; sliding it again
            # from the square it left would look like a stutter.
            self._attempt_move(self.state.selected_piece, end_square, animate=False)

        self.state.dragging = False
        self.state.drag_start = None
        self.state.selected_piece = None
        self.state.possible_moves = set()

    def _attempt_move(
        self, start: Tuple[int, int], end: Tuple[int, int], animate: bool = True
    ):
        """Play a human move, pausing for a promotion choice when needed."""
        if self.state.is_promotion(start, end):
            self.state.dragging = False
            self.state.selected_piece = None
            self.state.possible_moves = set()
            self.pending_promotion = (start, end)
            return

        self._play_move(start, end, animate=animate)

    def _play_move(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        promotion: PieceType = PieceType.QUEEN,
        animate: bool = True,
    ) -> bool:
        """Make a move and start the animation, effect and sound that go with it."""
        mover = self.state.board.get_piece(start)
        if not self.state.make_move(start, end, promotion=promotion):
            return False

        segments = []
        if animate and mover is not None:
            landed = self.state.board.get_piece(end)
            # A spy dies converting, so slide the spy in rather than the piece
            # it left behind on the square.
            drawn = mover if self.state.last_move_kind == "convert" else landed or mover
            segments.append((Piece(drawn.type, drawn.is_white), start, end))
            if self.state.last_move_kind == "castle":
                row = start[0]
                rook_from = (row, 7 if end[1] > start[1] else 0)
                rook_to = (row, end[1] - 1 if end[1] > start[1] else end[1] + 1)
                segments.append(
                    (Piece(PieceType.ROOK, mover.is_white), rook_from, rook_to)
                )

        self.anim = MoveAnimation(segments) if segments else None
        if self.state.last_move_kind == "convert":
            self.effect = SquareEffect(end)
        if self.state.stalemate_skipped:
            # The opponent had no legal move, so the house rule handed the turn
            # straight back. Say so, or it reads as the same side moving twice.
            side = "White" if self.state.is_white_turn else "Black"
            self.notice = Notice(f"Stalemate - {side} moves again")

        sound = self._move_sound()
        if self.anim is not None:
            self.pending_sound = sound
        else:
            self._play(sound)
        return True

    # ------------------------------------------------------------- computer

    def _computer_to_move(self) -> bool:
        return (
            self.game_mode == "ai"
            and not self.in_menu
            and not self.in_rules
            and not self.state.game_over
            and not self.state.is_white_turn
            and not self.pending_promotion
            and not self.rules_overlay
            # The search blocks the loop between yields, which would freeze the
            # player's piece in mid-slide. Let it land first.
            and not self._animating()
        )

    async def _make_computer_move(self):
        self.computer_thinking = True
        # Paint the "thinking" state before the search starts blocking.
        self._update_display()
        await asyncio.sleep(0)

        try:
            move = await ai.choose_move(self.state.board, False, self.difficulty)
        except Exception:
            logging.exception("Computer move failed; falling back to no move")
            move = None

        if move and not self.in_menu:
            self._play_move(move[0], move[1], promotion=PieceType.QUEEN)

        self.computer_thinking = False

    # -------------------------------------------------------------- display

    def _update_display(self):
        if self.in_menu:
            self.renderer.render_menu(self.screen, self.difficulty)
        elif self.in_rules:
            self.renderer.render_rules(self.screen)
        else:
            self.renderer.render(
                self.screen,
                self.state,
                game_mode=self.game_mode,
                difficulty=self.difficulty,
                thinking=self.computer_thinking,
                promoting=self.pending_promotion is not None,
                showing_rules=self.rules_overlay,
                anim=self.anim,
                effect=self.effect,
                notice=self.notice,
            )
        pygame.display.flip()

    def _move_sound(self) -> str:
        """Name the sound the last move earned.

        Ending the game and giving check outrank what the move itself did, so a
        mating capture is heard as a mate.
        """
        if self.state.game_over:
            return "checkmate"
        if self.state.board.is_in_check(self.state.is_white_turn):
            return "check"
        return {
            "promote": "promote",
            "castle": "castle",
            "capture": "capture",
            # A conversion is not a capture, but it is the closest sound we have.
            "convert": "capture",
        }.get(self.state.last_move_kind, "move")


async def main():
    app = ChessApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
