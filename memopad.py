# Quickstart:
#   pip install wcwidth
#   pip install windows-curses  # on Windows only
#   python memopad.py
"""Curses-based memo pad application.

This single-file program implements a tiny memo pad for the terminal. Notes can
be pinned, favourited, reordered and indented.  The interface uses only the
standard :mod:`curses` module and the third party :mod:`wcwidth` library for
Unicode width calculations.
"""
from __future__ import annotations

import curses
import json
import locale
import os
from dataclasses import dataclass
from typing import Dict, List

# ``wcwidth`` provides accurate cell width calculations for Unicode.  The
# package may not be installed in minimal test environments, so a small
# fallback is provided.  Installing ``wcwidth`` is still recommended for full
# accuracy.
try:  # pragma: no cover - exercised indirectly in tests
    from wcwidth import wcwidth  # type: ignore
except Exception:  # pragma: no cover
    import unicodedata

    def wcwidth(ch: str) -> int:
        """Best-effort width calculation used when :mod:`wcwidth` is missing."""
        if unicodedata.combining(ch):
            return 0
        if unicodedata.east_asian_width(ch) in "WF":
            return 2
        return 1

# Ensure the user's locale so curses works with UTF-8 terminals.
locale.setlocale(locale.LC_ALL, "")

MAX_INDENT = 8


def display_width(s: str) -> int:
    """Return the display width of *s* using :func:`wcwidth`.

    Negative widths from ``wcwidth`` are treated as zero.
    """
    return sum(max(wcwidth(ch), 0) for ch in s)


def clip_to_cells(text: str, max_cells: int) -> str:
    """Clip ``text`` so it occupies at most ``max_cells`` display cells."""
    width = 0
    result_chars: List[str] = []
    for ch in text:
        w = max(wcwidth(ch), 0)
        if width + w > max_cells:
            break
        result_chars.append(ch)
        width += w
    return "".join(result_chars)


@dataclass
class Note:
    """A single note entry."""

    text: str
    favorite: bool = False
    pinned: bool = False
    indent: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "text": self.text,
            "pinned": self.pinned,
            "favorite": self.favorite,
            "indent": self.indent,
        }


class MemoPad:
    """Manage notes and provide a curses interface."""

    def __init__(self, path: str = "memopad.json") -> None:
        self.path = path
        self.notes: List[Note] = []
        self.zoom = 0  # vertical spacing modifier
        self.selected = 0
        self.scroll = 0
        self.dirty = False
        self.load(path)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self, path: str = "memopad.json") -> None:
        """Load pad state from *path*.

        ``path`` defaults to ``self.path`` if the caller did not supply a
        value. Missing files are created with a few sample notes. Invalid JSON
        results in an empty pad and ``zoom`` of 0.
        """
        if path == "memopad.json" and getattr(self, "path", path) != "memopad.json":
            path = self.path
        self.path = path
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self.notes = [
                Note("Welcome to MemoPad"),
                Note("Pinned: Read me first", pinned=True),
                Note("★ Sample favorite item", favorite=True, indent=1),
            ]
            self.zoom = 0
            self.save(path)
            self.dirty = False
            return
        except json.JSONDecodeError:
            self.notes = []
            self.zoom = 0
            self.dirty = False
            return

        items = data.get("notes", []) if isinstance(data, dict) else []
        self.notes = []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", ""))
            pinned = bool(item.get("pinned", False))
            favorite = bool(item.get("favorite", False))
            indent = int(item.get("indent", 0))
            indent = max(0, min(MAX_INDENT, indent))
            self.notes.append(Note(text, favorite=favorite, pinned=pinned, indent=indent))
        self.zoom = int(data.get("zoom", 0)) if isinstance(data, dict) else 0
        self.dirty = False

    def save(self, path: str = "memopad.json") -> None:
        """Save pad state atomically to *path*.

        ``path`` defaults to :attr:`self.path` when omitted by the caller.
        """
        if path == "memopad.json" and self.path != "memopad.json":
            path = self.path
        self.path = path
        tmp = path + ".tmp"
        data = {"notes": [n.to_dict() for n in self.notes], "zoom": self.zoom}
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        self.dirty = False

    # ------------------------------------------------------------------
    # Operations on notes
    # ------------------------------------------------------------------
    def toggle_favorite(self, index: int) -> None:
        self.notes[index].favorite = not self.notes[index].favorite
        self.dirty = True

    def toggle_pin(self, index: int) -> None:
        note = self.notes.pop(index)
        note.pinned = not note.pinned
        if note.pinned:
            pos = max([i for i, n in enumerate(self.notes) if n.pinned] + [-1]) + 1
            self.notes.insert(pos, note)
            self.selected = pos
        else:
            pos = max([i for i, n in enumerate(self.notes) if n.pinned] + [-1]) + 1
            self.notes.insert(pos, note)
            self.selected = pos
        self.dirty = True

    def move_up(self, index: int) -> int:
        if index > 0 and self.notes[index].pinned == self.notes[index - 1].pinned:
            self.notes[index - 1], self.notes[index] = self.notes[index], self.notes[index - 1]
            self.dirty = True
            return index - 1
        return index

    def move_down(self, index: int) -> int:
        if index < len(self.notes) - 1 and self.notes[index].pinned == self.notes[index + 1].pinned:
            self.notes[index + 1], self.notes[index] = self.notes[index], self.notes[index + 1]
            self.dirty = True
            return index + 1
        return index

    def move_left(self, index: int) -> None:
        note = self.notes[index]
        note.indent = max(0, note.indent - 1)
        self.dirty = True

    def move_right(self, index: int) -> None:
        note = self.notes[index]
        note.indent = min(MAX_INDENT, note.indent + 1)
        self.dirty = True

    def zoom_in(self) -> None:
        self.zoom = min(self.zoom + 1, 8)
        self.dirty = True

    def zoom_out(self) -> None:
        self.zoom = max(self.zoom - 1, 0)
        self.dirty = True

    # ------------------------------------------------------------------
    # Curses UI helpers
    # ------------------------------------------------------------------
    def run(self) -> None:
        curses.wrapper(self._curses_main)

    def _ensure_visible(self, height: int) -> None:
        row = self.selected * (1 + self.zoom)
        if row < self.scroll:
            self.scroll = row
        elif row >= self.scroll + height:
            self.scroll = row - height + (1 + self.zoom)

    def _format_note(self, note: Note) -> str:
        indent = "  " * note.indent
        pin = "📌" if note.pinned else " "
        star = "★" if note.favorite else "☆"
        return f"{indent}{pin} {star} {note.text}"

    def _draw_header(self, win: curses.window, w: int) -> None:
        header = (
            "MemoPad — Alt[o]=★ Alt[p]=📌 Alt[w/s]=↑/↓ Alt[a/d]=←/→ "
            "Ctrl[w/s]=Zoom ± Ctrl[q]=Save+Quit"
        )
        win.addstr(0, 0, clip_to_cells(header, w - 1))

    def _draw_footer(self, win: curses.window, h: int, w: int) -> None:
        pinned = sum(n.pinned for n in self.notes)
        fav = sum(n.favorite for n in self.notes)
        footer = f"{self.path} | {len(self.notes)} notes ({pinned} pinned, {fav} favorites) | Zoom: {self.zoom}"
        win.addstr(h - 1, 0, clip_to_cells(footer, w - 1))

    def _draw_list(self, win: curses.window, h: int, w: int) -> None:
        spacing = 1 + self.zoom
        row = 0
        for idx, note in enumerate(self.notes):
            if row + spacing <= self.scroll:
                row += spacing
                continue
            y = 1 + row - self.scroll
            if y >= h - 1:
                break
            line = clip_to_cells(self._format_note(note), w - 1)
            attr = curses.A_REVERSE if idx == self.selected else 0
            win.addstr(y, 0, line.ljust(w - 1), attr)
            row += spacing

    def _prompt_save(self, win: curses.window) -> bool | None:
        h, w = win.getmaxyx()
        msg = "Save changes? (y/n)"
        y = h // 2
        x = max(0, (w - display_width(msg)) // 2)
        win.addstr(y, x, clip_to_cells(msg, w - 1))
        win.refresh()
        ch = win.getch()
        if ch in (ord("y"), ord("Y")):
            self.save(self.path)
            return True
        if ch in (ord("n"), ord("N")):
            return False
        return None

    def _handle_alt(self, ch: int) -> None:
        if ch in (ord("o"), ord("O")) and self.notes:
            self.toggle_favorite(self.selected)
        elif ch in (ord("p"), ord("P")) and self.notes:
            note = self.notes[self.selected]
            self.toggle_pin(self.selected)
            self.selected = self.notes.index(note)
        elif ch in (ord("w"), ord("W")) and self.notes:
            self.selected = self.move_up(self.selected)
        elif ch in (ord("s"), ord("S")) and self.notes:
            self.selected = self.move_down(self.selected)
        elif ch in (ord("a"), ord("A")) and self.notes:
            self.move_left(self.selected)
        elif ch in (ord("d"), ord("D")) and self.notes:
            self.move_right(self.selected)

    def _curses_main(self, stdscr: curses.window) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.use_default_colors()

        while True:
            h, w = stdscr.getmaxyx()
            stdscr.erase()
            if h < 3 or w < 20:
                msg = f"Window too small ({w}x{h}). Enlarge to continue."
                stdscr.addstr(h // 2, max(0, (w - display_width(msg)) // 2), clip_to_cells(msg, w - 1))
                stdscr.refresh()
                ch = stdscr.getch()
                if ch == curses.KEY_RESIZE:
                    continue
                if ch in (17,):
                    break
                continue

            self._ensure_visible(h - 2)
            self._draw_header(stdscr, w)
            self._draw_list(stdscr, h, w)
            self._draw_footer(stdscr, h, w)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch == curses.KEY_RESIZE:
                continue
            if ch == 17:  # Ctrl+Q
                self.save(self.path)
                break
            if ch == 23:  # Ctrl+W
                self.zoom_in()
                continue
            if ch == 19:  # Ctrl+S
                self.zoom_out()
                continue
            if ch in (curses.KEY_UP, ord("k")) and self.notes:
                self.selected = max(0, self.selected - 1)
                continue
            if ch in (curses.KEY_DOWN, ord("j")) and self.notes:
                self.selected = min(len(self.notes) - 1, self.selected + 1)
                continue
            if ch == 27:  # ESC or Alt prefix
                stdscr.nodelay(True)
                ch2 = stdscr.getch()
                stdscr.nodelay(False)
                if ch2 == -1:
                    if self.dirty:
                        res = self._prompt_save(stdscr)
                        if res is not None:
                            break
                    else:
                        break
                else:
                    self._handle_alt(ch2)


if __name__ == "__main__":
    MemoPad().run()

# Manual Test Checklist
# - Launch, arrow through notes, resize window.
# - Toggle favorite (Alt+o) and pin (Alt+p); verify grouping.
# - Move within group (Alt+w/Alt+s), indent/outdent (Alt+d/Alt+a).
# - Zoom in/out (Ctrl+w/Ctrl+s) and confirm extra spacing.
# - Save+Quit (Ctrl+q). Re-run and confirm persistence.
# - Paste CJK/emoji into a note in JSON and verify no curses ERRs and proper clipping.
