"""Ship behaviours: merchants cruise their route and run from a sighted threat."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jenesboat_v2.sim.geo import angle_diff, bearing, clamp, distance, wrap_degrees
from jenesboat_v2.sim.params import ESCORT_AI, MERCHANT_AI, MerchantAIParams

if TYPE_CHECKING:
    from jenesboat_v2.sim.world import Ship


def steer(ship: Ship, desired_heading: float, gain: float = 1.0 / 20.0) -> None:
    """Rudder proportional to the heading error, full rudder beyond 20 degrees."""
    ship.set_rudder(clamp(angle_diff(desired_heading, ship.heading) * gain, -1.0, 1.0))


def cruise(ship: Ship) -> None:
    """Hold ``ship.course`` at ``ship.cruise_speed`` using rudder and throttle orders."""
    steer(ship, ship.course)
    if ship.params.max_speed > 0:
        ship.set_throttle(clamp(ship.cruise_speed / ship.params.max_speed, 0.0, 1.0))


def flee_heading(ship: Ship, t: float, params: MerchantAIParams = MERCHANT_AI) -> float:
    """Directly away from the threat, plus this ship's spread bias and the current zigzag leg."""
    away = wrap_degrees(bearing(ship.threat_x, ship.threat_y, ship.x, ship.y))
    leg = int((t - ship.alert_since) // params.zigzag_period)
    zig = params.zigzag_angle if leg % 2 == 0 else -params.zigzag_angle
    return wrap_degrees(away + ship.spread * params.spread_angle + zig)


def shelter_heading(ship: Ship, params: MerchantAIParams = MERCHANT_AI) -> float:
    """Course for a merchant that has a shelter point behind an escort.  Never more than 90
    degrees from directly away from the threat: running for cover must not mean running at
    the boat."""
    assert ship.shelter is not None
    sx, sy = ship.shelter
    away = bearing(ship.threat_x, ship.threat_y, ship.x, ship.y)
    behind = distance(ship.threat_x, ship.threat_y, sx, sy) > distance(
        ship.threat_x, ship.threat_y, ship.x, ship.y
    )
    if behind or distance(ship.x, ship.y, sx, sy) <= ESCORT_AI.shelter_radius:
        # Already on the far side of the escort: keep going away.
        return wrap_degrees(away + ship.spread * params.spread_angle / 2)
    to_shelter = bearing(ship.x, ship.y, sx, sy)  # exposed: slip in behind the escort
    return wrap_degrees(away + clamp(angle_diff(to_shelter, away), -90.0, 90.0))


def flee(ship: Ship, t: float, params: MerchantAIParams = MERCHANT_AI) -> None:
    """Full speed away from the threat, zigzagging, spread out from the neighbours.  With an
    escort to shelter behind, run for the spot behind it instead, and hold the far side of it
    once there."""
    if ship.shelter is not None:
        steer(ship, shelter_heading(ship, params))
        ship.set_throttle(1.0)
        return
    steer(ship, flee_heading(ship, t, params))
    ship.set_throttle(1.0)


def merchant(ship: Ship, t: float, params: MerchantAIParams = MERCHANT_AI) -> None:
    if ship.alerted(t):
        flee(ship, t, params)
    else:
        cruise(ship)
