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
    p.add_argument(
        "--script",
        default=None,
        help=(
            "headless: JSON list of timed orders, e.g. "
            '\'[{"t":0,"throttle":1},{"t":5,"rudder":1},{"t":8,"dive":true}]\'. '
            "Keys: throttle, rudder (-1..1), dive (toggle), target_depth (m)."
        ),
    )
    return p


def run_headless(seconds: float, dt: float, script: str | None, trace: bool) -> dict:
    orders = sorted(json.loads(script) if script else [], key=lambda o: o.get("t", 0.0))
    game = Game(state_interval=1.0 if trace else math.inf)
    events.emit("ready", build=BUILD_ID, sha=GIT_SHA, platform="headless", seconds=seconds)
    sub = game.world.player
    t = 0.0
    while t < seconds - 1e-9:
        while orders and orders[0].get("t", 0.0) <= t + 1e-9:
            order = orders.pop(0)
            if "throttle" in order:
                sub.set_throttle(float(order["throttle"]))
            if "rudder" in order:
                sub.set_rudder(float(order["rudder"]))
            if "target_depth" in order:
                sub.set_target_depth(float(order["target_depth"]))
            if order.get("dive"):
                sub.toggle_dive()
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
        run_headless(args.seconds, args.dt, args.script, args.trace)
        return 0
    from jenesboat_v2.app import main as app_main

    app_main()
    return 0


def entrypoint() -> int:
    """Console-script wrapper; a closed pipe (``| head``) is not an error for agents."""
    try:
        return main()
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
