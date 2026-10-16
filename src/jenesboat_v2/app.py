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
        legend=rl.is_key_pressed(key.KEY_L),
        pause=rl.is_key_pressed(key.KEY_P),
        restart=rl.is_key_pressed(key.KEY_R),
    )


async def run(max_seconds: float | None = None, seed: int | None = None) -> None:
    """Open the window and run until closed (or ``max_seconds`` of game time elapsed)."""
    import pyray as rl

    system = platform.system()
    rl.set_trace_log_level(rl.TraceLogLevel.LOG_WARNING)
    rl.init_window(WIDTH, HEIGHT, f"jenesboat {BUILD_ID}")
    if system == "Emscripten":
        platform.window.window_resize()  # sync the canvas CSS size with the GL canvas
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
            ("SPACE", controls.dive_toggle),
            ("C", controls.deep),
            ("F", controls.fire),
            ("R", controls.restart),
        ):
            if pressed:
                events.emit("input", key=name)
        game.apply(controls, dt)
        game.update(dt)
        render.draw(rl, game, WIDTH, HEIGHT)
        if max_seconds is not None and game.world.time >= max_seconds:
            break
        await asyncio.sleep(0)

    events.emit("quit", **game.snapshot())
    rl.close_window()


def main(seed: int | None = None) -> None:
    asyncio.run(run(seed=seed))
