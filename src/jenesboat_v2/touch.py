"""On-screen buttons for touch screens (phones, tablets).

The buttons themselves are HTML elements over the canvas (``web/noctx.tmpl``): CSS sizes
them in device-independent pixels and the browser handles multi-touch, so nothing here
depends on raylib's pointer input.  The page keeps two integers, ``jb_held`` (buttons
currently pressed) and ``jb_taps`` (buttons pressed since the game last looked), one bit per
button in the order of ``KEYS``.  Once per frame the game reads both through the pygbag
bridge and acknowledges the taps, so a tap shorter than a frame is never lost.  The page also
reports how wide the button clusters are so the HUD can keep clear of them.

Everything below is plain Python; the browser-specific part is the ``WindowBridge``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

# Button names, in bit order.  They are the keyboard keys they stand for, plus TIME, which
# cycles through the time compressions (one button instead of four).  The page must use the
# same list in the same order: tests/test_touch.py checks web/noctx.tmpl against this.
KEYS = (
    "W",
    "S",
    "A",
    "D",
    "Q",
    "SPACE",
    "C",
    "F",
    "T",
    "MINUS",
    "EQUAL",
    "P",
    "L",
    "R",
    "Y",
    "N",
    "TIME",
)
BIT = {name: 1 << i for i, name in enumerate(KEYS)}
HELD_KEYS = frozenset({"A", "D"})  # the rudder keeps moving while these are held

# CSS px the button clusters take at the left and right edges of a phone screen (the page
# reports the real figures; these stand in for them in the desktop preview, --touch).
PAD_LEFT = 240.0
PAD_RIGHT = 195.0


class Bridge(Protocol):
    """What the game needs from the page: numbers in, a call out."""

    def get(self, name: str) -> float | None:
        """Value of the global ``name`` as a number, ``None`` if missing."""

    def call(self, name: str, *args: Any) -> None:
        """Call the global function ``name``; errors are swallowed."""


class WindowBridge:
    """The real thing: reads ``platform.window.<name>`` in the pygbag runtime."""

    def __init__(self, window: Any) -> None:
        self.window = window

    def get(self, name: str) -> float | None:
        try:
            return float(getattr(self.window, name))
        except Exception:  # noqa: BLE001 - undefined global or a non-number
            return None

    def call(self, name: str, *args: Any) -> None:
        try:
            getattr(self.window, name)(*args)
        except Exception:  # noqa: BLE001 - the page has no such hook
            pass


@dataclass
class TouchState:
    """What the touch overlay reported this frame."""

    active: bool = False  # the page shows touch buttons
    held: set[str] = field(default_factory=set)
    pressed: set[str] = field(default_factory=set)  # taps since the last poll
    pad_left: float = 0.0  # CSS px taken by the clusters on the left...
    pad_right: float = 0.0  # ...and on the right (bottom part of the screen)


def decode(bits: int) -> set[str]:
    return {name for name, bit in BIT.items() if bits & bit}


def encode(names) -> int:
    return sum(BIT[name] for name in names)


class TouchPad:
    """Polls the page for button state and tells it what the game is showing."""

    def __init__(self, bridge: Bridge | None) -> None:
        self.bridge = bridge
        self._shown: tuple | None = None

    def poll(self) -> TouchState:
        if self.bridge is None:
            return TouchState()
        active = self.bridge.get("jb_touch")
        if not active:
            return TouchState()
        held = int(self.bridge.get("jb_held") or 0)
        taps = int(self.bridge.get("jb_taps") or 0)
        if taps:
            self.bridge.call("jb_ack")
        return TouchState(
            active=True,
            held=decode(held),
            pressed=decode(taps),
            pad_left=self.bridge.get("jb_pad_left") or 0.0,
            pad_right=self.bridge.get("jb_pad_right") or 0.0,
        )

    def show(self, confirming: bool, paused: bool, time_scale: int, legend: bool) -> None:
        """Update the button labels (YES/NO prompt, RUN/PAUSE, x1..x32) when they change."""
        state = (bool(confirming), bool(paused), int(time_scale), bool(legend))
        if self.bridge is None or state == self._shown:
            return
        self._shown = state
        self.bridge.call("jb_show", int(confirming), int(paused), int(time_scale), int(legend))


def browser_bridge() -> WindowBridge | None:
    """The page bridge when running under pygbag, else ``None``."""
    import platform

    if platform.system() != "Emscripten":
        return None
    try:
        return WindowBridge(platform.window)  # type: ignore[attr-defined]
    except AttributeError:
        return None
