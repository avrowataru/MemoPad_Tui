# coding: utf-8
"""Terminal memo pad application with favorites, pinning, and movement.

This module implements a simple memo pad using the :mod:`curses` library.
Notes can be marked as favorite, pinned to the top, indented left/right and
reordered vertically.  Keyboard shortcuts are provided for common actions::

    Alt+o  - toggle favorite ("star")
    Alt+p  - toggle pin
    Alt+w  - move note up
    Alt+s  - move note down
    Alt+a  - move note left (decrease indent)
    Alt+d  - move note right (increase indent)
    Ctrl+w - zoom in
    Ctrl+s - zoom out
    Ctrl+q - exit (saving automatically)

The memo pad state is stored as JSON.  The :class:`MemoPad` class exposes
methods for manipulating notes which are unit tested independently from the
interactive interface.
"""
from __future__ import annotations

import json
import curses
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Note:
    """Represents a single note in the memo pad."""

    text: str
    favorite: bool = False
    pinned: bool = False
    indent: int = 0


class MemoPad:
    """A collection of notes with helper methods for manipulation."""

    def __init__(self, path: str = "memopad.json") -> None:
        """Create a memo pad.

        Parameters
        ----------
        path:
            Path to the JSON file used for persistence.
        """

        self.path = path
        self.notes: List[Note] = []
        self.zoom = 1
        self.load()

    # ------------------------------------------------------------------
    # persistence helpers
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Load notes from :attr:`path` if it exists.

        Missing files simply result in an empty memo pad."""

        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self.notes = [Note(**item) for item in raw]
        except FileNotFoundError:
            self.notes = []

    def save(self) -> None:
        """Persist notes to :attr:`path`."""

        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump([asdict(n) for n in self.notes], fh, indent=2)

    # ------------------------------------------------------------------
    # note operations
    # ------------------------------------------------------------------
    def toggle_favorite(self, index: int) -> None:
        """Toggle the favorite flag on the note at ``index``."""

        self.notes[index].favorite = not self.notes[index].favorite

    def toggle_pin(self, index: int) -> None:
        """Toggle pin on the note at ``index`` and keep pins on top."""

        self.notes[index].pinned = not self.notes[index].pinned
        # Reorder so pinned notes stay at the top.
        self.notes.sort(key=lambda n: (not n.pinned))

    def move_up(self, index: int) -> int:
        """Move the note at ``index`` one position upwards.

        Returns the new index of the note."""

        if index > 0 and self.notes[index].pinned == self.notes[index - 1].pinned:
            self.notes[index - 1], self.notes[index] = (
                self.notes[index],
                self.notes[index - 1],
            )
            return index - 1
        return index

    def move_down(self, index: int) -> int:
        """Move the note at ``index`` one position downwards.

        Returns the new index of the note."""

        if (
            index < len(self.notes) - 1
            and self.notes[index].pinned == self.notes[index + 1].pinned
        ):
            self.notes[index + 1], self.notes[index] = (
                self.notes[index],
                self.notes[index + 1],
            )
            return index + 1
        return index

    def move_left(self, index: int) -> None:
        """Decrease the indent level of the note at ``index``."""

        note = self.notes[index]
        note.indent = max(0, note.indent - 1)

    def move_right(self, index: int) -> None:
        """Increase the indent level of the note at ``index``."""

        self.notes[index].indent += 1

    def zoom_in(self) -> None:
        """Increase the zoom level for rendering."""

        self.zoom = min(self.zoom + 1, 5)

    def zoom_out(self) -> None:
        """Decrease the zoom level for rendering."""

        self.zoom = max(1, self.zoom - 1)

    # ------------------------------------------------------------------
    # interactive UI
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Launch the curses interface."""

        curses.wrapper(self._curses_main)

    def _curses_main(self, stdscr: "curses._CursesWindow") -> None:
        """Internal curses event loop."""

        curses.curs_set(0)
        stdscr.keypad(True)
        selected = 0

        while True:
            stdscr.clear()
            self._draw(stdscr, selected)
            stdscr.refresh()

            ch = stdscr.getch()
            # Detect control characters first
            if ch == 17:  # Ctrl+Q
                self.save()
                break
            if ch == 23:  # Ctrl+W zoom in
                self.zoom_in()
                continue
            if ch == 19:  # Ctrl+S zoom out
                self.zoom_out()
                continue
            if ch in (curses.KEY_UP, ord("k")):
                selected = max(0, selected - 1)
                continue
            if ch in (curses.KEY_DOWN, ord("j")):
                selected = min(len(self.notes) - 1, selected + 1)
                continue

            if ch == 27:  # Alt modifier
                ch2 = stdscr.getch()
                if ch2 in (ord("o"), ord("O")):
                    self.toggle_favorite(selected)
                elif ch2 in (ord("p"), ord("P")):
                    self.toggle_pin(selected)
                    # Pinning can reorder, ensure selected points to same note
                    selected = self.notes.index(self.notes[selected])
                elif ch2 in (ord("w"), ord("W")):
                    selected = self.move_up(selected)
                elif ch2 in (ord("s"), ord("S")):
                    selected = self.move_down(selected)
                elif ch2 in (ord("a"), ord("A")):
                    self.move_left(selected)
                elif ch2 in (ord("d"), ord("D")):
                    self.move_right(selected)

    def _draw(self, stdscr: "curses._CursesWindow", selected: int) -> None:
        """Render notes to the screen."""

        h, w = stdscr.getmaxyx()
        # Avoid drawing beyond the visible screen height which would raise
        # curses errors when the number of notes exceeds the terminal rows.
        for idx, note in enumerate(self.notes[: h - 1]):
            prefix = "★" if note.favorite else " "
            pin = "📌" if note.pinned else " "
            indent = "  " * note.indent
            line = f"{prefix}{pin} {indent}{note.text}"
            if self.zoom > 1:
                line = "".join(ch * self.zoom for ch in line)
            if idx == selected:
                stdscr.addnstr(idx, 0, line.ljust(w), w, curses.A_REVERSE)
            else:
                stdscr.addnstr(idx, 0, line.ljust(w), w)

        footer = f"Ctrl+Q save+exit | Ctrl+W zoom in | Ctrl+S zoom out | Zoom:{self.zoom}x"
        # Writing to the very last cell of the terminal (bottom-right) causes
        # ``addnstr`` to raise an error. Reserve one column to avoid touching it.
        width = max(0, w - 1)
        stdscr.addnstr(h - 1, 0, footer.ljust(width), width)


if __name__ == "__main__":
    MemoPad().run()
