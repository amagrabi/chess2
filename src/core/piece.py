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
        """
        glyphs = {
            PieceType.PAWN: "♟",
            PieceType.KNIGHT: "♞",
            PieceType.BISHOP: "♝",
            PieceType.ROOK: "♜",
            PieceType.QUEEN: "♛",
            PieceType.KING: "♚",
            PieceType.SPY: "⌖",
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
