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


## Installation

Create a virtual environment and install dependencies in editable mode:
```sh
pip install -e .
```

Start game:
```sh
chess2
```

You play against a randomizing AI. Press `Esc` to restart the game.

## Development

Install dev dependencies:
```sh
pip install -e ".[dev]"
```

Run tests:
```sh
pytest tests/
```

Creating Mac/Windows executables into `/dist` for releases:
```sh
pyinstaller chess2.spec
```
