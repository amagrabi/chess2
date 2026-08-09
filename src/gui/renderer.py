from typing import Dict, List, Optional, Set, Tuple

import pygame

from core.piece import Piece, PieceType
from game.state import PROMOTION_CHOICES, GameState
from utils import _resource_path

# The board is square; the panel beside it holds the move list and buttons.
BOARD_SIZE = 800
PANEL_WIDTH = 320
WINDOW_WIDTH = BOARD_SIZE + PANEL_WIDTH
WINDOW_HEIGHT = BOARD_SIZE

DIFFICULTY_LABELS = (("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"))

# Condensed for the in-game panel; the full wording lives on the rules screen.
SHORT_RULES = (
    "Knights jump in any direction",
    "Pawns move and capture forwards and diagonally",
    "The spy on h2/h7 converts one enemy piece, then dies",
    "Bishops cannot capture queens",
    "Stalemate gives your opponent another turn",
    "No en passant",
)

FULL_RULES = (
    "• Knights can now jump in all directions, because real horses stopped using L-shaped movement centuries ago.",
    "• Stalemate is no longer a draw. If you can't move, that's a you problem and your opponent gets another turn.",
    "• En passant has been disabled, so nobody ever has to spell it again.",
    "• Added a new piece on h2/h7, the spy. Moves in sneaky L-shapes, but converts enemy pieces instead of capturing them. Can only convert once and dies in the process.",
    "• Bishops can no longer capture queens. Just doesn't seem right.",
    "• Fixed a bug where computers were better at chess than humans.",
    "• Pawns can now move and capture both forwards and diagonally, like normal people. But they still can't move backwards. That would be ridiculous.",
)


class GUIRenderer:
    COLORS = {
        "background": (255, 255, 255),
        # Softer, less saturated wood than before, which gives the pieces more
        # contrast to sit against.
        "dark_square": (172, 126, 89),
        "light_square": (238, 216, 180),
        # Move hints are a neutral translucent brown rather than olive green,
        # so they read as part of the board instead of fighting it.
        "legal_moves": (74, 52, 36),
        "last_move": (214, 176, 84),
        "selected": (238, 202, 110),
        "check": (198, 74, 58),
        "white_piece": (250, 247, 242),
        "black_piece": (38, 32, 28),
        "piece_outline_light": (58, 44, 34),
        "piece_outline_dark": (232, 224, 212),
        "text": (0, 0, 0),
        "labels": (70, 70, 70),
        "panel": (38, 30, 24),
        "panel_text": (222, 208, 186),
        "panel_muted": (140, 124, 104),
        "button": (110, 78, 48),
        "button_active": (150, 110, 66),
        "button_disabled": (66, 54, 44),
        "accent": (203, 174, 122),
    }

    def __init__(self, screen_width: int = WINDOW_WIDTH, screen_height: int = WINDOW_HEIGHT):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.board_size = min(screen_height, screen_width - PANEL_WIDTH)
        self.square_size = self.board_size // 8

        # Everything is set in the bundled serif rather than pygame's built-in
        # freesansbold, which looks generic next to the painted backdrop.
        self.font = self._load_font(72)  # chess glyphs
        self.title_font = self._load_font(96, bold=True)
        self.game_over_font = self._load_font(64, bold=True)
        self.heading_font = self._load_font(34, bold=True)
        self.info_font = self._load_font(32)
        self.body_font = self._load_font(25)
        self.small_font = self._load_font(25)
        # The move list is laid out in columns, so it wants a plain UI face.
        self.mono_font = pygame.font.Font(None, 24)

        self.menu_background = self._load_menu_background()
        # Pieces are redrawn every frame; rendering the glyph and its outline
        # each time is wasteful, so cache one surface per (type, colour).
        self._piece_cache = {}

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
        try:
            font = pygame.font.Font(_resource_path("assets/FreeSerif.ttf"), size)
        except Exception as e:
            print(f"Serif font not available ({e}). Using default font.")
            font = pygame.font.Font(None, size)
        font.set_bold(bold)
        return font

    # ---------------------------------------------------------------- pieces

    def _piece_surface(self, piece: Piece) -> pygame.Surface:
        key = (piece.type, piece.is_white)
        cached = self._piece_cache.get(key)
        if cached is not None:
            return cached

        fill = (
            self.COLORS["white_piece"] if piece.is_white else self.COLORS["black_piece"]
        )
        outline = (
            self.COLORS["piece_outline_light"]
            if piece.is_white
            else self.COLORS["piece_outline_dark"]
        )

        body = self.font.render(piece.glyph, True, fill)
        edge = self.font.render(piece.glyph, True, outline)

        thickness = 2
        surface = pygame.Surface(
            (body.get_width() + thickness * 2, body.get_height() + thickness * 2),
            pygame.SRCALPHA,
        )
        # Stamp the outline in eight directions, then the fill on top.
        for dx, dy in (
            (-1, -1), (0, -1), (1, -1),
            (-1, 0), (1, 0),
            (-1, 1), (0, 1), (1, 1),
        ):
            surface.blit(
                edge, (thickness + dx * thickness, thickness + dy * thickness)
            )
        surface.blit(body, (thickness, thickness))

        self._piece_cache[key] = surface
        return surface

    # ------------------------------------------------------------- background

    def _load_menu_background(self):
        """Load and scale the menu backdrop once, so it isn't decoded every frame."""
        try:
            bg = pygame.image.load(_resource_path("assets/menu_background.jpg")).convert()
        except Exception as e:
            print(f"Menu background not available ({e}). Using plain background.")
            return None

        # Scale to cover the window without distorting the artwork, then centre.
        bw, bh = bg.get_size()
        scale = max(self.screen_width / bw, self.screen_height / bh)
        scaled = pygame.transform.smoothscale(bg, (int(bw * scale), int(bh * scale)))
        surface = pygame.Surface((self.screen_width, self.screen_height))
        surface.blit(
            scaled,
            (
                (self.screen_width - scaled.get_width()) // 2,
                (self.screen_height - scaled.get_height()) // 2,
            ),
        )
        return surface

    def _draw_menu_background(self, screen: pygame.Surface):
        if self.menu_background is not None:
            screen.blit(self.menu_background, (0, 0))
        else:
            screen.fill(self.COLORS["background"])

    # ---------------------------------------------------------------- geometry

    def menu_rects(self) -> Dict[str, pygame.Rect]:
        """Button rectangles for the menu, shared by drawing and hit-testing."""
        centre_x = self.screen_width // 2
        top = self.screen_height // 2 - 110
        rects = {
            "ai": pygame.Rect(0, 0, 320, 60),
            "local": pygame.Rect(0, 0, 320, 60),
            "rules": pygame.Rect(0, 0, 320, 60),
        }
        rects["ai"].center = (centre_x, top)
        rects["local"].center = (centre_x, top + 150)
        rects["rules"].center = (centre_x, top + 225)

        # Difficulty chips sit directly under the "vs. Computer" button.
        chip_width, gap = 100, 8
        total = len(DIFFICULTY_LABELS) * chip_width + (len(DIFFICULTY_LABELS) - 1) * gap
        x = centre_x - total // 2
        for key, _ in DIFFICULTY_LABELS:
            rects[key] = pygame.Rect(x, top + 45, chip_width, 38)
            x += chip_width + gap
        return rects

    def rules_back_rect(self) -> pygame.Rect:
        return pygame.Rect(20, self.screen_height - 70, 200, 50)

    def panel_button_rects(self) -> Dict[str, pygame.Rect]:
        x = self.board_size + 24
        width = PANEL_WIDTH - 48
        return {
            "rules": pygame.Rect(x, self.screen_height - 212, width, 52),
            "undo": pygame.Rect(x, self.screen_height - 148, width, 52),
            "menu": pygame.Rect(x, self.screen_height - 84, width, 52),
        }

    def rules_overlay_close_rect(self) -> pygame.Rect:
        return pygame.Rect(self.board_size // 2 - 90, self.board_size - 84, 180, 52)

    def promotion_rects(self) -> List[Tuple[PieceType, pygame.Rect]]:
        size = 110
        gap = 12
        total = len(PROMOTION_CHOICES) * size + (len(PROMOTION_CHOICES) - 1) * gap
        x = self.board_size // 2 - total // 2
        y = self.board_size // 2 - size // 2
        out = []
        for piece_type in PROMOTION_CHOICES:
            out.append((piece_type, pygame.Rect(x, y, size, size)))
            x += size + gap
        return out

    def square_at(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Screen position -> board square, or None if outside the board."""
        x, y = pos
        if not (0 <= x < self.board_size and 0 <= y < self.board_size):
            return None
        return (y // self.square_size, x // self.square_size)

    # ------------------------------------------------------------------ menu

    def _draw_title(self, screen: pygame.Surface, text: str, centre_y: int):
        """Dark serif over a light offset copy: a subtle emboss that lifts the
        title off the painted backdrop without the sticker look of an outline."""
        centre_x = self.screen_width // 2
        highlight = self.title_font.render(text, True, (252, 246, 235))
        screen.blit(highlight, highlight.get_rect(center=(centre_x + 2, centre_y + 3)))
        body = self.title_font.render(text, True, (38, 27, 20))
        screen.blit(body, body.get_rect(center=(centre_x, centre_y)))

    def _draw_button(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        colour=None,
        text_colour=None,
    ):
        pygame.draw.rect(screen, colour or self.COLORS["button"], rect, border_radius=6)
        text = font.render(label, True, text_colour or self.COLORS["white_piece"])
        screen.blit(text, text.get_rect(center=rect.center))

    def render_menu(self, screen: pygame.Surface, difficulty: str = "medium"):
        self._draw_menu_background(screen)
        rects = self.menu_rects()

        self._draw_title(screen, "Chess 2", self.screen_height // 4)

        self._draw_button(screen, rects["ai"], "Play vs. Computer", self.info_font)
        for key, label in DIFFICULTY_LABELS:
            selected = key == difficulty
            self._draw_button(
                screen,
                rects[key],
                label,
                self.small_font,
                colour=self.COLORS["button_active"]
                if selected
                else self.COLORS["button_disabled"],
                text_colour=self.COLORS["white_piece"]
                if selected
                else self.COLORS["panel_muted"],
            )
        self._draw_button(screen, rects["local"], "Local Multiplayer", self.info_font)
        self._draw_button(screen, rects["rules"], "Rules", self.info_font)

    def render_rules(self, screen: pygame.Surface):
        self._draw_menu_background(screen)

        overlay = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA
        )
        overlay.fill((28, 20, 15, 150))
        screen.blit(overlay, (0, 0))

        # Hold the text to a readable column instead of letting it run the full
        # width of the window.
        card = pygame.Rect(0, 0, min(self.screen_width - 180, 940), 0)
        card.centerx = self.screen_width // 2
        card.top = 120
        card.height = self.screen_height - card.top - 80

        panel = pygame.Surface(card.size, pygame.SRCALPHA)
        panel.fill((250, 244, 232, 240))
        screen.blit(panel, card.topleft)
        pygame.draw.rect(screen, (150, 122, 88), card, width=2, border_radius=4)

        self._draw_title(screen, "House Rules", 62)

        self._draw_rule_list(
            screen,
            card.inflate(-88, -72),
            self.body_font,
            (48, 36, 28),
            bullet_colour=(150, 110, 66),
        )

        self._draw_button(screen, self.rules_back_rect(), "Back", self.info_font)

    def _draw_rule_list(
        self,
        screen: pygame.Surface,
        area: pygame.Rect,
        font: pygame.font.Font,
        colour,
        bullet_colour=None,
    ):
        """Render the house rules with a hanging indent under each bullet.

        Wrapped lines line up with the text rather than the bullet, and rules
        are separated by more space than the lines within one rule, so each
        reads as its own item.
        """
        indent = 30
        line_height = font.get_linesize() + 4
        gap = 14
        y = area.top
        for rule in FULL_RULES:
            text = rule.lstrip("•").strip()
            lines = self._wrap(text, font, area.width - indent)
            screen.blit(
                font.render("•", True, bullet_colour or colour), (area.left, y)
            )
            for line in lines:
                screen.blit(
                    font.render(line, True, colour), (area.left + indent, y)
                )
                y += line_height
            y += gap
        return y

    @staticmethod
    def _wrap(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        words = text.split()
        if not words:
            return []
        lines, current = [], words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] < max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    # ------------------------------------------------------------------ game

    def render(
        self,
        screen: pygame.Surface,
        state: GameState,
        game_mode: str = "ai",
        difficulty: str = "medium",
        thinking: bool = False,
        promoting: bool = False,
        showing_rules: bool = False,
    ):
        self._draw_board(screen)
        self._draw_highlights(screen, state)
        self._draw_pieces(screen, state)
        self._draw_labels(screen)
        self._draw_panel(screen, state, game_mode, difficulty, thinking)
        if showing_rules:
            self._draw_rules_overlay(screen)
        elif promoting:
            self._draw_promotion(screen, state)
        elif state.game_over:
            self._draw_game_over(screen, state)

    def _draw_rules_overlay(self, screen: pygame.Surface):
        """The house rules, over the board, without leaving the game."""
        overlay = pygame.Surface((self.board_size, self.board_size), pygame.SRCALPHA)
        overlay.fill((22, 16, 13, 235))
        screen.blit(overlay, (0, 0))

        title = self.game_over_font.render(
            "House Rules", True, self.COLORS["accent"]
        )
        screen.blit(title, title.get_rect(center=(self.board_size // 2, 56)))

        self._draw_rule_list(
            screen,
            pygame.Rect(48, 112, self.board_size - 96, self.board_size - 210),
            self.small_font,
            self.COLORS["panel_text"],
            bullet_colour=self.COLORS["accent"],
        )

        self._draw_button(
            screen, self.rules_overlay_close_rect(), "Back to game", self.info_font
        )

    def _draw_panel(
        self,
        screen: pygame.Surface,
        state: GameState,
        game_mode: str,
        difficulty: str,
        thinking: bool,
    ):
        panel = pygame.Rect(self.board_size, 0, PANEL_WIDTH, self.screen_height)
        pygame.draw.rect(screen, self.COLORS["panel"], panel)

        x = self.board_size + 24
        y = 28

        heading = self.heading_font.render("Chess 2", True, self.COLORS["accent"])
        screen.blit(heading, (x, y))
        y += 44

        if game_mode == "ai":
            subtitle = f"vs. Computer ({difficulty.capitalize()})"
        else:
            subtitle = "Local Multiplayer"
        screen.blit(
            self.small_font.render(subtitle, True, self.COLORS["panel_muted"]), (x, y)
        )
        y += 34

        if thinking:
            status = "Computer is thinking..."
        elif state.game_over:
            status = {
                "white_wins": "White wins",
                "black_wins": "Black wins",
                "draw": "Draw",
            }.get(state.game_result, "Game over")
        else:
            status = "White to move" if state.is_white_turn else "Black to move"
            if state.board.is_in_check(state.is_white_turn):
                status += " - check!"
        screen.blit(
            self.small_font.render(status, True, self.COLORS["panel_text"]), (x, y)
        )
        y += 40

        pygame.draw.line(
            screen, self.COLORS["button_disabled"], (x, y), (x + PANEL_WIDTH - 48, y)
        )
        y += 16

        self._draw_move_list(screen, state, x, y)

        buttons = self.panel_button_rects()
        undo_enabled = state.can_undo()
        self._draw_button(screen, buttons["rules"], "House Rules", self.info_font)
        self._draw_button(
            screen,
            buttons["undo"],
            "Undo",
            self.info_font,
            colour=self.COLORS["button"]
            if undo_enabled
            else self.COLORS["button_disabled"],
            text_colour=self.COLORS["white_piece"]
            if undo_enabled
            else self.COLORS["panel_muted"],
        )
        self._draw_button(screen, buttons["menu"], "Main Menu", self.info_font)

    def _draw_move_list(
        self, screen: pygame.Surface, state: GameState, x: int, y: int
    ):
        available = self.screen_height - 234 - y
        line_height = 24
        max_rows = max(available // line_height, 0)

        # Before the first move the panel is empty anyway, so use it to teach
        # the house rules -- they are the whole point of the game and easy to
        # miss otherwise.
        if not state.move_log:
            screen.blit(
                self.small_font.render(
                    "What's different", True, self.COLORS["accent"]
                ),
                (x, y),
            )
            y += 30
            for hint in SHORT_RULES:
                for line in self._wrap(
                    f"• {hint}", self.mono_font, PANEL_WIDTH - 48
                ):
                    screen.blit(
                        self.mono_font.render(
                            line, True, self.COLORS["panel_muted"]
                        ),
                        (x, y),
                    )
                    y += 22
                y += 4
            return

        rows = []
        for i in range(0, len(state.move_log), 2):
            rows.append(
                (
                    f"{i // 2 + 1}.",
                    state.move_log[i],
                    state.move_log[i + 1] if i + 1 < len(state.move_log) else "",
                )
            )

        # Explicit columns: the font is proportional, so padded strings would
        # not line up.
        for number, white, black in rows[-max_rows:]:
            screen.blit(
                self.mono_font.render(number, True, self.COLORS["panel_muted"]), (x, y)
            )
            screen.blit(
                self.mono_font.render(white, True, self.COLORS["panel_text"]),
                (x + 38, y),
            )
            if black:
                screen.blit(
                    self.mono_font.render(black, True, self.COLORS["panel_text"]),
                    (x + 142, y),
                )
            y += line_height

    def _draw_promotion(self, screen: pygame.Surface, state: GameState):
        overlay = pygame.Surface((self.board_size, self.board_size), pygame.SRCALPHA)
        overlay.fill((20, 15, 12, 190))
        screen.blit(overlay, (0, 0))

        prompt = self.info_font.render(
            "Promote to:", True, self.COLORS["panel_text"]
        )
        screen.blit(
            prompt,
            prompt.get_rect(
                center=(self.board_size // 2, self.board_size // 2 - 100)
            ),
        )

        # The promoting side is the one that just moved, i.e. not the side to move.
        is_white = not state.is_white_turn
        for piece_type, rect in self.promotion_rects():
            pygame.draw.rect(screen, self.COLORS["light_square"], rect, border_radius=8)
            piece_surface = self._piece_surface(Piece(piece_type, is_white))
            screen.blit(piece_surface, piece_surface.get_rect(center=rect.center))

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
        if state.last_move:
            self._draw_last_move_highlight(screen, state.last_move)

        self._draw_check_highlight(screen, state)

        if state.selected_piece:
            self._draw_selected_highlight(screen, state.selected_piece)
            self._draw_legal_moves(screen, state)

    def _tint_square(self, screen: pygame.Surface, pos: Tuple[int, int], colour, alpha):
        surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        surface.fill((*colour, alpha))
        screen.blit(surface, (pos[1] * self.square_size, pos[0] * self.square_size))

    def _draw_selected_highlight(self, screen: pygame.Surface, pos: Tuple[int, int]):
        self._tint_square(screen, pos, self.COLORS["selected"], 130)

    def _draw_check_highlight(self, screen: pygame.Surface, state: GameState):
        """Mark the king's square when it is in check."""
        if state.game_over or not state.board.is_in_check(state.is_white_turn):
            return
        for r in range(8):
            for c in range(8):
                piece = state.board.board[r][c]
                if (
                    piece
                    and piece.type == PieceType.KING
                    and piece.is_white == state.is_white_turn
                ):
                    self._tint_square(screen, (r, c), self.COLORS["check"], 120)
                    return

    def _draw_legal_moves(self, screen: pygame.Surface, state: GameState):
        """A dot marks a quiet move; a ring marks a capture or spy conversion."""
        for move in state.possible_moves:
            overlay = pygame.Surface(
                (self.square_size, self.square_size), pygame.SRCALPHA
            )
            local = (self.square_size // 2, self.square_size // 2)
            if state.board.get_piece(move) is not None:
                pygame.draw.circle(
                    overlay,
                    (*self.COLORS["legal_moves"], 120),
                    local,
                    self.square_size // 2 - 4,
                    width=6,
                )
            else:
                pygame.draw.circle(
                    overlay,
                    (*self.COLORS["legal_moves"], 110),
                    local,
                    self.square_size // 7,
                )
            screen.blit(
                overlay,
                (move[1] * self.square_size, move[0] * self.square_size),
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
        surface = self._piece_surface(piece)
        screen.blit(
            surface,
            surface.get_rect(
                center=(
                    pos[1] * self.square_size + self.square_size // 2,
                    pos[0] * self.square_size + self.square_size // 2,
                )
            ),
        )

    def _draw_dragged_piece(self, screen: pygame.Surface, state: GameState):
        if not state.selected_piece:
            return

        piece = state.board.get_piece(state.selected_piece)
        if not piece:
            return

        surface = self._piece_surface(piece)
        screen.blit(surface, surface.get_rect(center=pygame.mouse.get_pos()))

    def _draw_labels(self, screen: pygame.Surface):
        label_font = pygame.font.Font(None, 16)
        for row in range(8):
            for col in range(8):
                if row == 7:
                    label = chr(ord("a") + col)
                    text_surface = label_font.render(label, True, self.COLORS["labels"])
                    screen.blit(
                        text_surface,
                        text_surface.get_rect(
                            bottomright=(
                                (col + 1) * self.square_size - 2,
                                (row + 1) * self.square_size - 2,
                            )
                        ),
                    )
                if col == 7:
                    label = str(8 - row)
                    text_surface = label_font.render(label, True, self.COLORS["labels"])
                    screen.blit(
                        text_surface,
                        text_surface.get_rect(
                            topright=(
                                (col + 1) * self.square_size - 2,
                                row * self.square_size + 2,
                            )
                        ),
                    )

    def _draw_game_over(self, screen: pygame.Surface, state: GameState):
        if not state.game_result:
            return

        texts = {
            "white_wins": "Checkmate, white wins!",
            "black_wins": "Checkmate, black wins!",
            "draw": "Draw by threefold repetition!",
        }
        centre_x = self.board_size // 2

        banner = pygame.Surface((self.board_size, 160), pygame.SRCALPHA)
        banner.fill((20, 15, 12, 200))
        screen.blit(banner, (0, self.board_size // 2 - 80))

        text = self.game_over_font.render(
            texts[state.game_result], True, self.COLORS["panel_text"]
        )
        screen.blit(text, text.get_rect(center=(centre_x, self.board_size // 2 - 20)))

        prompt = self.info_font.render(
            "Press ESC for the menu", True, self.COLORS["panel_muted"]
        )
        screen.blit(prompt, prompt.get_rect(center=(centre_x, self.board_size // 2 + 40)))
