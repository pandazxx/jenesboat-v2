"""Torpedoes: tubes that reload, straight runners that arm after a short distance, and the
fire-control geometry the HUD uses to show the lead."""

from __future__ import annotations

import math
from dataclasses import dataclass

from jenesboat_v2.sim.geo import project, ray_line_crossing, track_angle
from jenesboat_v2.sim.params import DEPTH_CHARGE, G7E, DepthChargeParams, TorpedoParams


@dataclass
class Tubes:
    params: TorpedoParams = G7E
    loaded: int = -1  # -1: fill all tubes on creation
    reserves: int = -1
    reload_timer: float = 0.0

    def __post_init__(self) -> None:
        if self.loaded < 0:
            self.loaded = self.params.tubes
        if self.reserves < 0:
            self.reserves = self.params.reserves

    @property
    def reloading(self) -> bool:
        return self.loaded < self.params.tubes and self.reserves > 0

    @property
    def can_fire(self) -> bool:
        return self.loaded > 0

    def fire(self) -> bool:
        if not self.can_fire:
            return False
        self.loaded -= 1
        return True

    def step(self, dt: float) -> None:
        """Reload one tube at a time from the reserves."""
        if not self.reloading:
            self.reload_timer = 0.0
            return
        self.reload_timer += dt
        if self.reload_timer >= self.params.reload_time:
            self.reload_timer -= self.params.reload_time
            self.loaded += 1
            self.reserves -= 1

    def snapshot(self) -> dict:
        return {
            "loaded": self.loaded,
            "reserves": self.reserves,
            "reload": round(self.reload_timer, 1) if self.reloading else None,
        }


@dataclass
class Torpedo:
    torpedo_id: int
    x: float
    y: float
    heading: float
    params: TorpedoParams = G7E
    run: float = 0.0
    alive: bool = True
    start_x: float = 0.0  # launch point, the track is the straight line from here
    start_y: float = 0.0

    def __post_init__(self) -> None:
        self.start_x, self.start_y = self.x, self.y

    @property
    def armed(self) -> bool:
        return self.run >= self.params.arm_distance

    @property
    def speed(self) -> float:
        return self.params.speed

    def step(self, dt: float) -> None:
        if not self.alive:
            return
        self.x, self.y = project(self.x, self.y, self.heading, self.params.speed * dt)
        self.run += self.params.speed * dt
        if self.run >= self.params.max_run:
            self.alive = False

    def snapshot(self) -> dict:
        return {
            "id": self.torpedo_id,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "heading": round(self.heading, 1),
            "run": round(self.run, 0),
            "armed": self.armed,
            "alive": self.alive,
        }


@dataclass(frozen=True)
class Solution:
    """Where a torpedo fired now along the boat's heading would cross the target's track.

    ``error`` is how far (m) the target will be short of the crossing when the torpedo gets
    there: positive = fire later (the target has not arrived), negative = too late.
    """

    cross_x: float
    cross_y: float
    run: float  # m from the tube to the crossing
    time: float  # s the torpedo needs to get there
    target_x: float  # where the target will be when the torpedo reaches the crossing
    target_y: float
    error: float
    track_angle: float = 90.0  # deg off the target's axis the torpedo meets it (90 = beam)

    def snapshot(self) -> dict:
        return {
            "run": round(self.run, 0),
            "time": round(self.time, 1),
            "error": round(self.error, 0),
            "track_angle": round(self.track_angle, 0),
        }


def solution(
    sx: float,
    sy: float,
    s_heading: float,
    torpedo: TorpedoParams,
    tx: float,
    ty: float,
    t_heading: float,
    t_speed: float,
) -> Solution | None:
    """Fire-control geometry for a straight-running torpedo, ``None`` if the tracks do not cross
    ahead of the boat within the torpedo's run."""
    cross = ray_line_crossing(sx, sy, s_heading, tx, ty, t_heading)
    if cross is None:
        return None
    run, along = cross
    if run > torpedo.max_run:
        return None
    time = run / torpedo.speed
    travel = t_speed * time
    cx, cy = project(sx, sy, s_heading, run)
    px, py = project(tx, ty, t_heading, travel)
    return Solution(cx, cy, run, time, px, py, along - travel, track_angle(s_heading, t_heading))


@dataclass
class DepthCharge:
    """Dropped from a destroyer, sinks at a fixed rate and bursts at its set depth."""

    charge_id: int
    x: float
    y: float
    set_depth: float
    params: DepthChargeParams = DEPTH_CHARGE
    depth: float = 0.0
    burst: bool = False

    def step(self, dt: float) -> bool:
        """Sink; ``True`` on the step it reaches its depth and bursts."""
        self.depth = min(self.set_depth, self.depth + self.params.sink_rate * dt)
        if self.depth >= self.set_depth - 1e-9:
            self.burst = True
        return self.burst

    def effect_on(self, x: float, y: float, depth: float) -> float:
        """Hull damage (0..1) a burst here does to a boat at (x, y, depth); 1 inside the lethal
        radius, falling off linearly to nothing at the damage radius."""
        d = math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2 + (depth - self.set_depth) ** 2)
        if d <= self.params.lethal_radius:
            return 1.0
        if d >= self.params.damage_radius:
            return 0.0
        span = self.params.damage_radius - self.params.lethal_radius
        return self.params.damage * (1.0 - (d - self.params.lethal_radius) / span)

    def snapshot(self) -> dict:
        return {
            "id": self.charge_id,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "depth": round(self.depth, 1),
            "set_depth": round(self.set_depth, 1),
        }
