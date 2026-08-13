# Chess 2

<p align="center">
    <img width="400" height="400" src="demo.gif" alt="Demo">
</p>

The last patch for chess was probably shipped over 100 years ago, so it's time for some improvements:

* Knights can now jump in all directions, because real horses stopped using L-shaped movement centuries ago.
* Stalemate is no longer a draw. If you can't move, that's a you problem and your opponent gets another turn.
* *Ėń pãşšãñţ*  has been disabled, so nobody ever has to spell it again.
* Added a new piece on h2/h7, the spy. Moves in sneaky L-shapes, but converts enemy pieces instead of capturing them. Can only convert once and dies in the process.
* Bishops can no longer capture queens. Just doesn't seem right.
* Fixed a bug where computers were better at chess than humans.
* Pawns can now move and capture both forwards and diagonally, like normal people. But they still can't move backwards. That would be ridiculous.


## Play

Play in your browser at **[chesstwo.pages.dev](https://chesstwo.pages.dev/)** — no install needed.
The first load takes a moment while the Python runtime downloads.

Pick Easy, Medium or Hard for the computer opponent. Easy is the original
move-at-random opponent; Medium and Hard actually search ahead. Take back a move
with the Undo button or the `U` key. After a checkmate, start again with the
Rematch button or the `R` key.

The panel beside the board keeps the move list, the pieces that are out of play
and who is ahead on material. The spy is the pawn in the hat on h2/h7; the
squares it can convert are ringed in teal rather than marked as captures.

## Installation

### Option 1: Executables

Executables for macOS and Windows can be found under [releases](https://github.com/amagrabi/chess2/releases).

### Option 2: Python

Create and activate a virtual environment, for example via [uv](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uv venv
source .venv/bin/activate
```

Install dependencies in editable mode:
```sh
uv pip install -e .
```

Start game:
```sh
chess2
```

### Option 3: Docker (experimental)

Setup is still error-prone, because pygame and Docker aren't best friends.

Requirements: Install [XQuartz](https://www.xquartz.org/) (Mac) or [Xming](https://sourceforge.net/projects/xming/) (Windows). 

Build and start the Docker container:
```sh
docker-compose build
docker-compose up
```

## Development

Install dev dependencies:
```sh
uv pip install -e ".[dev]"
```

Install pre-commit hooks for auto-formatting:
```sh
pre-commit install
```

Run tests:
```sh
pytest tests/
```

Creating macOS/Windows executables into `/dist` for releases:
```sh
pyinstaller chess2.spec
```
