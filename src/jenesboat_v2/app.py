"""Windowed game loop shared by the native build and the pygbag (browser) build.

The game draws in *logical* pixels: 960x540 on a 16:9 screen, wider on a wider screen (a
phone held sideways is about 19.5:9) and 450 px tall instead of 540 on small screens so the
HUD text stays readable.  ``Layout`` maps that logical space onto whatever the canvas is:
the GL viewport covers the whole canvas buffer (on high-DPI screens it is devicePixelRatio
times larger than the window raylib asked for) and the projection is the logical size.
"""

from __future__ import annotations

import asyncio
import platform
from dataclasses import dataclass
from typing import Any

from jenesboat_v2 import events, render, touch
from jenesboat_v2._build_info import BUILD_ID, GIT_SHA
from jenesboat_v2.game import TIME_SCALES, Controls, Game

WIDTH = 960
HEIGHT = 540
MIN_HEIGHT = 450  # logical px on screens shorter than HEIGHT: bigger text on a phone
MIN_WIDTH = 960  # the HUD is laid out for at least this many logical px across
SCREENSHOT_AT = 2.0  # s of game time before --screenshot saves the frame

RL_MODELVIEW = 0x1700
RL_PROJECTION = 0x1701

# Keyboard key for every button name; the names are the ones touch.KEYS uses.
KEYBOARD = {
    "W": "KEY_W",
    "S": "KEY_S",
    "A": "KEY_A",
    "D": "KEY_D",
    "Q": "KEY_Q",
    "SPACE": "KEY_SPACE",
    "C": "KEY_C",
    "F": "KEY_F",
    "T": "KEY_T",
    "MINUS": "KEY_MINUS",
    "EQUAL": "KEY_EQUAL",
    "1": "KEY_ONE",
    "2": "KEY_TWO",
    "3": "KEY_THREE",
    "4": "KEY_FOUR",
    "P": "KEY_P",
    "L": "KEY_L",
    "R": "KEY_R",
    "Y": "KEY_Y",
    "N": "KEY_N",
}
LOGGED = ("W", "S", "Q", "P", "T", "SPACE", "C", "F", "R", "TIME")  # keys that emit an input event


def logical_size(css_width: float, css_height: float) -> tuple[int, int]:
    """Logical pixels to draw for a canvas of ``css_width`` x ``css_height`` CSS pixels.

    The height is HEIGHT, or on a short screen as little as MIN_HEIGHT while keeping at
    least MIN_WIDTH across; the width follows the canvas aspect ratio so nothing is
    stretched and a wide screen shows more map.
    """
    if css_width <= 0 or css_height <= 0:
        return WIDTH, HEIGHT
    aspect = css_width / css_height
    if css_height >= HEIGHT:
        height = float(HEIGHT)
    else:
        height = min(float(HEIGHT), max(float(MIN_HEIGHT), MIN_WIDTH / aspect))
    return int(round(height * aspect)), int(round(height))


@dataclass(frozen=True)
class Layout:
    width: int  # logical px drawn
    height: int
    css_width: float  # the canvas box in CSS px (window px natively)
    css_height: float
    buffer: tuple[int, int]  # the GL buffer in device px

    @property
    def scale(self) -> float:
        """Logical px per CSS px."""
        return self.height / self.css_height if self.css_height else 1.0

    def snapshot(self) -> dict:
        return {
            "width": self.buffer[0],
            "height": self.buffer[1],
            "logical": [self.width, self.height],
            "css": [round(self.css_width), round(self.css_height)],
        }


def measure(rl, window: Any | None) -> Layout:
    """Current canvas size: from the page in the browser, from raylib natively."""
    css_w = css_h = buf_w = buf_h = 0
    if window is not None:
        try:
            canvas = window.canvas
            css_w, css_h = float(canvas.clientWidth), float(canvas.clientHeight)
            buf_w, buf_h = int(canvas.width), int(canvas.height)
        except Exception:  # noqa: BLE001 - no canvas yet
            css_w = css_h = buf_w = buf_h = 0
    if css_w < 8 or css_h < 8 or buf_w < 8 or buf_h < 8:
        css_w, css_h = float(rl.get_screen_width()), float(rl.get_screen_height())
        buf_w, buf_h = int(rl.get_render_width()), int(rl.get_render_height())
    width, height = logical_size(css_w, css_h)
    return Layout(width, height, css_w, css_h, (buf_w, buf_h))


def apply_layout(rl, layout: Layout) -> None:
    """Stretch the viewport over the buffer and project the logical size onto it.  Done
    every frame: raylib resets both when it thinks the window changed size."""
    rl.rl_viewport(0, 0, layout.buffer[0], layout.buffer[1])
    rl.rl_matrix_mode(RL_PROJECTION)
    rl.rl_load_identity()
    rl.rl_ortho(0.0, float(layout.width), float(layout.height), 0.0, 0.0, 1.0)
    rl.rl_matrix_mode(RL_MODELVIEW)
    rl.rl_load_identity()


def keyboard_state(rl) -> tuple[set[str], set[str]]:
    """Button names pressed this frame (edges) and held (A/D) on the keyboard."""
    key = rl.KeyboardKey
    pressed = {name for name, attr in KEYBOARD.items() if rl.is_key_pressed(getattr(key, attr))}
    held = {name for name in touch.HELD_KEYS if rl.is_key_down(getattr(key, KEYBOARD[name]))}
    return pressed, held


def controls_from_keys(pressed: set[str], held: set[str], time_scale: int) -> Controls:
    """Turn button names (keyboard or touch) into this frame's ``Controls``.  ``TIME`` is
    the touch button that steps through the time compressions."""
    scale = None
    for name, value in zip(("1", "2", "3", "4"), TIME_SCALES, strict=True):
        if name in pressed:
            scale = value
    if "TIME" in pressed:
        index = TIME_SCALES.index(time_scale) if time_scale in TIME_SCALES else 0
        scale = TIME_SCALES[(index + 1) % len(TIME_SCALES)]
    return Controls(
        throttle_up="W" in pressed,
        throttle_down="S" in pressed,
        port="A" in held,
        starboard="D" in held,
        rudder_center="Q" in pressed,
        dive_toggle="SPACE" in pressed,
        deep="C" in pressed,
        fire="F" in pressed,
        zoom_in="EQUAL" in pressed,
        zoom_out="MINUS" in pressed,
        time_scale=scale,
        next_target="T" in pressed,
        legend="L" in pressed,
        pause="P" in pressed,
        restart="R" in pressed,
        confirm="Y" in pressed,
        cancel="N" in pressed,
    )


def read_controls(rl, pad: touch.TouchState, time_scale: int) -> Controls:
    """Keyboard and touch buttons merged; also logs the presses agents watch for."""
    pressed, held = keyboard_state(rl)
    for name in LOGGED:
        if name in pressed:
            events.emit("input", key=name)
        elif name in pad.pressed:
            events.emit("input", key=name, source="touch")
    return controls_from_keys(pressed | pad.pressed, held | pad.held, time_scale)


async def run(
    max_seconds: float | None = None,
    seed: int | None = None,
    size: tuple[int, int] | None = None,
    touch_layout: bool = False,
    screenshot: str | None = None,
) -> None:
    """Open the window and run until closed (or ``max_seconds`` of game time elapsed).

    ``size`` is the native window size; ``touch_layout`` lays the HUD out as on a touch
    screen without one (to look at it on a desktop); ``screenshot`` saves the frame at
    SCREENSHOT_AT seconds of game time and quits.
    """
    import pyray as rl

    system = platform.system()
    width, height = size or (WIDTH, HEIGHT)
    rl.set_trace_log_level(rl.TraceLogLevel.LOG_WARNING)
    rl.init_window(width, height, f"jenesboat {BUILD_ID}")
    window = None
    if system == "Emscripten":
        # The page CSS (web/noctx.tmpl) places the canvas; this only focuses it.
        window = platform.window  # type: ignore[attr-defined]
        window.window_resize()
    bridge = touch.browser_bridge()
    pad = touch.TouchPad(bridge)
    layout: Layout | None = None
    rl.set_target_fps(60)

    events.emit("ready", build=BUILD_ID, sha=GIT_SHA, platform=system, width=width, height=height)
    game = Game(seed=seed)

    while not rl.window_should_close():
        dt = min(rl.get_frame_time(), 0.1)
        current = measure(rl, window)
        if current != layout:
            layout = current
            events.emit("viewport", **layout.snapshot())
        apply_layout(rl, layout)
        state = pad.poll()
        if touch_layout and not state.active:
            state = touch.TouchState(True, pad_left=touch.PAD_LEFT, pad_right=touch.PAD_RIGHT)
        controls = read_controls(rl, state, game.time_scale)
        game.apply(controls, dt)
        game.update(dt)
        pad.show(game.confirming_restart, game.paused, game.time_scale, game.show_legend)
        insets = None
        if state.active:
            insets = render.Pad(state.pad_left * layout.scale, state.pad_right * layout.scale)
        render.draw(rl, game, layout.width, layout.height, insets)
        if screenshot is not None and game.world.time >= SCREENSHOT_AT:
            rl.take_screenshot(screenshot)
            events.emit("screenshot", path=screenshot, **layout.snapshot())
            break
        if max_seconds is not None and game.world.time >= max_seconds:
            break
        await asyncio.sleep(0)

    events.emit("quit", **game.snapshot())
    rl.close_window()


def main(
    seed: int | None = None,
    size: tuple[int, int] | None = None,
    touch_layout: bool = False,
    screenshot: str | None = None,
) -> None:
    asyncio.run(run(seed=seed, size=size, touch_layout=touch_layout, screenshot=screenshot))
