"""Command line entry point: windowed game by default, ``--headless`` for agents and tests."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence

from jenesboat_v2 import events
from jenesboat_v2._build_info import BUILD_ID, GIT_SHA
from jenesboat_v2.game import Game
from jenesboat_v2.sim import difficulty
from jenesboat_v2.sim.vessel import telegraph_by_name

VERSION = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jenesboat-v2", description="2D WWII submarine game")
    p.add_argument("--version", action="store_true", help="print version and build id")
    p.add_argument(
        "--headless",
        action="store_true",
        help="run the simulation without a window and print JENESBOAT JSON events",
    )
    p.add_argument("--seconds", type=float, default=10.0, help="headless: game time to simulate")
    p.add_argument("--dt", type=float, default=0.1, help="headless: simulation step in seconds")
    p.add_argument("--trace", action="store_true", help="headless: emit a state event every second")
    p.add_argument("--seed", type=int, default=None, help="scenario seed (random if omitted)")
    p.add_argument(
        "--difficulty",
        choices=difficulty.DIFFICULTY_NAMES,
        default=None,
        help=f"difficulty level (default {difficulty.DEFAULT_DIFFICULTY}): {difficulty.describe()}",
    )
    p.add_argument(
        "--size",
        default=None,
        metavar="WxH",
        help="windowed: window size in px, e.g. 976x450 (a phone held sideways)",
    )
    p.add_argument(
        "--touch",
        action="store_true",
        help="windowed: lay the HUD out as on a touch screen (between the button clusters)",
    )
    p.add_argument(
        "--screenshot",
        default=None,
        metavar="FILE",
        help="windowed: save a PNG after 2 s of game time and quit (needs a display)",
    )
    p.add_argument(
        "--script",
        default=None,
        help=(
            "headless: JSON list of timed orders, e.g. "
            '\'[{"t":0,"throttle":1},{"t":5,"rudder":1},{"t":8,"dive":true}]\'. '
            "Keys: throttle (-1..1) or telegraph ('ahead half', ...), rudder (-1..1), "
            "dive (toggle), deep, target_depth (m), fire, time_scale (1, 2, 4, 8, 16 or 32), "
            "pause (toggle), target (ship id, or null for automatic), next_target."
        ),
    )
    return p


def run_headless(
    seconds: float,
    dt: float,
    script: str | None,
    trace: bool,
    seed: int | None = None,
    difficulty_name: str | None = None,
) -> dict:
    """Simulate ``seconds`` of game time (time compression applies on top of that)."""
    orders = sorted(json.loads(script) if script else [], key=lambda o: o.get("t", 0.0))
    level = difficulty.get(difficulty_name)
    events.emit(
        "ready",
        build=BUILD_ID,
        sha=GIT_SHA,
        platform="headless",
        seconds=seconds,
        difficulty=level.name,
    )
    game = Game(state_interval=1.0 if trace else math.inf, seed=seed, difficulty=level.name)
    sub = game.world.player
    t = 0.0
    while t < seconds - 1e-9:
        while orders and orders[0].get("t", 0.0) <= t + 1e-9:
            order = orders.pop(0)
            if "throttle" in order:
                sub.set_throttle(float(order["throttle"]))
            if "telegraph" in order:
                index = telegraph_by_name(str(order["telegraph"]))
                if index is None:
                    raise SystemExit(f"unknown telegraph order {order['telegraph']!r}")
                sub.set_telegraph(index)
            if "rudder" in order:
                sub.set_rudder(float(order["rudder"]))
            if "target_depth" in order:
                sub.set_target_depth(float(order["target_depth"]))
            if order.get("dive"):
                sub.toggle_dive()
            if order.get("deep"):
                sub.order_deep()
            if "time_scale" in order:
                game.set_time_scale(int(order["time_scale"]))
            if order.get("fire"):
                game.fire()
            if order.get("pause"):
                game.toggle_pause()
            if "target" in order:
                game.select_target(order["target"])
            if order.get("next_target"):
                game.next_target()
            events.emit("order", **order)
        game.update(dt)
        t += dt
    final = game.snapshot()
    events.emit("final", **final)
    return final


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(f"jenesboat-v2 {VERSION} (build {BUILD_ID})")
        return 0
    if args.headless:
        run_headless(args.seconds, args.dt, args.script, args.trace, args.seed, args.difficulty)
        return 0
    from jenesboat_v2.app import main as app_main

    app_main(
        seed=args.seed,
        size=parse_size(args.size),
        touch_layout=args.touch,
        screenshot=args.screenshot,
        difficulty=args.difficulty,
    )
    return 0


def parse_size(text: str | None) -> tuple[int, int] | None:
    """``"976x450"`` -> ``(976, 450)``; ``None`` stays ``None``."""
    if text is None:
        return None
    w, sep, h = text.lower().partition("x")
    if not sep or not w.isdigit() or not h.isdigit() or int(w) < 1 or int(h) < 1:
        raise SystemExit(f"--size must look like 960x540, not {text!r}")
    return int(w), int(h)


def entrypoint() -> int:
    """Console-script wrapper; a closed pipe (``| head``) is not an error for agents."""
    try:
        return main()
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
