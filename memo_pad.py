import curses
import json
import os

DATA_FILE = "memos.json"

def load_memos():
    """Load memos from the data file.

    Returns:
        list[str]: List of memo strings.
    """
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memos(memos):
    """Persist memos to the data file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(memos, f, indent=2)


def draw_menu(stdscr, memos, selected_idx):
    """Render the memo list."""
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    header = "MemoPad - Sticky Notes (a=add d=delete q=quit)"
    stdscr.addstr(0, 0, header[:width-1])
    for idx, memo in enumerate(memos):
        line = f"{idx + 1}. {memo}"
        if idx == selected_idx:
            stdscr.attron(curses.A_REVERSE)
        stdscr.addstr(idx + 2, 2, line[:width-4])
        if idx == selected_idx:
            stdscr.attroff(curses.A_REVERSE)
    stdscr.refresh()


def get_user_input(stdscr, prompt):
    """Prompt for user input at the bottom of the screen."""
    curses.echo()
    height = stdscr.getmaxyx()[0]
    stdscr.addstr(height - 2, 2, prompt)
    stdscr.clrtoeol()
    stdscr.refresh()
    text = stdscr.getstr(height - 2, len(prompt) + 2).decode("utf-8")
    curses.noecho()
    return text


def main(stdscr):
    """Run the main event loop."""
    curses.curs_set(0)
    memos = load_memos()
    selected_idx = 0
    while True:
        draw_menu(stdscr, memos, selected_idx)
        ch = stdscr.getch()
        if ch in (ord('q'), ord('Q')):
            break
        elif ch in (curses.KEY_DOWN, ord('j')) and memos:
            selected_idx = (selected_idx + 1) % len(memos)
        elif ch in (curses.KEY_UP, ord('k')) and memos:
            selected_idx = (selected_idx - 1) % len(memos)
        elif ch in (ord('a'), ord('A')):
            text = get_user_input(stdscr, "New memo: ")
            if text:
                memos.append(text)
                save_memos(memos)
                selected_idx = len(memos) - 1
        elif ch in (ord('d'), ord('D')) and memos:
            del memos[selected_idx]
            save_memos(memos)
            if selected_idx >= len(memos):
                selected_idx = max(0, len(memos) - 1)
    stdscr.clear()
    stdscr.addstr(0, 0, "Goodbye!")
    stdscr.refresh()
    curses.napms(1000)


if __name__ == "__main__":
    curses.wrapper(main)
