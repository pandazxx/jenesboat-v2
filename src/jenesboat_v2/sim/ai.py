"""Ship behaviours.  Milestone 0 only knows how to cruise on a fixed course."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jenesboat_v2.sim.vessel import angle_diff, clamp

if TYPE_CHECKING:
    from jenesboat_v2.sim.world import Ship


def cruise(ship: Ship) -> None:
    """Hold ``ship.course`` at ``ship.cruise_speed`` using rudder and throttle orders."""
    error = angle_diff(ship.course, ship.heading)
    ship.set_rudder(clamp(error / 30.0, -1.0, 1.0))
    if ship.params.max_speed > 0:
        ship.set_throttle(clamp(ship.cruise_speed / ship.params.max_speed, 0.0, 1.0))
