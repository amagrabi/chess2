from dataclasses import dataclass
from enum import Enum, auto


class PieceType(Enum):
    PAWN = auto()
    KNIGHT = auto()
    BISHOP = auto()
    ROOK = auto()
    QUEEN = auto()
    KING = auto()
    SPY = auto()


# Rough worth of each piece in centipawns, tuned for Chess 2 rather than normal
# chess: knights jump in every direction so they are worth more, bishops cannot
# capture queens so they are worth less, and the spy swings material by twice
# its target's value. Shared by the AI search and the material counter in the
# panel, so both agree on who is ahead. The king is deliberately absent -- it is
# never material, and the search adds its own sentinel value.
MATERIAL_VALUES = {
    PieceType.PAWN: 100,
    PieceType.KNIGHT: 380,
    PieceType.BISHOP: 290,
    PieceType.ROOK: 500,
    PieceType.QUEEN: 900,
    PieceType.SPY: 350,
}


@dataclass
class Piece:
    type: PieceType
    is_white: bool
    has_moved: bool = False

    @property
    def glyph(self) -> str:
        """Solid silhouette used for drawing, for both colours.

        The outlined white glyphs (♙♘♗) render as thin, washed-out shapes; a
        filled silhouette tinted white and given a dark outline reads far
        better on the board.

        The spy borrows the pawn silhouette -- Unicode has no spy, and the
        crosshair used before read as a UI marker rather than a piece. The
        renderer stamps a hat on top of it, which is what tells the two apart.
        """
        glyphs = {
            PieceType.PAWN: "♟",
            PieceType.KNIGHT: "♞",
            PieceType.BISHOP: "♝",
            PieceType.ROOK: "♜",
            PieceType.QUEEN: "♛",
            PieceType.KING: "♚",
            PieceType.SPY: "♟",
        }
        return glyphs[self.type]

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
