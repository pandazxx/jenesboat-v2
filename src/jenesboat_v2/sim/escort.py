"""Escort AI: destroyers keep station on the convoy, listen with active sonar and, once the
boat is found, split into hunters (go and drop depth charges) and screens (stay between the
boat and the fleet).  They go back to formation when the track has been lost for a while.

Everything here is a function of the ``World`` it is handed; it owns no state besides the
per-ship ``EscortState`` and the group's ``Datum`` (the best guess of where the boat is).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from jenesboat_v2.sim import ai
from jenesboat_v2.sim.geo import bearing, clamp, distance, project
from jenesboat_v2.sim.params import (
    DEPTH_CHARGE,
    ESCORT_AI,
    SONAR_ASDIC,
    DepthChargeParams,
    EscortAIParams,
    SonarParams,
)
from jenesboat_v2.sim.weapons import DepthCharge

if TYPE_CHECKING:
    from jenesboat_v2.sim.world import Ship, World

FORMATION = "formation"
HUNT = "hunt"
SCREEN = "screen"

FRESH_DATUM = 60.0  # s, a fix this young is good enough to drop charges on
MERCHANT_WARNING_RANGE = 8_000.0  # m, merchants this near a contact are warned by radio
TORPEDO_DATUM_HOLDOFF = 30.0  # s, a torpedo hit does not overrule a younger fix than this


@dataclass
class EscortState:
    mode: str = FORMATION
    next_ping: float = 0.0
    charges: int = DEPTH_CHARGE.magazine
    drop_left: int = 0  # charges still to go in the current pattern
    drop_timer: float = 0.0
    cooldown_until: float = -math.inf
    search_leg: int = 0
    sonar_range: float = 0.0  # m, what the set could hear right now (for the HUD and tests)


@dataclass
class Datum:
    """Where the escorts think the boat is, and how old that is."""

    x: float
    y: float
    t: float
    reason: str


# --- sensing -------------------------------------------------------------------------------


def sonar_range(world: World, ship: Ship, sonar: SonarParams = SONAR_ASDIC) -> float:
    """What this ship's active sonar can hear right now: reduced by the noise of the other
    ships around it (its own convoy), by its own speed, and for a creeping boat."""
    neighbours = sum(
        1
        for other in world.active_ships
        if other is not ship
        and distance(ship.x, ship.y, other.x, other.y) <= sonar.interference_radius
    )
    reach = sonar.range
    reach *= clamp(1.0 - sonar.interference_per_ship * neighbours, sonar.interference_floor, 1.0)
    if abs(ship.speed) > sonar.own_noise_speed:
        reach *= sonar.own_noise_factor
    if abs(world.player.speed) <= sonar.quiet_speed:
        reach *= sonar.quiet_factor
    return reach


def report(world: World, x: float, y: float, reason: str, by: str) -> None:
    """Something told the escorts where the boat is (sonar, a sighting, a torpedo hit).  The
    first report starts the engagement; later ones just refresh the datum."""
    t = world.time
    if reason == "torpedo" and world.datum and t - world.datum.t < TORPEDO_DATUM_HOLDOFF:
        return
    fresh = world.datum is None
    world.datum = Datum(x, y, t, reason)
    if fresh:
        world.emit("escort_alarm", reason=reason, by=by)
    # The convoy is told and runs for the screen.
    world.alert_group(x, y, "escort", by, quiet=True, radius=MERCHANT_WARNING_RANGE)


def _ping(world: World, ship: Ship, state: EscortState, sonar: SonarParams = SONAR_ASDIC) -> None:
    if world.time < state.next_ping:
        return
    state.next_ping = world.time + sonar.ping_interval
    state.sonar_range = sonar_range(world, ship, sonar)
    sub = world.player
    d = distance(ship.x, ship.y, sub.x, sub.y)
    if sonar.min_range <= d <= state.sonar_range:
        ex = world.rng.uniform(-sonar.position_error, sonar.position_error)
        ey = world.rng.uniform(-sonar.position_error, sonar.position_error)
        report(world, sub.x + ex, sub.y + ey, "sonar", ship.ship_id)


# --- group decisions -----------------------------------------------------------------------


def hunters_wanted(escorts: int, params: EscortAIParams = ESCORT_AI) -> int:
    return clamp(escorts // params.hunters_per_escort, 1, params.max_hunters) if escorts else 0


def _assign_roles(world: World, escorts: list[Ship], params: EscortAIParams) -> None:
    """The escorts nearest the datum hunt; the rest screen.  Called every tick, it only
    changes anything at the start of an engagement or when a hunter has been lost."""
    datum = world.datum
    assert datum is not None
    hunters = [e for e in escorts if e.escort.mode == HUNT]
    missing = hunters_wanted(len(escorts), params) - len(hunters)
    if missing <= 0:
        return
    pool = [e for e in escorts if e.escort.mode != HUNT]
    pool.sort(key=lambda e: distance(e.x, e.y, datum.x, datum.y))
    for e in pool[:missing]:
        e.escort.mode = HUNT
    for e in pool[missing:]:
        e.escort.mode = SCREEN
    if missing == hunters_wanted(len(escorts), params):  # a fresh engagement
        world.emit(
            "escort_split",
            hunters=[e.ship_id for e in escorts if e.escort.mode == HUNT],
            screens=[e.ship_id for e in escorts if e.escort.mode == SCREEN],
        )


def _stand_down(world: World, escorts: list[Ship]) -> None:
    world.datum = None
    for e in escorts:
        e.escort.mode = FORMATION
        e.escort.drop_left = 0
    world.emit("escort_stand_down")


# --- ship behaviours -----------------------------------------------------------------------


def _goto(ship: Ship, x: float, y: float, speed: float) -> None:
    ai.steer(ship, bearing(ship.x, ship.y, x, y))
    ship.set_throttle(clamp(speed / ship.params.max_speed, 0.0, 1.0))


def _convoy(world: World, escort: Ship) -> tuple[float, float, float, float]:
    """Centre, route course and speed of the merchants still afloat (the escort's own track
    when there are none)."""
    ships = [s for s in world.active_ships if s.kind == "merchant"]
    if not ships:
        return escort.x, escort.y, escort.course, escort.cruise_speed
    n = len(ships)
    return (
        sum(s.x for s in ships) / n,
        sum(s.y for s in ships) / n,
        ships[0].course,
        sum(s.cruise_speed for s in ships) / n,
    )


def _keep_station(ship: Ship, sx: float, sy: float, facing: float, speed: float, p) -> None:
    d = distance(ship.x, ship.y, sx, sy)
    if d > p.station_tolerance:
        _goto(ship, sx, sy, clamp(speed + 0.02 * d, speed, p.attack_speed))
    else:
        ai.steer(ship, facing)
        ship.set_throttle(clamp(speed / ship.params.max_speed, 0.0, 1.0))


def _formation(world: World, ship: Ship, rank: int, p: EscortAIParams) -> None:
    cx, cy, course, speed = _convoy(world, ship)
    side = 1.0 if rank % 2 == 0 else -1.0
    sx, sy = project(cx, cy, course, p.station_ahead)
    sx, sy = project(sx, sy, course + 90.0, side * p.station_abeam)
    _keep_station(ship, sx, sy, course, speed, p)


def _screen(world: World, ship: Ship, rank: int, count: int, p: EscortAIParams) -> None:
    datum = world.datum
    assert datum is not None
    cx, cy, _, speed = _convoy(world, ship)
    toward = bearing(cx, cy, datum.x, datum.y)
    sx, sy = project(cx, cy, toward, p.screen_distance)
    sx, sy = project(sx, sy, toward + 90.0, (rank - (count - 1) / 2) * p.screen_abeam)
    _keep_station(ship, sx, sy, toward, speed, p)


def _drop(world: World, ship: Ship, depth_params: DepthChargeParams) -> None:
    state = ship.escort
    sub = world.player
    set_depth = clamp(
        sub.depth + world.rng.uniform(-depth_params.depth_error, depth_params.depth_error),
        depth_params.min_depth,
        sub.spec.max_depth,
    )
    world.next_charge_id += 1
    world.depth_charges.append(
        DepthCharge(world.next_charge_id, ship.x, ship.y, set_depth, depth_params)
    )
    state.charges -= 1
    state.drop_left -= 1
    state.drop_timer = depth_params.drop_interval


def _hunt(
    world: World,
    ship: Ship,
    dt: float,
    p: EscortAIParams,
    depth_params: DepthChargeParams = DEPTH_CHARGE,
) -> None:
    state, datum, t = ship.escort, world.datum, world.time
    assert datum is not None
    if state.drop_left > 0:  # mid-run: hold course and speed over the datum
        ship.set_rudder(0.0)
        state.drop_timer -= dt
        if state.drop_timer <= 0.0 and state.charges > 0:
            _drop(world, ship, depth_params)
        elif state.charges <= 0:
            state.drop_left = 0
        return
    d = distance(ship.x, ship.y, datum.x, datum.y)
    fresh = t - datum.t <= FRESH_DATUM
    if fresh and d <= depth_params.drop_radius and t >= state.cooldown_until and state.charges > 0:
        state.cooldown_until = t + depth_params.pattern_cooldown
        state.drop_left = depth_params.pattern_size
        world.emit("depth_charge_run", ship=ship.ship_id, charges=state.charges)
        _drop(world, ship, depth_params)
        return
    if fresh:
        _goto(ship, datum.x, datum.y, p.attack_speed if d > p.approach_range else p.approach_speed)
        return
    # No recent fix: sweep a widening square around the datum.
    radius = clamp(p.search_start + p.search_growth * (t - datum.t), p.search_start, p.search_max)
    angle = state.search_leg * 90.0 + 45.0
    wx, wy = project(datum.x, datum.y, angle, radius)
    if distance(ship.x, ship.y, wx, wy) < p.station_tolerance * 0.8:
        state.search_leg += 1
    _goto(ship, wx, wy, p.search_speed)


def _shelter(world: World, escorts: list[Ship], p: EscortAIParams) -> None:
    """Alerted merchants head for the nearest escort that is not off hunting."""
    guards = [e for e in escorts if e.escort.mode != HUNT]
    for ship in world.active_ships:
        if ship.kind != "merchant":
            continue
        ship.shelter = None
        if not ship.alerted(world.time) or not guards:
            continue
        guard = min(guards, key=lambda e: distance(e.x, e.y, ship.x, ship.y))
        away = bearing(ship.threat_x, ship.threat_y, guard.x, guard.y)
        ship.shelter = project(guard.x, guard.y, away, p.shelter_distance)


def step(world: World, dt: float, p: EscortAIParams = ESCORT_AI) -> None:
    """Run one tick of every escort and set the merchants' shelter points."""
    escorts = sorted(
        (s for s in world.active_ships if s.kind == "military"), key=lambda s: s.ship_id
    )
    if not escorts:
        return
    for e in escorts:
        _ping(world, e, e.escort)
    datum = world.datum
    if datum is not None and world.time - datum.t > p.lose_track_time:
        _stand_down(world, escorts)
        datum = None
    if datum is not None:
        _assign_roles(world, escorts, p)
    screens = [e for e in escorts if e.escort.mode == SCREEN]
    for rank, e in enumerate(escorts):
        mode = e.escort.mode
        if datum is None or mode == FORMATION:
            _formation(world, e, rank, p)
        elif mode == HUNT:
            _hunt(world, e, dt, p)
        else:
            _screen(world, e, screens.index(e), len(screens), p)
    _shelter(world, escorts, p)
