"""Classic ship maneuvering: propeller sets speed, rudder turns, both with inertia."""

from __future__ import annotations

import math
from dataclasses import dataclass

KNOT = 0.514444  # metres per second


def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def wrap_degrees(deg: float) -> float:
    return deg % 360.0


def angle_diff(target: float, current: float) -> float:
    """Signed shortest turn from ``current`` to ``target`` in degrees (-180, 180]."""
    return (target - current + 180.0) % 360.0 - 180.0


@dataclass(frozen=True)
class VesselParams:
    max_speed: float  # m/s, full ahead
    acceleration: float = 0.3  # m/s^2 toward the ordered speed
    turn_rate: float = 6.0  # deg/s at full rudder with steerage way
    reverse_fraction: float = 0.5  # max astern speed as fraction of max_speed
    length: float = 60.0  # metres (drawing only)
    beam: float = 8.0  # metres (drawing only)


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

    def step(self, dt: float) -> None:
        target = self.target_speed()
        delta = self.params.acceleration * dt
        if abs(target - self.speed) <= delta:
            self.speed = target
        elif target > self.speed:
            self.speed += delta
        else:
            self.speed -= delta

        # The rudder only bites with water flowing over it.
        steerage = max(self.params.max_speed * 0.3, 1e-9)
        flow = min(1.0, abs(self.speed) / steerage)
        direction = 1.0 if self.speed >= 0 else -1.0
        self.heading = wrap_degrees(
            self.heading + self.rudder * self.params.turn_rate * flow * direction * dt
        )

        rad = math.radians(self.heading)
        self.x += math.sin(rad) * self.speed * dt
        self.y += math.cos(rad) * self.speed * dt

    def snapshot(self) -> dict[str, float]:
        return {
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "heading": round(self.heading, 1),
            "speed_kn": round(self.speed_knots, 2),
            "throttle": round(self.throttle, 2),
            "rudder": round(self.rudder, 2),
        }
