"""Windowed game loop shared by the native build and the pygbag (browser) build."""

from __future__ import annotations

import asyncio
import platform

from jenesboat_v2 import events, render
from jenesboat_v2._build_info import BUILD_ID, GIT_SHA
from jenesboat_v2.game import Controls, Game

WIDTH = 960
HEIGHT = 540


def read_controls(rl) -> Controls:
    key = rl.KeyboardKey
    return Controls(
        throttle_up=rl.is_key_down(key.KEY_W),
        throttle_down=rl.is_key_down(key.KEY_S),
        port=rl.is_key_down(key.KEY_A),
        starboard=rl.is_key_down(key.KEY_D),
        dive_toggle=rl.is_key_pressed(key.KEY_SPACE),
    )


async def run(max_seconds: float | None = None) -> None:
    """Open the window and run until closed (or ``max_seconds`` of game time elapsed)."""
    import pyray as rl

    system = platform.system()
    rl.set_trace_log_level(rl.TraceLogLevel.LOG_WARNING)
    rl.init_window(WIDTH, HEIGHT, f"jenesboat {BUILD_ID}")
    if system == "Emscripten":
        platform.window.window_resize()  # sync the canvas CSS size with the GL canvas
    rl.set_target_fps(60)

    game = Game()
    events.emit("ready", build=BUILD_ID, sha=GIT_SHA, platform=system, width=WIDTH, height=HEIGHT)

    while not rl.window_should_close():
        dt = min(rl.get_frame_time(), 0.1)
        controls = read_controls(rl)
        if controls.dive_toggle:
            events.emit("input", key="SPACE")
        game.apply(controls, dt)
        game.update(dt)
        render.draw(rl, game, WIDTH, HEIGHT)
        if max_seconds is not None and game.world.time >= max_seconds:
            break
        await asyncio.sleep(0)

    events.emit("quit", **game.snapshot())
    rl.close_window()


def main() -> None:
    asyncio.run(run())
