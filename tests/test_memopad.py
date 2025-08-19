from pathlib import Path
import sys

# Ensure project root is on the import path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from memopad import MemoPad, Note


def make_pad(tmp_path, notes):
    path = tmp_path / "pad.json"
    pad = MemoPad(path=str(path))
    pad.notes = notes
    return pad, path


def test_toggle_favorite(tmp_path):
    pad, _ = make_pad(tmp_path, [Note("a"), Note("b")])
    pad.toggle_favorite(0)
    assert pad.notes[0].favorite
    pad.toggle_favorite(0)
    assert not pad.notes[0].favorite


def test_toggle_pin_reorders(tmp_path):
    pad, _ = make_pad(tmp_path, [Note("a"), Note("b")])
    pad.toggle_pin(1)
    assert pad.notes[0].pinned and pad.notes[0].text == "b"


def test_move_up_down(tmp_path):
    pad, _ = make_pad(tmp_path, [Note("a"), Note("b"), Note("c")])
    idx = pad.move_down(0)
    assert idx == 1 and pad.notes[1].text == "a"
    idx = pad.move_up(idx)
    assert idx == 0 and pad.notes[0].text == "a"


def test_indent(tmp_path):
    pad, _ = make_pad(tmp_path, [Note("a")])
    pad.move_right(0)
    pad.move_right(0)
    assert pad.notes[0].indent == 2
    pad.move_left(0)
    assert pad.notes[0].indent == 1
    pad.move_left(0)
    pad.move_left(0)
    assert pad.notes[0].indent == 0


def test_save_load(tmp_path):
    pad, path = make_pad(tmp_path, [Note("a"), Note("b", favorite=True)])
    pad.save()
    new_pad = MemoPad(path=str(path))
    assert len(new_pad.notes) == 2
    assert new_pad.notes[1].favorite


def test_zoom(tmp_path):
    pad, _ = make_pad(tmp_path, [])
    assert pad.zoom == 1
    pad.zoom_in()
    assert pad.zoom == 2
    pad.zoom_out()
    assert pad.zoom == 1
    pad.zoom_out()
    assert pad.zoom == 1
