"""Windowed game loop shared by the native build and the pygbag (browser) build."""

from __future__ import annotations

import asyncio
import platform

from jenesboat_v2 import events, render
from jenesboat_v2._build_info import BUILD_ID, GIT_SHA
from jenesboat_v2.game import TIME_SCALES, Controls, Game

WIDTH = 960
HEIGHT = 540


def read_controls(rl) -> Controls:
    key = rl.KeyboardKey
    scale = None
    keys = (key.KEY_ONE, key.KEY_TWO, key.KEY_THREE, key.KEY_FOUR)
    for k, value in zip(keys, TIME_SCALES, strict=True):
        if rl.is_key_pressed(k):
            scale = value
    return Controls(
        throttle_up=rl.is_key_pressed(key.KEY_W),
        throttle_down=rl.is_key_pressed(key.KEY_S),
        port=rl.is_key_down(key.KEY_A),
        starboard=rl.is_key_down(key.KEY_D),
        rudder_center=rl.is_key_pressed(key.KEY_Q),
        dive_toggle=rl.is_key_pressed(key.KEY_SPACE),
        deep=rl.is_key_pressed(key.KEY_C),
        fire=rl.is_key_pressed(key.KEY_F),
        zoom_in=rl.is_key_pressed(key.KEY_EQUAL),
        zoom_out=rl.is_key_pressed(key.KEY_MINUS),
        time_scale=scale,
        next_target=rl.is_key_pressed(key.KEY_T),
        legend=rl.is_key_pressed(key.KEY_L),
        pause=rl.is_key_pressed(key.KEY_P),
        restart=rl.is_key_pressed(key.KEY_R),
    )


def fit_viewport(rl, current: tuple[int, int] | None) -> tuple[int, int] | None:
    """Stretch the GL viewport over the whole canvas buffer.

    On high-DPI screens the browser GL buffer is devicePixelRatio times larger than the
    960x540 window raylib asked for, and raylib's viewport stays 960x540 in the bottom-left
    corner (GL's origin).  Drawing stays in 960x540 coordinates; only the viewport changes.
    """
    try:
        canvas = platform.window.canvas  # type: ignore[attr-defined]
        size = (int(canvas.width), int(canvas.height))
    except Exception:  # noqa: BLE001 - no canvas (not in a browser page)
        return current
    if size == current or size[0] <= 0 or size[1] <= 0:
        return current
    rl.rl_viewport(0, 0, size[0], size[1])
    events.emit("viewport", width=size[0], height=size[1])
    return size


async def run(max_seconds: float | None = None, seed: int | None = None) -> None:
    """Open the window and run until closed (or ``max_seconds`` of game time elapsed)."""
    import pyray as rl

    system = platform.system()
    rl.set_trace_log_level(rl.TraceLogLevel.LOG_WARNING)
    rl.init_window(WIDTH, HEIGHT, f"jenesboat {BUILD_ID}")
    if system == "Emscripten":
        # The page CSS (web/noctx.tmpl) centres and scales the canvas; this only focuses it.
        platform.window.window_resize()
    viewport: tuple[int, int] | None = None
    rl.set_target_fps(60)

    events.emit("ready", build=BUILD_ID, sha=GIT_SHA, platform=system, width=WIDTH, height=HEIGHT)
    game = Game(seed=seed)

    while not rl.window_should_close():
        dt = min(rl.get_frame_time(), 0.1)
        controls = read_controls(rl)
        for name, pressed in (
            ("W", controls.throttle_up),
            ("S", controls.throttle_down),
            ("Q", controls.rudder_center),
            ("P", controls.pause),
            ("T", controls.next_target),
            ("SPACE", controls.dive_toggle),
            ("C", controls.deep),
            ("F", controls.fire),
            ("R", controls.restart),
        ):
            if pressed:
                events.emit("input", key=name)
        game.apply(controls, dt)
        game.update(dt)
        if system == "Emscripten":
            viewport = fit_viewport(rl, viewport)
        render.draw(rl, game, WIDTH, HEIGHT)
        if max_seconds is not None and game.world.time >= max_seconds:
            break
        await asyncio.sleep(0)

    events.emit("quit", **game.snapshot())
    rl.close_window()


def main(seed: int | None = None) -> None:
    asyncio.run(run(seed=seed))
