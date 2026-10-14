"""Classic ship maneuvering: propeller sets speed, rudder turns, both with inertia."""

from __future__ import annotations

import math
from dataclasses import dataclass

from jenesboat_v2.sim.geo import angle_diff, clamp, wrap_degrees
from jenesboat_v2.sim.params import KNOT, VesselParams

__all__ = ["KNOT", "Vessel", "VesselParams", "angle_diff", "clamp", "wrap_degrees"]


@dataclass
class Vessel:
    """A vessel in a flat world.  ``x`` east, ``y`` north, ``heading`` clockwise from north."""

    params: VesselParams
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    speed: float = 0.0  # m/s along heading, negative when going astern
    throttle: float = 0.0  # propeller order, -1 (full astern) .. 1 (full ahead)
    rudder: float = 0.0  # -1 (full port) .. 1 (full starboard)

    def set_throttle(self, value: float) -> None:
        self.throttle = clamp(value, -1.0, 1.0)

    def set_rudder(self, value: float) -> None:
        self.rudder = clamp(value, -1.0, 1.0)

    def max_speed_now(self) -> float:
        """Current speed ceiling; subclasses may reduce it (e.g. when submerged)."""
        return self.params.max_speed

    def target_speed(self) -> float:
        limit = self.max_speed_now()
        if self.throttle >= 0:
            return self.throttle * limit
        return self.throttle * limit * self.params.reverse_fraction

    @property
    def speed_knots(self) -> float:
        return self.speed / KNOT

    def turn_rate_now(self) -> float:
        """deg/s at the current rudder and speed.  A ship turns on a roughly constant radius,
        so the rate grows with speed; going astern the rudder works the other way."""
        rate = math.degrees(self.rudder * self.speed / self.params.turn_radius)
        return clamp(rate, -self.params.max_turn_rate, self.params.max_turn_rate)

    def step(self, dt: float) -> None:
        target = self.target_speed()
        delta = self.params.acceleration * dt
        if abs(target - self.speed) <= delta:
            self.speed = target
        elif target > self.speed:
            self.speed += delta
        else:
            self.speed -= delta

        self.heading = wrap_degrees(self.heading + self.turn_rate_now() * dt)

        rad = math.radians(self.heading)
        self.x += math.sin(rad) * self.speed * dt
        self.y += math.cos(rad) * self.speed * dt

    def contains(self, px: float, py: float, margin: float = 0.0) -> bool:
        """Is the point inside the hull box (length along heading, beam across)?"""
        rad = math.radians(self.heading)
        dx, dy = px - self.x, py - self.y
        along = dx * math.sin(rad) + dy * math.cos(rad)
        across = dx * math.cos(rad) - dy * math.sin(rad)
        return (
            abs(along) <= self.params.length / 2 + margin
            and abs(across) <= self.params.beam / 2 + margin
        )

    def snapshot(self) -> dict[str, float]:
        return {
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "heading": round(self.heading, 1),
            "speed_kn": round(self.speed_knots, 2),
            "throttle": round(self.throttle, 2),
            "rudder": round(self.rudder, 2),
        }
