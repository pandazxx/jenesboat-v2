"""Escort AI: destroyers keep station on the convoy, listen with active sonar and, once the
boat is found, split into hunters (go and drop depth charges) and screens (stay between the
boat and the fleet).  They go back to formation when the track has been lost for a while.

Everything here is a function of the ``World`` it is handed; it owns no state besides the
per-ship ``EscortState`` and the group's ``Datum`` (the best guess of where the boat is).
The numbers come from ``world.rules``; the behaviours a difficulty level can swap are the
``escort_search`` and ``escort_evade`` strategy slots (``sim/difficulty.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from jenesboat_v2.sim import ai
from jenesboat_v2.sim.difficulty import pick, strategy
from jenesboat_v2.sim.geo import angle_diff, bearing, clamp, distance, project, wrap_degrees
from jenesboat_v2.sim.params import ESCORT_AI, DepthChargeParams, EscortAIParams, SonarParams
from jenesboat_v2.sim.weapons import DepthCharge, Torpedo

if TYPE_CHECKING:
    from jenesboat_v2.sim.world import Ship, World

FORMATION = "formation"
HUNT = "hunt"
SCREEN = "screen"

FRESH_DATUM = 60.0  # s, a fix this young is good enough to drop charges on
MERCHANT_WARNING_RANGE = 8_000.0  # m, merchants this near a contact are warned by radio
FIRST_CHARGE_DELAY = 10.0  # s, about how long the first charge takes to sink to the boat
TORPEDO_DATUM_HOLDOFF = 30.0  # s, a torpedo hit does not overrule a younger fix than this


@dataclass
class EscortState:
    mode: str = FORMATION
    next_ping: float = 0.0
    charges: int = -1  # -1: filled from the rules' magazine when the ship joins a world
    drop_left: int = 0  # charges still to go in the current pattern
    drop_timer: float = 0.0
    cooldown_until: float = -math.inf
    search_leg: int = 0
    sonar_range: float = 0.0  # m, what the set could hear right now (for the HUD and tests)
    evading: int | None = None  # id of the torpedo the ship is dodging
    evade_at: float = 0.0  # s, when the helm answers (after the reaction time)


@dataclass
class Datum:
    """Where the escorts think the boat is, and how old that is."""

    x: float
    y: float
    t: float
    reason: str
    vx: float = 0.0  # m/s, the boat's estimated velocity (from the recent fixes)
    vy: float = 0.0
    fixes: tuple[tuple[float, float, float], ...] = ()  # (t, x, y) of recent sonar/sight fixes

    def predict(self, t: float, lead_limit: float = ESCORT_AI.lead_limit) -> tuple[float, float]:
        """Where the boat should be at time ``t`` if it holds the course and speed the fixes
        show (never carried further than ``lead_limit`` past the last fix)."""
        dt = clamp(t - self.t, 0.0, lead_limit)
        return self.x + self.vx * dt, self.y + self.vy * dt


# --- sensing -------------------------------------------------------------------------------


def sonar_range(world: World, ship: Ship, sonar: SonarParams | None = None) -> float:
    """What this ship's active sonar can hear right now: reduced by the noise of the other
    ships around it (its own convoy), by its own speed, and for a creeping boat."""
    sonar = world.rules.sonar if sonar is None else sonar
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
    world.datum = _refresh_datum(world.datum, x, y, t, reason, world.rules.escort_ai)
    if fresh:
        world.emit("escort_alarm", reason=reason, by=by)
    # The convoy is told and runs for the screen.
    world.alert_group(x, y, "escort", by, quiet=True, radius=MERCHANT_WARNING_RANGE)


def _refresh_datum(
    old: Datum | None, x: float, y: float, t: float, reason: str, p: EscortAIParams = ESCORT_AI
) -> Datum:
    """A new fix, with the boat's course and speed worked out from the recent ones (the fixes
    are a few tens of metres out, so only a long baseline gives a usable velocity)."""
    if reason == "torpedo":  # a rough guess: no fixes, no velocity
        return Datum(x, y, t, reason)
    history = tuple(f for f in (old.fixes if old else ()) if t - f[0] <= p.track_window)
    fixes = (*history, (t, x, y))
    if len(fixes) < 3 or t - fixes[0][0] < p.track_min_baseline:
        return Datum(x, y, t, reason, 0.0, 0.0, fixes)
    # Least-squares line through the fixes: the position now and the velocity, with the noise
    # of the individual fixes averaged out.
    n = len(fixes)
    mt = sum(f[0] for f in fixes) / n
    stt = sum((f[0] - mt) ** 2 for f in fixes)
    vx = sum((f[0] - mt) * f[1] for f in fixes) / stt
    vy = sum((f[0] - mt) * f[2] for f in fixes) / stt
    speed = math.hypot(vx, vy)
    if speed > p.max_track_speed:
        vx, vy = vx * p.max_track_speed / speed, vy * p.max_track_speed / speed
    x = sum(f[1] for f in fixes) / n + vx * (t - mt)
    y = sum(f[2] for f in fixes) / n + vy * (t - mt)
    return Datum(x, y, t, reason, vx, vy, fixes)


def _ping(world: World, ship: Ship, state: EscortState) -> None:
    sonar = world.rules.sonar
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


def escort_station(
    cx: float, cy: float, course: float, rank: int, p: EscortAIParams = ESCORT_AI
) -> tuple[float, float]:
    """Formation station of the escort of this ``rank``: ahead of the convoy centre and off
    its flank, alternating sides, a station further out for each pair."""
    side = 1.0 if rank % 2 == 0 else -1.0
    sx, sy = project(cx, cy, course, p.station_ahead)
    return project(sx, sy, course + 90.0, side * (1 + rank // 2) * p.station_abeam)


def _formation(world: World, ship: Ship, rank: int, p: EscortAIParams) -> None:
    cx, cy, course, speed = _convoy(world, ship)
    sx, sy = escort_station(cx, cy, course, rank, p)
    _keep_station(ship, sx, sy, course, speed, p)


def _screen(world: World, ship: Ship, rank: int, count: int, p: EscortAIParams) -> None:
    datum = world.datum
    assert datum is not None
    cx, cy, _, speed = _convoy(world, ship)
    toward = bearing(cx, cy, datum.x, datum.y)
    sx, sy = project(cx, cy, toward, p.screen_distance)
    sx, sy = project(sx, sy, toward + 90.0, (rank - (count - 1) / 2) * p.screen_abeam)
    _keep_station(ship, sx, sy, toward, speed, p)


def _drop(world: World, ship: Ship, p: EscortAIParams, depth_params: DepthChargeParams) -> None:
    """One charge of the pattern.  It is aimed where the boat will be when the charge has
    sunk to its depth (the datum's predicted path), a little to one side or the other, and
    each charge is set deeper than the last so the pattern covers the band the boat is in.
    The projectors throw up to ``throw_range``, so the ship need not cross the boat's path;
    a charge whose aim point is out of range is not thrown."""
    state = ship.escort
    sub = world.player
    datum = world.datum
    assert datum is not None
    n = depth_params.pattern_size
    k = n - state.drop_left  # 0 for the first charge of the run
    layer = k / (n - 1) if n > 1 else 0.5
    set_depth = clamp(
        sub.depth + depth_params.depth_error * (2.0 * layer - 1.0),
        depth_params.min_depth,
        sub.spec.max_depth,
    )
    state.drop_left -= 1
    state.drop_timer = depth_params.drop_interval
    ax, ay = datum.predict(world.time + set_depth / depth_params.sink_rate, p.lead_limit)
    speed = math.hypot(datum.vx, datum.vy)
    across = (
        math.degrees(math.atan2(datum.vx, datum.vy)) + 90.0
        if speed > 0.1
        else world.rng.uniform(0.0, 360.0)
    )
    side = 1.0 if k % 2 == 0 else -1.0
    ax, ay = project(ax, ay, across, side * world.rng.uniform(0.0, 1.0) * depth_params.scatter)
    if distance(ship.x, ship.y, ax, ay) > depth_params.throw_range:
        return
    world.next_charge_id += 1
    world.depth_charges.append(DepthCharge(world.next_charge_id, ax, ay, set_depth, depth_params))
    state.charges -= 1


def _hunt(world: World, ship: Ship, dt: float, p: EscortAIParams) -> None:
    state, datum, t = ship.escort, world.datum, world.time
    depth_params = world.rules.depth_charge
    assert datum is not None
    if state.drop_left > 0:  # mid-run: hold course and speed while the projectors fire
        ship.set_rudder(0.0)
        state.drop_timer -= dt
        if state.charges <= 0:
            state.drop_left = 0
        elif state.drop_timer <= 0.0:
            _drop(world, ship, p, depth_params)
        return
    # Chase where the boat will be when we get there, not where it was.
    d = distance(ship.x, ship.y, datum.x, datum.y)
    px, py = datum.predict(t + d / max(ship.speed, p.approach_speed), p.lead_limit)
    fresh = t - datum.t <= FRESH_DATUM
    if (
        fresh
        and distance(ship.x, ship.y, *datum.predict(t + FIRST_CHARGE_DELAY, p.lead_limit))
        <= depth_params.throw_range
        and t >= state.cooldown_until
        and state.charges > 0
    ):
        state.cooldown_until = t + depth_params.pattern_cooldown
        state.drop_left = depth_params.pattern_size
        world.emit("depth_charge_run", ship=ship.ship_id, charges=state.charges)
        _drop(world, ship, p, depth_params)
        return
    if fresh:
        _goto(ship, px, py, p.attack_speed if d > p.approach_range else p.approach_speed)
        return
    pick(world.level, "escort_search")(world, ship, p)


# --- strategies ----------------------------------------------------------------------------


@strategy("escort_search", "box")
def box_search(world: World, ship: Ship, p: EscortAIParams) -> None:
    """No recent fix: sweep a square around the datum that widens as the track gets older."""
    state, datum, t = ship.escort, world.datum, world.time
    assert datum is not None
    radius = clamp(p.search_start + p.search_growth * (t - datum.t), p.search_start, p.search_max)
    angle = state.search_leg * 90.0 + 45.0
    wx, wy = project(datum.x, datum.y, angle, radius)
    if distance(ship.x, ship.y, wx, wy) < p.station_tolerance * 0.8:
        state.search_leg += 1
    _goto(ship, wx, wy, p.search_speed)


@strategy("escort_evade", "none")
def no_evasion(world: World, ship: Ship, dt: float) -> bool:
    """The M2 escort: it never notices a torpedo."""
    return False


def closest_approach(ship: Ship, torpedo: Torpedo) -> tuple[float, float]:
    """``(distance, seconds)`` of the torpedo's closest pass to the ship if both hold course
    and speed; the seconds are negative once it is moving away."""
    rad = math.radians(torpedo.heading)
    tvx, tvy = math.sin(rad) * torpedo.speed, math.cos(rad) * torpedo.speed
    rad = math.radians(ship.heading)
    svx, svy = math.sin(rad) * ship.speed, math.cos(rad) * ship.speed
    rx, ry = ship.x - torpedo.x, ship.y - torpedo.y
    vx, vy = svx - tvx, svy - tvy  # the ship's motion as seen from the torpedo
    vv = vx * vx + vy * vy
    if vv < 1e-9:
        return math.hypot(rx, ry), math.inf
    t = -(rx * vx + ry * vy) / vv
    return math.hypot(rx + vx * t, ry + vy * t), t


def comb_heading(ship: Ship, torpedo: Torpedo, comb_angle: float) -> float:
    """The course that combs the torpedo's track: nearly parallel to it, ``comb_angle`` off
    toward the side of the track the ship is already on, running with the torpedo or
    toward it, whichever is the smaller turn from the present heading."""
    d = torpedo.heading
    rad = math.radians(d)
    ux, uy = math.sin(rad), math.cos(rad)
    rx, ry = ship.x - torpedo.x, ship.y - torpedo.y
    side = rx * uy - ry * ux  # > 0: the ship is to the right of the track
    if abs(side) < 1.0:  # dead on the track: open toward where the bow already points
        rad = math.radians(ship.heading)
        side = math.sin(rad) * uy - math.cos(rad) * ux
    sign = 1.0 if side >= 0 else -1.0
    with_it = wrap_degrees(d + sign * comb_angle)
    against = wrap_degrees(d + 180.0 - sign * comb_angle)
    return min((with_it, against), key=lambda h: abs(angle_diff(h, ship.heading)))


def _torpedo_threat(world: World, ship: Ship) -> tuple[Torpedo, float, float] | None:
    """The nearest running torpedo this ship can hear (or see the wake of) that will pass
    closer than the threat width before it runs out, with its closest approach."""
    ev = world.rules.evasion
    found = None
    for torpedo in world.torpedoes:
        if not torpedo.alive:
            continue
        d = distance(ship.x, ship.y, torpedo.x, torpedo.y)
        wake = torpedo.params.wake_visible_range * ship.type.lookout * world.light
        if d > max(ev.hear_range, wake):
            continue
        cpa, seconds = closest_approach(ship, torpedo)
        if seconds <= 0.0 or cpa > ev.threat_width:
            continue
        if torpedo.speed * seconds > torpedo.params.max_run - torpedo.run:
            continue  # it will run out first
        if found is None or d < found[0]:
            found = (d, torpedo, cpa, seconds)
    return None if found is None else found[1:]


@strategy("escort_evade", "comb")
def comb_the_track(world: World, ship: Ship, dt: float) -> bool:
    """Hear a torpedo that will pass too close and, after the reaction time, turn hard to
    comb its track at full speed until it has gone by or run out, then carry on."""
    state = ship.escort
    torpedo = next((t for t in world.torpedoes if t.torpedo_id == state.evading and t.alive), None)
    if torpedo is not None and closest_approach(ship, torpedo)[1] <= 0.0:
        torpedo = None  # it went by
    if torpedo is None:
        state.evading = None
        threat = _torpedo_threat(world, ship)
        if threat is None:
            return False
        torpedo, cpa, seconds = threat
        state.evading = torpedo.torpedo_id
        state.evade_at = world.time + world.rules.evasion.reaction_time
        world.emit(
            "torpedo_seen",
            ship=ship.ship_id,
            torpedo=torpedo.torpedo_id,
            cpa=round(cpa),
            seconds=round(seconds),
        )
    if world.time < state.evade_at:
        return False  # still reacting: carry on as before
    ai.steer(ship, comb_heading(ship, torpedo, world.rules.evasion.comb_angle))
    ship.set_throttle(1.0)
    return True


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


def step(world: World, dt: float, p: EscortAIParams | None = None) -> None:
    """Run one tick of every escort and set the merchants' shelter points."""
    p = world.rules.escort_ai if p is None else p
    escorts = sorted(
        (s for s in world.active_ships if s.kind == "military"), key=lambda s: s.ship_id
    )
    if not escorts:
        return
    evade = pick(world.level, "escort_evade")
    for e in escorts:
        if e.escort.charges < 0:
            e.escort.charges = world.rules.depth_charge.magazine
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
        if evade(world, e, dt):
            continue
        if datum is None or mode == FORMATION:
            _formation(world, e, rank, p)
        elif mode == HUNT:
            _hunt(world, e, dt, p)
        else:
            _screen(world, e, screens.index(e), len(screens), p)
    _shelter(world, escorts, p)
