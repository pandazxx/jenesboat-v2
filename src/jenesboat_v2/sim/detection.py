"""Who sees whom.  Pure functions of the boat's state, a ship type and the light.

The boat sees ships with lookouts (surfaced), the periscope (periscope depth) or the
hydrophones (bearing only, slow and at least at periscope depth).  Ships see the boat when it
is surfaced, or its periscope/wake at periscope depth (further the faster it goes), and never
when it is deep.  ``light`` is 1.0 by day; night will scale the visual ranges down.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jenesboat_v2.sim.geo import bearing, distance
from jenesboat_v2.sim.params import DETECTION, DetectionParams, ShipType

if TYPE_CHECKING:
    from jenesboat_v2.sim.submarine import Submarine
    from jenesboat_v2.sim.world import Ship

VISUAL = "visual"
HYDROPHONE = "hydrophone"


@dataclass(frozen=True)
class Contact:
    """What the boat knows about one ship.  A hydrophone contact is the operator's estimate
    (position, course and speed from the bearing and the screw noise) and cannot tell the
    ship type; a visual contact is exact and identified."""

    ship_id: str
    method: str
    bearing: float
    type: str = ""
    range: float | None = None
    x: float | None = None
    y: float | None = None
    heading: float | None = None
    speed: float | None = None

    def snapshot(self) -> dict:
        data: dict = {
            "id": self.ship_id,
            "method": self.method,
            "bearing": round(self.bearing, 1),
        }
        if self.x is not None:
            data.update(
                type=self.type,
                range=round(self.range or 0.0, 0),
                x=round(self.x or 0.0, 1),
                y=round(self.y or 0.0, 1),
                heading=round(self.heading or 0.0, 1),
                speed_kn=round((self.speed or 0.0) / 0.514444, 2),
            )
        return data


def sub_visual_range(sub: Submarine, ship_type: ShipType, light: float = 1.0) -> float:
    """How far the boat can see a ship of this type right now (0 when blind)."""
    if sub.surfaced:
        base = sub.spec.lookout_range
    elif sub.periscope_usable:
        base = sub.spec.periscope_range
    else:
        return 0.0
    return base * ship_type.visibility * light


def sub_hydrophone_range(sub: Submarine, ship_type: ShipType) -> float:
    return sub.spec.hydrophone_range if sub.hydrophone_usable else 0.0


def ship_detection_range(
    sub: Submarine, ship_type: ShipType, light: float = 1.0, det: DetectionParams = DETECTION
) -> float:
    """How far a ship of this type can see the boat in its current state (0 = invisible)."""
    if sub.surfaced:
        base = det.surfaced_range
    elif sub.depth <= det.periscope_max_depth:
        excess = max(0.0, abs(sub.speed) - det.periscope_quiet_speed)
        base = det.periscope_range + det.periscope_speed_penalty * excess
    else:
        return 0.0
    return base * ship_type.lookout * light


def observe(sub: Submarine, ship: Ship, light: float = 1.0) -> Contact | None:
    """The boat's contact on ``ship``, visual if possible, else hydrophone, else ``None``."""
    d = distance(sub.x, sub.y, ship.x, ship.y)
    brg = bearing(sub.x, sub.y, ship.x, ship.y)
    if d <= sub_visual_range(sub, ship.type, light):
        return Contact(
            ship_id=ship.ship_id,
            method=VISUAL,
            bearing=brg,
            type=ship.type.name,
            range=d,
            x=ship.x,
            y=ship.y,
            heading=ship.heading,
            speed=ship.speed,
        )
    if d <= sub_hydrophone_range(sub, ship.type) and abs(ship.speed) > 0.1:
        return Contact(
            ship_id=ship.ship_id,
            method=HYDROPHONE,
            bearing=brg,
            type="",
            range=d,
            x=ship.x,
            y=ship.y,
            heading=ship.heading,
            speed=ship.speed,
        )
    return None


def ship_sees_sub(
    sub: Submarine, ship: Ship, light: float = 1.0, det: DetectionParams = DETECTION
) -> bool:
    return distance(sub.x, sub.y, ship.x, ship.y) <= ship_detection_range(
        sub, ship.type, light, det
    )
