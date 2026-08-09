"""Computer opponents for Chess 2.

The search runs inside the browser's event loop (pygbag/WebAssembly), so it
yields periodically instead of blocking — otherwise the page freezes and the
board stops repainting while the computer thinks.

Piece values are tuned for Chess 2's rules rather than normal chess:
knights jump in every direction so they are worth more, bishops cannot capture
queens so they are worth less, and the spy is a one-shot piece that swings
material by twice its target's value.
"""

import asyncio
import random
from typing import List, Optional, Tuple

from core.board import ChessBoard
from core.piece import PieceType

EASY = "easy"
MEDIUM = "medium"
HARD = "hard"

DIFFICULTY_DEPTH = {EASY: 0, MEDIUM: 2, HARD: 3}

PIECE_VALUES = {
    PieceType.PAWN: 100,
    PieceType.KNIGHT: 380,  # jumps in all directions here, so worth more
    PieceType.BISHOP: 290,  # cannot capture queens, so worth less
    PieceType.ROOK: 500,
    PieceType.QUEEN: 900,
    PieceType.SPY: 350,
    PieceType.KING: 20000,
}

# Small nudge toward the centre, applied to every piece.
CENTRE_BONUS = [
    [0, 0, 1, 2, 2, 1, 0, 0],
    [0, 1, 2, 3, 3, 2, 1, 0],
    [1, 2, 3, 4, 4, 3, 2, 1],
    [2, 3, 4, 5, 5, 4, 3, 2],
    [2, 3, 4, 5, 5, 4, 3, 2],
    [1, 2, 3, 4, 4, 3, 2, 1],
    [0, 1, 2, 3, 3, 2, 1, 0],
    [0, 0, 1, 2, 2, 1, 0, 0],
]

MATE_SCORE = 100_000

Move = Tuple[Tuple[int, int], Tuple[int, int]]


def evaluate(board: ChessBoard, is_white: bool) -> int:
    """Score the position from is_white's point of view, in centipawns."""
    score = 0
    for r in range(8):
        for c in range(8):
            piece = board.board[r][c]
            if piece is None:
                continue
            value = PIECE_VALUES[piece.type] + CENTRE_BONUS[r][c]
            if piece.type == PieceType.PAWN:
                # Reward pushing pawns; white advances toward row 0.
                value += (6 - r) * 4 if piece.is_white else (r - 1) * 4
            score += value if piece.is_white == is_white else -value
    return score


def _move_order_key(board: ChessBoard, move: Move) -> int:
    """Search captures first so alpha-beta prunes more."""
    target = board.board[move[1][0]][move[1][1]]
    if target is None:
        return 0
    return -PIECE_VALUES[target.type]


class _Search:
    def __init__(self, board: ChessBoard, yield_every: int = 900):
        self.board = board
        self.nodes = 0
        self.yield_every = yield_every

    async def _maybe_yield(self):
        self.nodes += 1
        if self.nodes % self.yield_every == 0:
            # Hand control back so the browser can paint a frame.
            await asyncio.sleep(0)

    async def negamax(self, depth: int, is_white: bool, alpha: int, beta: int) -> int:
        await self._maybe_yield()

        # Evaluate before generating moves: leaf nodes vastly outnumber interior
        # ones, and generating a full legal move list there (just to spot mate)
        # dominated the search cost. Mates are still found one ply higher up.
        if depth == 0:
            return evaluate(self.board, is_white)

        moves = self.board.legal_moves_for(is_white)
        if not moves:
            if self.board.is_in_check(is_white):
                return -MATE_SCORE - depth  # prefer mates that arrive sooner
            # Chess 2 quirk: stalemate is not a draw, the opponent simply moves
            # again. Treat it as a bad but survivable position.
            return -50

        moves.sort(key=lambda m: _move_order_key(self.board, m))

        best = -MATE_SCORE * 2
        for start, end in moves:
            snap = self.board.snapshot()
            self.board.apply_move(start, end)
            score = -await self.negamax(depth - 1, not is_white, -beta, -alpha)
            self.board.restore(snap)

            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best

    async def best_move(self, depth: int, is_white: bool) -> Optional[Move]:
        moves = self.board.legal_moves_for(is_white)
        if not moves:
            return None

        moves.sort(key=lambda m: _move_order_key(self.board, m))

        alpha = -MATE_SCORE * 2
        best_moves: List[Move] = []
        for start, end in moves:
            snap = self.board.snapshot()
            self.board.apply_move(start, end)
            score = -await self.negamax(depth - 1, not is_white, -MATE_SCORE * 2, -alpha)
            self.board.restore(snap)

            if not best_moves or score > alpha:
                alpha = score
                best_moves = [(start, end)]
            elif score == alpha:
                best_moves.append((start, end))

        # Pick randomly between equally good moves so games are not identical.
        return random.choice(best_moves)


async def choose_move(
    board: ChessBoard, is_white: bool, difficulty: str = MEDIUM
) -> Optional[Move]:
    """Pick a move for `is_white`, yielding to the event loop while thinking."""
    moves = board.legal_moves_for(is_white)
    if not moves:
        return None

    depth = DIFFICULTY_DEPTH.get(difficulty, 2)
    if depth <= 0:
        # The original opponent, kept as the joke difficulty.
        return random.choice(moves)

    return await _Search(board).best_move(depth, is_white)
