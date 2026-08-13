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

TAGLINE = "Chess, but with the last hundred years of patches applied"

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


def _lighten(colour, amount: int):
    return tuple(min(255, channel + amount) for channel in colour)


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
        # Board coordinates are drawn in the colour of the opposite square, so
        # they read as printed on the wood instead of floating over it.
        "label_on_light": (150, 118, 84),
        "label_on_dark": (223, 203, 172),
        "panel": (38, 30, 24),
        "panel_text": (222, 208, 186),
        "panel_muted": (140, 124, 104),
        "button": (110, 78, 48),
        "button_hover": (138, 100, 62),
        "button_active": (150, 110, 66),
        "button_disabled": (66, 54, 44),
        "accent": (203, 174, 122),
        # Cool tone for the spy's conversions: the one thing on the board that
        # is neither a quiet move nor a capture, so it gets its own hue.
        "convert": (86, 132, 130),
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
        # Panel lists and board coordinates. All in the same serif: pygame's
        # built-in face renders unevenly at these sizes and looked like a
        # different program next to the rest of the interface.
        self.list_font = self._load_font(23)
        self.label_font = self._load_font(20)

        self.menu_background = self._load_menu_background()
        # Pieces are redrawn every frame; rendering the glyph and its outline
        # each time is wasteful, so cache one surface per (type, colour, size).
        self._piece_cache = {}
        self._piece_fonts = {}
        # Set once per frame so buttons can light up under the pointer without
        # every caller having to thread the mouse position through.
        self._mouse = (-1, -1)

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

    def _piece_font(self, size: Optional[int]) -> pygame.font.Font:
        """The glyph font at a given size, cached. None means the board size."""
        if size is None:
            return self.font
        font = self._piece_fonts.get(size)
        if font is None:
            font = self._piece_fonts[size] = self._load_font(size)
        return font

    def _piece_surface(
        self, piece: Piece, size: Optional[int] = None
    ) -> pygame.Surface:
        key = (piece.type, piece.is_white, size)
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
        font = self._piece_font(size)
        thickness = max(1, round(font.get_height() / 40))

        body = font.render(piece.glyph, True, fill)
        edge = font.render(piece.glyph, True, outline)

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

        if piece.type == PieceType.SPY:
            self._add_hat(surface, fill, outline)

        self._piece_cache[key] = surface
        return surface

    def _flat_piece_surface(
        self, piece_type: PieceType, is_white: bool, size: int
    ) -> pygame.Surface:
        """A single-colour silhouette, for lists rather than the board.

        The board treatment -- dark fill, light outline -- turns into a hollow
        ring on the near-black panel, so pieces out of play are drawn as flat
        shapes in two panel tones instead.
        """
        key = ("flat", piece_type, is_white, size)
        cached = self._piece_cache.get(key)
        if cached is not None:
            return cached

        colour = (232, 222, 202) if is_white else (132, 110, 86)
        piece = Piece(piece_type, is_white)
        surface = self._piece_font(size).render(piece.glyph, True, colour).copy()
        if piece_type == PieceType.SPY:
            self._add_hat(surface, colour, colour)

        self._piece_cache[key] = surface
        return surface

    @staticmethod
    def _add_hat(surface: pygame.Surface, fill, outline):
        """Turn a pawn silhouette into the spy by pulling a hat over its head.

        Drawn relative to the glyph's own ink, so it lands correctly at any
        font size.
        """
        box = surface.get_bounding_rect()
        if not box.height:
            return

        brim_y = box.top + int(box.height * 0.24)
        brim_w, brim_h = int(box.width * 0.98), max(5, int(box.height * 0.11))
        crown_w, crown_h = int(box.width * 0.46), int(box.height * 0.16)

        # The outline pass is a slightly larger copy of the same two shapes, so
        # the hat carries the same edge as the piece under it.
        for colour, grow in ((outline, max(2, brim_h // 3)), (fill, 0)):
            crown = pygame.Rect(0, 0, crown_w + grow * 2, crown_h + grow)
            crown.midbottom = (box.centerx, brim_y + grow)
            pygame.draw.rect(surface, colour, crown, border_radius=max(2, crown_w // 4))
            brim = pygame.Rect(0, 0, brim_w + grow * 2, brim_h + grow * 2)
            brim.center = (box.centerx, brim_y)
            pygame.draw.ellipse(surface, colour, brim)

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

    def game_over_rects(self) -> Dict[str, pygame.Rect]:
        """Rematch and menu buttons on the game-over banner."""
        width, height, gap = 196, 52, 18
        x = self.board_size // 2 - (width * 2 + gap) // 2
        y = self.board_size // 2 + 8
        return {
            "rematch": pygame.Rect(x, y, width, height),
            "menu": pygame.Rect(x + width + gap, y, width, height),
        }

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

    def _draw_title(
        self, screen: pygame.Surface, text: str, centre_y: int, light: bool = False
    ):
        """Serif title with a soft drop shadow.

        `light` picks cream lettering for dark backdrops. The previous version
        offset a light copy behind dark lettering on every screen, which over
        the dimmed rules overlay read as a misprint rather than an emboss.
        """
        centre_x = self.screen_width // 2
        body_colour = (247, 240, 226) if light else (38, 27, 20)
        shadow_colour = (18, 12, 8) if light else (86, 62, 40)

        shadow = self.title_font.render(text, True, shadow_colour)
        shadow.set_alpha(110)
        # Two offsets, so the shadow falls off instead of ending in a hard edge.
        for dx, dy in ((2, 3), (4, 6)):
            screen.blit(shadow, shadow.get_rect(center=(centre_x + dx, centre_y + dy)))

        body = self.title_font.render(text, True, body_colour)
        screen.blit(body, body.get_rect(center=(centre_x, centre_y)))

    def _draw_button(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        colour=None,
        text_colour=None,
        enabled: bool = True,
    ):
        """Draw a button, lit up while the pointer is over it.

        Every clickable thing goes through here, so hover feedback is uniform
        and nothing looks dead under the cursor.
        """
        hovered = enabled and rect.collidepoint(self._mouse)
        base = colour or self.COLORS["button"]
        if hovered:
            base = self.COLORS["button_hover"] if colour is None else _lighten(base, 22)

        pygame.draw.rect(screen, base, rect, border_radius=6)
        if hovered:
            pygame.draw.rect(
                screen, self.COLORS["accent"], rect, width=2, border_radius=6
            )
        text = font.render(label, True, text_colour or self.COLORS["white_piece"])
        screen.blit(text, text.get_rect(center=rect.center))

    def render_menu(self, screen: pygame.Surface, difficulty: str = "medium"):
        self._mouse = pygame.mouse.get_pos()
        self._draw_menu_background(screen)
        rects = self.menu_rects()

        # High enough that the tagline clears the first button.
        title_y = self.screen_height // 5
        self._draw_title(screen, "Chess 2", title_y)
        tagline = self.body_font.render(TAGLINE, True, (96, 74, 54))
        screen.blit(
            tagline, tagline.get_rect(center=(self.screen_width // 2, title_y + 64))
        )

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
        self._mouse = pygame.mouse.get_pos()
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

        self._draw_title(screen, "House Rules", 62, light=True)

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
        anim: Optional["MoveAnimation"] = None,
        effect: Optional["SquareEffect"] = None,
        notice: Optional["Notice"] = None,
    ):
        self._mouse = pygame.mouse.get_pos()
        # Whether the board is waiting on this player, which decides if squares
        # light up under the pointer.
        interactive = (
            (game_mode == "local" or state.is_white_turn)
            and not thinking
            and not state.game_over
            and not promoting
            and not showing_rules
        )
        self._draw_board(screen)
        self._draw_highlights(screen, state, interactive)
        self._draw_labels(screen)
        self._draw_pieces(screen, state, anim)
        self._draw_effect(screen, effect)
        self._draw_panel(screen, state, game_mode, difficulty, thinking)
        self._draw_notice(screen, notice)
        if showing_rules:
            self._draw_rules_overlay(screen)
        elif promoting:
            self._draw_promotion(screen, state)
        elif state.game_over:
            self._draw_game_over(screen, state)

    def _draw_notice(self, screen: pygame.Surface, notice: Optional["Notice"]):
        """A banner across the top of the board, for a rule that just fired."""
        if notice is None or notice.done:
            return

        text = self.info_font.render(notice.text, True, self.COLORS["accent"])
        card = text.get_rect().inflate(56, 28)
        card.center = (self.board_size // 2, 54)

        panel = pygame.Surface(card.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (22, 16, 13, 236), panel.get_rect(), border_radius=8)
        # Fade out at the end rather than blinking off.
        alpha = int(255 * min(1.0, (1 - notice.progress) * 5))
        panel.set_alpha(alpha)
        text.set_alpha(alpha)
        screen.blit(panel, card.topleft)
        screen.blit(text, text.get_rect(center=card.center))

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
            self.body_font,
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
            # Animate the ellipsis: on the harder settings the search takes long
            # enough that a static line looks like the game has frozen.
            status = "Computer is thinking" + "." * (
                1 + (pygame.time.get_ticks() // 350) % 3
            )
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

        width = PANEL_WIDTH - 48
        pygame.draw.line(
            screen, self.COLORS["button_disabled"], (x, y), (x + width, y)
        )
        y += 16

        y = self._draw_captured(screen, state, x, y, width)
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
            enabled=undo_enabled,
        )
        self._draw_button(screen, buttons["menu"], "Main Menu", self.info_font)

    def _draw_captured(
        self, screen: pygame.Surface, state: GameState, x: int, y: int, width: int
    ) -> int:
        """Pieces out of play, and who is ahead on material.

        Nothing is drawn until the first piece falls: an empty tray would just
        push the house-rules hints down for no reason.
        """
        if not state.captured:
            return y

        balance = state.material_balance()
        heading = self.list_font.render("Out of play", True, self.COLORS["accent"])
        screen.blit(heading, (x, y))
        if balance:
            leader = "White" if balance > 0 else "Black"
            badge = self.list_font.render(
                f"{leader} +{abs(balance) / 100:.1f}", True, self.COLORS["panel_text"]
            )
            screen.blit(badge, (x + width - badge.get_width(), y))
        y += 30

        for is_white in (False, True):
            lost = state.losses(is_white)
            if not lost:
                continue
            step = min(22, max(12, (width - 24) // len(lost)))
            for i, piece_type in enumerate(lost):
                surface = self._flat_piece_surface(piece_type, is_white, 30)
                screen.blit(
                    surface, surface.get_rect(center=(x + 11 + i * step, y + 12))
                )
            y += 28

        pygame.draw.line(
            screen, self.COLORS["button_disabled"], (x, y + 6), (x + width, y + 6)
        )
        return y + 22

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
                lines = self._wrap(hint, self.list_font, PANEL_WIDTH - 66)
                screen.blit(
                    self.list_font.render("•", True, self.COLORS["accent"]), (x, y)
                )
                for line in lines:
                    screen.blit(
                        self.list_font.render(
                            line, True, self.COLORS["panel_muted"]
                        ),
                        (x + 16, y),
                    )
                    y += 24
                y += 6
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
        # not line up. The move just played is picked out in the accent colour
        # so it can be found at a glance.
        latest = len(state.move_log) - 1
        shown = rows[-max_rows:]
        first = len(rows) - len(shown)
        for row_index, (number, white, black) in enumerate(shown, first):
            screen.blit(
                self.list_font.render(number, True, self.COLORS["panel_muted"]), (x, y)
            )
            for ply, text, offset in ((0, white, 38), (1, black, 142)):
                if not text:
                    continue
                current = row_index * 2 + ply == latest
                colour = self.COLORS["accent"] if current else self.COLORS["panel_text"]
                screen.blit(self.list_font.render(text, True, colour), (x + offset, y))
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
            hovered = rect.collidepoint(self._mouse)
            pygame.draw.rect(
                screen,
                (250, 236, 206) if hovered else self.COLORS["light_square"],
                rect,
                border_radius=8,
            )
            if hovered:
                pygame.draw.rect(
                    screen, self.COLORS["accent"], rect, width=3, border_radius=8
                )
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

        # A short falloff along the panel edge, so the panel reads as sitting
        # above the board rather than butting up against it.
        shadow = pygame.Surface((10, self.board_size), pygame.SRCALPHA)
        for i in range(10):
            pygame.draw.line(
                shadow, (30, 20, 12, 60 - i * 6), (9 - i, 0), (9 - i, self.board_size)
            )
        screen.blit(shadow, (self.board_size - 10, 0))

    def _draw_highlights(
        self, screen: pygame.Surface, state: GameState, interactive: bool = False
    ):
        if state.last_move:
            self._draw_last_move_highlight(screen, state.last_move)

        self._draw_check_highlight(screen, state)

        if interactive:
            self._draw_hover_highlight(screen, state)

        if state.selected_piece:
            self._draw_selected_highlight(screen, state.selected_piece)
            self._draw_legal_moves(screen, state)

    def _outline_square(
        self, screen: pygame.Surface, pos: Tuple[int, int], colour, alpha, width=3
    ):
        surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        pygame.draw.rect(
            surface,
            (*colour, alpha),
            (0, 0, self.square_size, self.square_size),
            width=width,
        )
        screen.blit(surface, (pos[1] * self.square_size, pos[0] * self.square_size))

    def _draw_hover_highlight(self, screen: pygame.Surface, state: GameState):
        """Ring the square under the pointer.

        Bright on a square the selected piece can reach, soft on a piece that is
        available to pick up. An outline rather than a tint: a wash light enough
        not to muddy the wood was invisible on the pale squares.
        """
        square = self.square_at(self._mouse)
        if square is None:
            return
        if square in state.possible_moves:
            self._outline_square(screen, square, (252, 244, 224), 225, width=4)
        elif state.selected_piece is None:
            piece = state.board.get_piece(square)
            if piece is not None and piece.is_white == state.is_white_turn:
                self._outline_square(screen, square, (252, 244, 224), 130)

    def _tint_square(self, screen: pygame.Surface, pos: Tuple[int, int], colour, alpha):
        surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        surface.fill((*colour, alpha))
        screen.blit(surface, (pos[1] * self.square_size, pos[0] * self.square_size))

    def _draw_selected_highlight(self, screen: pygame.Surface, pos: Tuple[int, int]):
        self._tint_square(screen, pos, self.COLORS["selected"], 130)

    def _draw_check_highlight(self, screen: pygame.Surface, state: GameState):
        """Mark the king's square when it is in check.

        Left on after checkmate, where it points at the king that could not get
        out of it -- the side to move is the mated one.
        """
        if not state.board.is_in_check(state.is_white_turn):
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
        """A dot marks a quiet move, a ring a capture.

        A spy takes nothing -- it flips the piece and dies -- so its targets get
        a double ring in the conversion colour instead. Otherwise the game's one
        genuinely new mechanic looks exactly like an ordinary capture.
        """
        selected = (
            state.board.get_piece(state.selected_piece)
            if state.selected_piece
            else None
        )
        converting = selected is not None and selected.type == PieceType.SPY

        radius = self.square_size // 2 - 4
        for move in state.possible_moves:
            overlay = pygame.Surface(
                (self.square_size, self.square_size), pygame.SRCALPHA
            )
            local = (self.square_size // 2, self.square_size // 2)
            occupied = state.board.get_piece(move) is not None
            if occupied and converting:
                for r, alpha in ((radius, 190), (radius - 9, 130)):
                    pygame.draw.circle(
                        overlay, (*self.COLORS["convert"], alpha), local, r, width=4
                    )
            elif occupied:
                pygame.draw.circle(
                    overlay,
                    (*self.COLORS["legal_moves"], 120),
                    local,
                    radius,
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

    def _draw_effect(self, screen: pygame.Surface, effect: Optional["SquareEffect"]):
        """A ring bursting out of a square: the spy's conversion landing."""
        if effect is None or effect.done:
            return
        progress = effect.progress
        centre = (
            effect.pos[1] * self.square_size + self.square_size // 2,
            effect.pos[0] * self.square_size + self.square_size // 2,
        )
        size = self.square_size * 2
        overlay = pygame.Surface((size, size), pygame.SRCALPHA)
        for delay in (0.0, 0.22):
            ring = progress - delay
            if ring <= 0:
                continue
            radius = int(self.square_size * (0.18 + 0.55 * ring))
            alpha = int(210 * (1 - ring) ** 2)
            pygame.draw.circle(
                overlay,
                (*self.COLORS["convert"], alpha),
                (size // 2, size // 2),
                radius,
                width=max(2, int(6 * (1 - ring))),
            )
        screen.blit(overlay, overlay.get_rect(center=centre))

    def _draw_last_move_highlight(
        self, screen: pygame.Surface, last_move: Tuple[Tuple[int, int], Tuple[int, int]]
    ):
        for pos in last_move:
            surface = pygame.Surface(
                (self.square_size, self.square_size), pygame.SRCALPHA
            )
            surface.fill((*self.COLORS["last_move"], 100))
            screen.blit(surface, (pos[1] * self.square_size, pos[0] * self.square_size))

    def _draw_pieces(
        self,
        screen: pygame.Surface,
        state: GameState,
        anim: Optional["MoveAnimation"] = None,
    ):
        # A piece mid-slide is drawn at its interpolated position instead of on
        # the square it has already legally arrived at.
        arriving = anim.destinations() if anim and not anim.done else frozenset()

        for row in range(8):
            for col in range(8):
                piece = state.board.get_piece((row, col))
                if (row, col) in arriving:
                    continue
                if piece and (not state.dragging or (row, col) != state.selected_piece):
                    self._draw_piece(screen, piece, (row, col))

        if arriving:
            self._draw_animated_pieces(screen, anim)

        if state.dragging and state.selected_piece:
            self._draw_dragged_piece(screen, state)

    def _draw_animated_pieces(self, screen: pygame.Surface, anim: "MoveAnimation"):
        eased = anim.eased_progress()
        for piece, start, end in anim.segments:
            surface = self._piece_surface(piece)
            centre = tuple(
                int(
                    (start[axis] + (end[axis] - start[axis]) * eased) * self.square_size
                    + self.square_size // 2
                )
                for axis in (1, 0)
            )
            screen.blit(surface, surface.get_rect(center=centre))

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

    def _square_label_colour(self, row: int, col: int):
        """Ink for a coordinate: the colour the square underneath is not."""
        return (
            self.COLORS["label_on_light"]
            if (row + col) % 2 == 0
            else self.COLORS["label_on_dark"]
        )

    def _draw_labels(self, screen: pygame.Surface):
        """Files along the bottom rank, ranks up the right-hand file.

        Previously drawn in pygame's built-in font at 16px in a flat grey, which
        was illegible on the dark squares and only half-visible on the light
        ones.
        """
        pad = 6
        for i in range(8):
            file_label = self.label_font.render(
                chr(ord("a") + i), True, self._square_label_colour(7, i)
            )
            screen.blit(
                file_label,
                file_label.get_rect(
                    bottomright=(
                        (i + 1) * self.square_size - pad,
                        self.board_size - pad + 2,
                    )
                ),
            )
            rank_label = self.label_font.render(
                str(8 - i), True, self._square_label_colour(i, 7)
            )
            screen.blit(
                rank_label,
                rank_label.get_rect(
                    topright=(
                        self.board_size - pad,
                        i * self.square_size + pad - 2,
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
        centre_y = self.board_size // 2

        banner = pygame.Surface((self.board_size, 220), pygame.SRCALPHA)
        banner.fill((20, 15, 12, 208))
        screen.blit(banner, (0, centre_y - 110))

        text = self.game_over_font.render(
            texts[state.game_result], True, self.COLORS["panel_text"]
        )
        screen.blit(text, text.get_rect(center=(centre_x, centre_y - 56)))

        buttons = self.game_over_rects()
        self._draw_button(screen, buttons["rematch"], "Rematch", self.info_font)
        self._draw_button(screen, buttons["menu"], "Main Menu", self.info_font)


class MoveAnimation:
    """Slides the pieces of a move from their old squares to their new ones.

    Purely cosmetic: the move is already applied to the board, this only decides
    where the pieces are drawn while they catch up. Without it the computer's
    reply simply teleports and is easy to miss.
    """

    DURATION_MS = 150

    def __init__(self, segments, duration: int = DURATION_MS):
        # [(piece, from_square, to_square)] -- more than one for castling.
        self.segments = segments
        self.duration = duration
        self.start_ms = pygame.time.get_ticks()

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, (pygame.time.get_ticks() - self.start_ms) / self.duration)

    @property
    def done(self) -> bool:
        return not self.segments or self.progress >= 1.0

    def eased_progress(self) -> float:
        """Ease out, so the piece leaves quickly and settles onto the square."""
        return 1 - (1 - self.progress) ** 3

    def destinations(self) -> Set[Tuple[int, int]]:
        return {end for _, _, end in self.segments}


class _Timed:
    """Shared clock for the short-lived visual flourishes."""

    DURATION_MS = 500

    def __init__(self, duration: Optional[int] = None):
        self.duration = self.DURATION_MS if duration is None else duration
        self.start_ms = pygame.time.get_ticks()

    @property
    def progress(self) -> float:
        return min(1.0, (pygame.time.get_ticks() - self.start_ms) / self.duration)

    @property
    def done(self) -> bool:
        return self.progress >= 1.0


class SquareEffect(_Timed):
    """A short burst centred on one square, used for spy conversions."""

    DURATION_MS = 520

    def __init__(self, pos: Tuple[int, int], duration: Optional[int] = None):
        super().__init__(duration)
        self.pos = pos


class Notice(_Timed):
    """A line of text shown briefly over the board, then faded out."""

    DURATION_MS = 2600

    def __init__(self, text: str, duration: Optional[int] = None):
        super().__init__(duration)
        self.text = text
