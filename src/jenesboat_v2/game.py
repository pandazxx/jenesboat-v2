"""Frontend-agnostic game session: turns control intents into orders and ticks the world."""

from __future__ import annotations

from dataclasses import dataclass

from jenesboat_v2 import events
from jenesboat_v2.sim import World, default_world

THROTTLE_RAMP = 0.5  # throttle units per second while W/S is held


@dataclass
class Controls:
    """What the player is doing this frame.  ``dive_toggle`` is an edge (key pressed)."""

    throttle_up: bool = False
    throttle_down: bool = False
    port: bool = False
    starboard: bool = False
    dive_toggle: bool = False


class Game:
    def __init__(self, world: World | None = None, state_interval: float = 1.0) -> None:
        self.world = world or default_world()
        self.state_interval = state_interval
        self._since_state = 0.0
        self.state_events = 0

    def apply(self, controls: Controls, dt: float) -> None:
        sub = self.world.player
        if controls.throttle_up:
            sub.set_throttle(sub.throttle + THROTTLE_RAMP * dt)
        if controls.throttle_down:
            sub.set_throttle(sub.throttle - THROTTLE_RAMP * dt)
        rudder = 0.0
        if controls.port:
            rudder -= 1.0
        if controls.starboard:
            rudder += 1.0
        sub.set_rudder(rudder)
        if controls.dive_toggle:
            sub.toggle_dive()

    def update(self, dt: float) -> None:
        self.world.step(dt)
        self._since_state += dt
        if self._since_state >= self.state_interval - 1e-9:
            self._since_state = 0.0
            self.emit_state()

    def snapshot(self) -> dict:
        return self.world.snapshot()

    def emit_state(self) -> None:
        self.state_events += 1
        events.emit("state", **self.snapshot())
