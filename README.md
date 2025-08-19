# MemoPad TUI

Simple terminal memo pad that lets you curate notes.  Notes can be marked as
favourites, pinned to the top, reordered and the view can be zoomed in or out.
All interaction happens through the keyboard making it a compact personal
scratch pad.

## Installation

The application only depends on the Python standard library and `pytest` for
running the test-suite.  On Windows, `windows-curses` is required in order to
provide the `curses` interface.  Install everything via::

```bash
pip install -r requirements.txt
```

## Usage

Run the interactive interface with::

```bash
python memopad.py
```

Keyboard shortcuts:

| Keys       | Action                         |
|------------|--------------------------------|
| `Alt+o`    | Toggle favourite star          |
| `Alt+p`    | Toggle pin (pinned notes stay at top) |
| `Alt+w`    | Move selected note up          |
| `Alt+s`    | Move selected note down        |
| `Alt+a`    | Move note left (decrease indent) |
| `Alt+d`    | Move note right (increase indent) |
| `Ctrl+w`   | Zoom in                        |
| `Ctrl+s`   | Zoom out                       |
| `Ctrl+q`   | Save and exit                  |

## Code overview

`memopad.py` exposes a `MemoPad` class containing the application logic:

- `load()` / `save()` handle persistence of the memo pad file.
- `toggle_favorite(index)` and `toggle_pin(index)` update note metadata.
- `move_up(index)` / `move_down(index)` reorder notes while keeping pinned
  items grouped.
- `move_left(index)` / `move_right(index)` adjust note indentation.
- `zoom_in()` / `zoom_out()` change the rendering zoom level.
- `run()` launches the curses based user interface.

## Testing

Automated tests cover the behaviour of the `MemoPad` methods.  Execute them
with::

```bash
pytest
```
