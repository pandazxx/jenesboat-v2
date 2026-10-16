"""Classic ship maneuvering: propeller sets speed, rudder turns, both with inertia."""

from __future__ import annotations

import math
from dataclasses import dataclass

from jenesboat_v2.sim.geo import angle_diff, clamp, wrap_degrees
from jenesboat_v2.sim.params import KNOT, RUDDER_MAX_ANGLE, TELEGRAPH, VesselParams

__all__ = ["KNOT", "Vessel", "VesselParams", "angle_diff", "clamp", "wrap_degrees"]


def telegraph_index(throttle: float) -> int:
    """The telegraph position nearest to a throttle fraction."""
    return min(range(len(TELEGRAPH)), key=lambda i: abs(TELEGRAPH[i][1] - throttle))


def telegraph_by_name(name: str) -> int | None:
    name = name.strip().upper()
    return next((i for i, (label, _) in enumerate(TELEGRAPH) if label == name), None)


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

    # --- the bridge view of the orders ---------------------------------------------------

    @property
    def telegraph(self) -> int:
        return telegraph_index(self.throttle)

    @property
    def telegraph_label(self) -> str:
        return TELEGRAPH[self.telegraph][0]

    def set_telegraph(self, index: int) -> None:
        index = max(0, min(len(TELEGRAPH) - 1, index))
        self.set_throttle(TELEGRAPH[index][1])

    def telegraph_step(self, delta: int) -> None:
        """One telegraph position ahead (+1) or astern (-1)."""
        self.set_telegraph(self.telegraph + delta)

    @property
    def rudder_angle(self) -> float:
        """Degrees, positive to starboard."""
        return self.rudder * RUDDER_MAX_ANGLE

    @property
    def rudder_label(self) -> str:
        angle = self.rudder_angle
        if abs(angle) < 0.5:
            return "RUDDER AMIDSHIPS"
        return f"RUDDER {abs(angle):2.0f} {'STBD' if angle > 0 else 'PORT'}"

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
            "telegraph": self.telegraph_label,
            "rudder": round(self.rudder, 2),
        }
