"""The touch-button protocol between the page (web/noctx.tmpl) and the game (touch.py)."""

import re
from pathlib import Path

from jenesboat_v2 import touch

TEMPLATE = Path(__file__).resolve().parents[1] / "web" / "noctx.tmpl"


class FakeBridge:
    """A page: numeric globals and the calls the game makes."""

    def __init__(self, **values):
        self.values = values
        self.calls: list[tuple] = []

    def get(self, name):
        value = self.values.get(name)
        return None if isinstance(value, str) else value

    def text(self, name):
        value = self.values.get(name)
        return value if isinstance(value, str) else None

    def call(self, name, *args):
        self.calls.append((name, *args))
        if name == "jb_ack":
            self.values["jb_taps"] = 0


def test_bits_round_trip_and_fit_in_an_int32():
    assert len(touch.KEYS) <= 31
    names = {"W", "D", "TIME"}
    assert touch.decode(touch.encode(names)) == names
    assert touch.decode(0) == set()


def test_poll_reports_held_and_tapped_buttons_and_acknowledges_taps():
    bridge = FakeBridge(
        jb_touch=1,
        jb_held=touch.encode({"D"}),
        jb_taps=touch.encode({"W", "D", "F"}),
        jb_pad_left=240,
        jb_pad_right=195,
    )
    state = touch.TouchPad(bridge).poll()
    assert state.active
    assert state.held == {"D"}
    assert state.pressed == {"W", "D", "F"}
    assert (state.pad_left, state.pad_right) == (240, 195)
    assert bridge.calls == [("jb_ack",)]
    again = touch.TouchPad(bridge).poll()
    assert again.pressed == set() and again.held == {"D"}  # taps were consumed, the hold stays


def test_poll_is_inert_without_a_page_or_without_touch():
    assert not touch.TouchPad(None).poll().active
    bridge = FakeBridge(jb_touch=0, jb_held=touch.encode({"A"}), jb_taps=1)
    state = touch.TouchPad(bridge).poll()
    assert not state.active and not state.held and not state.pressed
    assert bridge.calls == []
    assert not touch.TouchPad(FakeBridge()).poll().active  # old page without the globals


def test_show_tells_the_page_only_when_something_changed():
    bridge = FakeBridge(jb_touch=1)
    pad = touch.TouchPad(bridge)
    pad.show(confirming=False, paused=False, time_scale=1, legend=True)
    pad.show(confirming=False, paused=False, time_scale=1, legend=True)
    pad.show(confirming=True, paused=False, time_scale=4, legend=False)
    assert bridge.calls == [("jb_show", 0, 0, 1, 1), ("jb_show", 1, 0, 4, 0)]
    touch.TouchPad(None).show(True, True, 2, True)  # no page: nothing to do


def test_window_bridge_swallows_missing_globals_and_bad_values():
    class Window:
        jb_touch = 1
        jb_held = "7"

        def jb_ack(self):
            raise RuntimeError("boom")

    bridge = touch.WindowBridge(Window())
    assert bridge.get("jb_touch") == 1.0
    assert bridge.get("jb_held") == 7.0
    assert bridge.get("jb_taps") is None
    bridge.call("jb_ack")  # raises inside the page: ignored
    bridge.call("jb_missing")


def test_browser_bridge_is_none_outside_the_browser():
    assert touch.browser_bridge() is None


def test_page_uses_the_same_buttons_in_the_same_order():
    text = TEMPLATE.read_text()
    m = re.search(r"const JB_KEYS = \[(.*?)\];", text, re.S)
    assert m, "web/noctx.tmpl must define JB_KEYS"
    page_keys = tuple(re.findall(r'"([A-Z0-9]+)"', m.group(1)))
    assert page_keys == touch.KEYS
    buttons = re.findall(r'<button data-key="([A-Z0-9]+)"', text)
    assert sorted(buttons) == sorted(touch.KEYS), "one button per key"
    held = re.search(r"const HOLD = new Set\(\[(.*?)\]\)", text)
    assert held and set(re.findall(r'"([A-Z]+)"', held.group(1))) == set(touch.HELD_KEYS)
    for name in ("jb_touch", "jb_held", "jb_taps", "jb_ack", "jb_show", "jb_pad_left"):
        assert f"window.{name}" in text
