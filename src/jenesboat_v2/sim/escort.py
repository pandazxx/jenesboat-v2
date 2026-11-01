"""Escort AI: destroyers keep station on the convoy, listen with active sonar and, once the
boat is found, split into hunters (go and drop depth charges) and screens (stay between the
boat and the fleet).  They stand down when the track is lost, when the hunt has taken them
too far from the convoy or too long, or when the racks are empty.

The sonar gives one *effective reach* per ping (``effective_reach``): the sheet's range
scaled by the boat's aspect, speed and depth relative to the thermocline and by the set's
own state, zero behind a noise shadow (a friendly ship, the cloud a pattern leaves, another
escort's wake), heard only inside the cone the set can be trained over and outside the blind
zone under the keel.  A fix is a random point in a ring that grows as the echo gets fainter.

The hunt is a cycle: attack while the fix is fresh, attack the dead-reckoned position once
when it is stale (the *datum attack*), assume a straight flight away and attack along it a
few times (the *blind lead*), then search; the track is lost when the search has heard
nothing for ``lose_track_time``.  The charges are set in depth bands; a band is confirmed by
a pattern that does real damage and left for the next after one that does not.

Everything here is a function of the ``World`` it is handed; it owns no state besides the
per-ship ``EscortState`` and the group's ``Datum`` (the best guess of where the boat is).
The numbers come from ``world.rules``; the behaviours a difficulty level can swap are the
``escort_search`` and ``escort_evade`` strategy slots (``sim/difficulty.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from jenesboat_v2.sim import ai
from jenesboat_v2.sim.difficulty import pick, strategy
from jenesboat_v2.sim.geo import angle_diff, bearing, clamp, distance, project, wrap_degrees
from jenesboat_v2.sim.params import (
    ESCORT_AI,
    KNOT,
    DepthChargeParams,
    EscortAIParams,
    SonarParams,
)
from jenesboat_v2.sim.weapons import DepthCharge, Torpedo

if TYPE_CHECKING:
    from jenesboat_v2.sim.world import Ship, World

FORMATION = "formation"
HUNT = "hunt"
SCREEN = "screen"

# What a ship is up to, for the HUD and the log (the mode says which job it has).
INTENT_FORMATION = "formation"
INTENT_RETURNING = "returning"
INTENT_SCREENING = "screening"
INTENT_HUNTING = "hunting"  # steering for the predicted position
INTENT_ATTACKING = "attacking"  # a run is on
INTENT_SWEEPING = "sweeping"  # down the torpedo's track
INTENT_SEARCHING = "searching"  # no fix worth attacking: the search pattern

FRESH_DATUM = 60.0  # s, a fix this young is good enough to drop charges on
MERCHANT_WARNING_RANGE = 8_000.0  # m, merchants this near a contact are warned by radio
FIRST_CHARGE_DELAY = 10.0  # s, about how long the first charge takes to sink to the boat
TORPEDO_DATUM_HOLDOFF = 30.0  # s, a torpedo does not overrule a younger fix than this
POINT = "point"
LINE = "line"
STAND_DOWN_LOST = "lost"  # no echo for lose_track_time after the hunter arrived
STAND_DOWN_LEASH = "leash"  # the hunt took a hunter too far from the convoy
STAND_DOWN_TIME = "time"  # the hunt has gone on too long
STAND_DOWN_CHARGES = "charges"  # the racks are empty


@dataclass
class EscortState:
    mode: str = FORMATION
    intent: str = INTENT_FORMATION
    next_ping: float = 0.0
    charges: int = -1  # -1: filled from the rules' magazine when the ship joins a world
    drop_left: int = 0  # charges still to go in the current pattern
    drop_timer: float = 0.0
    cooldown_until: float = -math.inf
    run_started: float = 0.0  # s, when the current run began (the run-over release's clock)
    search_leg: int = 0
    sonar_range: float = 0.0  # m, the effective reach of the last ping (HUD and tests)
    echo: bool = False  # the last ping came back
    echo_why: str = "no ping yet"  # why it did not, or "echo"
    fast_until: float = -math.inf  # s, the set is settling after a sprint until then
    evading: int | None = None  # id of the torpedo the ship is dodging
    evade_at: float = 0.0  # s, when the helm answers (after the reaction time)


@dataclass
class Cloud:
    """The disturbed water a pattern leaves: a noise shadow nobody hears through."""

    x: float
    y: float
    until: float  # s, sim time it has cleared
    radius: float


@dataclass
class Datum:
    """Where the escorts think the boat is, how sure they are, and how deep they will set
    the charges.  ``kind`` is a point (a fix) or a line (a torpedo's track, the boat
    somewhere along it within ``length``)."""

    x: float
    y: float
    t: float
    reason: str
    vx: float = 0.0  # m/s, the boat's estimated velocity (from the recent fixes)
    vy: float = 0.0
    fixes: tuple[tuple[float, float, float], ...] = ()  # (t, x, y) of recent sonar/sight fixes
    ring: float = 0.0  # m, radius of the last fix's uncertainty (0: exact)
    band: int = 0  # index into depth_charge.bands: where the next pattern is set
    kind: str = POINT
    heading: float = 0.0  # line: the direction from the near end toward the launch point
    length: float = 0.0  # line: how far along it the boat can be
    assumed: bool = False  # the velocity is the blind lead's guess, not a track
    attacks: int = 0  # runs made on this datum since the last fresh fix
    blind_attacks: int = 0  # of those, how many on the assumed flight
    search_since: float | None = None  # s, when the hunter started searching (the lose-track clock)
    run_damage: float = 0.0  # the boat's hull damage when the last run started

    def predict(self, t: float, lead_limit: float = ESCORT_AI.lead_limit) -> tuple[float, float]:
        """Where the boat should be at time ``t`` if it holds the course and speed the fixes
        show (never carried further than ``lead_limit`` past the last fix)."""
        dt = clamp(t - self.t, 0.0, lead_limit)
        return self.x + self.vx * dt, self.y + self.vy * dt

    def line_point(self, along: float) -> tuple[float, float]:
        return project(self.x, self.y, self.heading, clamp(along, 0.0, self.length))


# --- sensing -------------------------------------------------------------------------------


def aspect_factor(world: World, ship: Ship, sonar: SonarParams) -> float:
    """``f_aspect``: a beam-on hull returns a strong echo, an end-on one a weak one."""
    sub = world.player
    aspect = angle_diff(bearing(sub.x, sub.y, ship.x, ship.y), sub.heading)
    return sonar.aspect_floor + (1.0 - sonar.aspect_floor) * abs(math.sin(math.radians(aspect)))


def set_factor(world: World, ship: Ship, sonar: SonarParams, settled: bool = False) -> float:
    """``f_set``: the set's own state.  Sprinting deafens it, it needs ``settle_time`` after
    slowing down, and a hard turn halves what it hears.  ``settled`` asks for the reach a
    quiet, steady ship would have (the HUD's ``ECHO`` figure)."""
    if settled:
        return 1.0
    state = ship.escort
    if abs(ship.speed) > sonar.own_noise_speed:
        state.fast_until = world.time + sonar.settle_time
        return sonar.own_noise_factor
    if world.time < state.fast_until:
        return 0.0
    if abs(ship.rudder) > 0.5:
        return sonar.turn_factor
    return 1.0


def effective_reach(
    world: World, ship: Ship, sonar: SonarParams | None = None, settled: bool = False
) -> float:
    """The range at which ``ship``'s sonar can hold the boat right now."""
    sonar = world.rules.sonar if sonar is None else sonar
    sub = world.player
    reach = sonar.range * aspect_factor(world, ship, sonar)
    if abs(sub.speed) <= sonar.quiet_speed:
        reach *= sonar.quiet_factor
    if world.layer_depth is not None and sub.depth > world.layer_depth:
        reach *= sonar.layer_factor
    return reach * set_factor(world, ship, sonar, settled)


sonar_range = effective_reach  # the old name


def blind_zone(world: World, sonar: SonarParams | None = None) -> float:
    sonar = world.rules.sonar if sonar is None else sonar
    return clamp(
        world.player.depth * sonar.depth_blind_ratio, sonar.min_range, sonar.blind_zone_cap
    )


def shadowed_by(world: World, ship: Ship, brg: float, d: float) -> str | None:
    """What hides the boat (bearing ``brg``, range ``d`` from ``ship``) behind its noise: a
    friendly ship's id (afloat or not) or ``"cloud"``, else ``None``.  A noise source casts a
    sector beyond itself whose half-angle is its noise radius over its range."""
    sonar = world.rules.sonar
    for other in world.ships:
        if other is ship:
            continue
        od = distance(ship.x, ship.y, other.x, other.y)
        if od < 1.0 or od >= d:
            continue
        knots = 0.0 if other.sunk else abs(other.speed) / KNOT
        noise = sonar.noise_base + sonar.noise_per_knot * knots
        if abs(angle_diff(bearing(ship.x, ship.y, other.x, other.y), brg)) <= math.degrees(
            math.atan(noise / od)
        ):
            return other.ship_id
    for cloud in world.clouds:
        od = distance(ship.x, ship.y, cloud.x, cloud.y)
        if od < 1.0 or od >= d + cloud.radius:
            continue
        if od <= cloud.radius or abs(
            angle_diff(bearing(ship.x, ship.y, cloud.x, cloud.y), brg)
        ) <= math.degrees(math.atan(cloud.radius / od)):
            return "cloud"
    return None


def ping_outcome(world: World, ship: Ship) -> tuple[str | None, float]:
    """Why this ping gets no echo (``None`` if it does) and the fix's ring radius if it does.
    Rolls the faint-echo chance, so call it once per ping."""
    sonar = world.rules.sonar
    sub = world.player
    reach = effective_reach(world, ship, sonar)
    ship.escort.sonar_range = reach
    d = distance(ship.x, ship.y, sub.x, sub.y)
    brg = bearing(ship.x, ship.y, sub.x, sub.y)
    blind = blind_zone(world, sonar)
    if reach <= 0.0:
        return "set settling after the sprint", 0.0
    if d < blind:
        return f"boat under the keel (blind zone {blind:.0f} m)", 0.0
    if abs(angle_diff(brg, ship.heading)) > sonar.arc:
        return "boat outside the sonar cone", 0.0
    if d > reach:
        return f"out of reach ({reach:.0f} m)", 0.0
    shadow = shadowed_by(world, ship, brg, d)
    if shadow is not None:
        return ("boat behind the cloud" if shadow == "cloud" else f"boat behind {shadow}"), 0.0
    sure = sonar.sure_fraction * reach
    chance = 1.0 if d <= sure else clamp((reach - d) / max(reach - sure, 1e-9), 0.0, 1.0)
    if world.rng.random() > chance:
        return f"faint echo missed ({chance:.0%} chance)", 0.0
    return None, sonar.area_base + sonar.area_span * d / reach


def _ping(world: World, ship: Ship, state: EscortState) -> None:
    sonar = world.rules.sonar
    if world.time < state.next_ping:
        return
    state.next_ping = world.time + sonar.ping_interval
    why, ring = ping_outcome(world, ship)
    had_echo = state.echo
    if why is not None:
        state.echo, state.echo_why = False, why
        if had_echo and state.mode == HUNT:
            world.emit("echo_lost", ship=ship.ship_id, why=why)
        return
    state.echo, state.echo_why = True, "echo"
    sub = world.player
    r = ring * math.sqrt(world.rng.random())
    fx, fy = project(sub.x, sub.y, world.rng.uniform(0.0, 360.0), r)
    report(world, fx, fy, "sonar", ship.ship_id, ring=ring)


def report(world: World, x: float, y: float, reason: str, by: str, ring: float = 0.0) -> None:
    """Something told the escorts where the boat is (sonar, a sighting, radar).  The first
    report starts the engagement; later ones refresh the datum.  A sighting or radar fix is
    exact and says the boat is shallow; a sonar fix says nothing about depth."""
    t = world.time
    fresh = world.datum is None
    band = 0 if reason in ("sighted", "radar") else 1
    world.datum = _refresh_datum(world.datum, x, y, t, reason, world.rules.escort_ai, ring, band)
    if fresh:
        world.hunt_since = t
        world.emit("escort_alarm", reason=reason, by=by)
    # The convoy is told and runs for the screen.
    world.alert_group(x, y, "escort", by, quiet=True, radius=MERCHANT_WARNING_RANGE)


def report_line(world: World, x: float, y: float, heading: float, length: float, by: str) -> None:
    """A torpedo was observed: the boat is somewhere along its track, within ``length`` of
    (x, y) in direction ``heading``.  Does not overrule a fix younger than the hold-off."""
    t = world.time
    if world.datum is not None and t - world.datum.t < TORPEDO_DATUM_HOLDOFF:
        return
    fresh = world.datum is None
    world.datum = Datum(x, y, t, "torpedo", kind=LINE, heading=heading, length=length, band=0)
    if fresh:
        world.hunt_since = t
        world.emit("escort_alarm", reason="torpedo", by=by)
    world.emit(
        "torpedo_line", by=by, x=round(x), y=round(y), heading=round(heading), length=round(length)
    )
    world.alert_group(x, y, "escort", by, quiet=True, radius=MERCHANT_WARNING_RANGE)


def _refresh_datum(
    old: Datum | None,
    x: float,
    y: float,
    t: float,
    reason: str,
    p: EscortAIParams = ESCORT_AI,
    ring: float = 0.0,
    band: int = 0,
) -> Datum:
    """A new fix, with the boat's course and speed worked out from the recent ones (the fixes
    are tens of metres out, so only a long baseline gives a usable velocity).  The depth band
    and the hunt's bookkeeping carry over from the old datum."""
    if old is not None and old.kind == POINT:
        band = old.band
    history = tuple(f for f in (old.fixes if old else ()) if t - f[0] <= p.track_window)
    fixes = (*history, (t, x, y))
    keep = {
        "band": band,
        "search_since": old.search_since if old else None,
        "attacks": old.attacks if old else 0,
        "run_damage": old.run_damage if old else 0.0,
    }
    if len(fixes) < 3 or t - fixes[0][0] < p.track_min_baseline:
        return Datum(x, y, t, reason, 0.0, 0.0, fixes, ring=ring, **keep)
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
    return Datum(x, y, t, reason, vx, vy, fixes, ring=ring, **keep)


def _observe_torpedoes(world: World, escorts: list[Ship]) -> None:
    """An escort that hears a running torpedo (or sees its wake) gives the group its track:
    the boat is somewhere back along it, within the torpedo's run."""
    ev = world.rules.evasion
    for torpedo in world.torpedoes:
        if not torpedo.alive or torpedo.torpedo_id in world.observed_torpedoes:
            continue
        for ship in escorts:
            d = distance(ship.x, ship.y, torpedo.x, torpedo.y)
            wake = torpedo.params.wake_visible_range * ship.type.lookout * world.light
            if d <= max(ev.hear_range, wake):
                world.observed_torpedoes.add(torpedo.torpedo_id)
                back = wrap_degrees(torpedo.heading + 180.0)
                report_line(world, torpedo.x, torpedo.y, back, torpedo.params.max_run, ship.ship_id)
                break


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


def _stand_down(world: World, escorts: list[Ship], reason: str = STAND_DOWN_LOST) -> None:
    world.datum = None
    world.hunt_since = None
    for e in escorts:
        e.escort.mode = FORMATION
        e.escort.drop_left = 0
        _set_intent(world, e, INTENT_RETURNING)
    world.emit("escort_stand_down", reason=reason)


def _hunt_over(world: World, escorts: list[Ship], p: EscortAIParams) -> str | None:
    """Why the escorts should stand down now, or ``None``."""
    datum = world.datum
    assert datum is not None
    t = world.time
    if world.hunt_since is not None and t - world.hunt_since > p.max_hunt_time:
        return STAND_DOWN_TIME
    hunters = [e for e in escorts if e.escort.mode == HUNT]
    cx, cy, _, _ = _convoy(world, escorts[0])
    if any(distance(e.x, e.y, cx, cy) > p.hunt_leash for e in hunters):
        return STAND_DOWN_LEASH
    if hunters and all(e.escort.charges <= 0 for e in hunters):
        return STAND_DOWN_CHARGES
    since = datum.t if datum.search_since is None else max(datum.t, datum.search_since)
    if datum.search_since is not None and t - since > p.lose_track_time:
        return STAND_DOWN_LOST
    return None


def _set_intent(world: World, ship: Ship, intent: str) -> None:
    if ship.escort.intent != intent:
        ship.escort.intent = intent
        world.emit("escort_intent", ship=ship.ship_id, intent=intent)


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


def _keep_station(ship: Ship, sx: float, sy: float, facing: float, speed: float, p) -> bool:
    """Steer for the station; ``True`` once on it."""
    d = distance(ship.x, ship.y, sx, sy)
    if d > p.station_tolerance:
        _goto(ship, sx, sy, clamp(speed + 0.02 * d, speed, p.attack_speed))
        return False
    ai.steer(ship, facing)
    ship.set_throttle(clamp(speed / ship.params.max_speed, 0.0, 1.0))
    return True


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
    on_station = _keep_station(ship, sx, sy, course, speed, p)
    _set_intent(world, ship, INTENT_FORMATION if on_station else INTENT_RETURNING)


def _screen(world: World, ship: Ship, rank: int, count: int, p: EscortAIParams) -> None:
    datum = world.datum
    assert datum is not None
    cx, cy, _, speed = _convoy(world, ship)
    toward = bearing(cx, cy, datum.x, datum.y)
    sx, sy = project(cx, cy, toward, p.screen_distance)
    sx, sy = project(sx, sy, toward + 90.0, (rank - (count - 1) / 2) * p.screen_abeam)
    _keep_station(ship, sx, sy, toward, speed, p)
    _set_intent(world, ship, INTENT_SCREENING)


def _lead_limit(datum: Datum, p: EscortAIParams) -> float:
    return p.max_hunt_time if datum.assumed else p.lead_limit


def _drop(world: World, ship: Ship, p: EscortAIParams, dc: DepthChargeParams) -> None:
    """One charge of the pattern.  It is aimed where the boat will be when the charge has
    sunk to its depth (the datum's predicted path), a little to one side or the other, and
    the pattern is spread over the depth band the escorts are working.  A charge is released
    when the ship can reach its aim point (within ``throw_range``); if the aim points stay
    ahead and out of reach for ``run_max_time`` the run is abandoned (the run-over release)."""
    state = ship.escort
    sub = world.player
    datum = world.datum
    assert datum is not None
    n = dc.pattern_size
    k = n - state.drop_left  # 0 for the first charge of the run
    lo, hi = dc.bands[datum.band % len(dc.bands)]
    layer = k / (n - 1) if n > 1 else 0.5
    set_depth = clamp(lo + (hi - lo) * layer, lo, sub.spec.max_depth)
    ax, ay = datum.predict(world.time + set_depth / dc.sink_rate, _lead_limit(datum, p))
    rad = math.radians(ship.heading)
    ahead = (ax - ship.x) * math.sin(rad) + (ay - ship.y) * math.cos(rad)
    if distance(ship.x, ship.y, ax, ay) > dc.throw_range and ahead > 0.0:
        if world.time - state.run_started < dc.run_max_time:
            state.drop_timer = 0.5  # not there yet: hold course, try again shortly
            return
        state.drop_left = 0
        world.emit("run_abandoned", ship=ship.ship_id)
        return
    state.drop_left -= 1
    state.drop_timer = dc.drop_interval
    speed = math.hypot(datum.vx, datum.vy)
    across = (
        math.degrees(math.atan2(datum.vx, datum.vy)) + 90.0
        if speed > 0.1
        else world.rng.uniform(0.0, 360.0)
    )
    side = 1.0 if k % 2 == 0 else -1.0
    ax, ay = project(ax, ay, across, side * world.rng.uniform(0.0, 1.0) * dc.scatter)
    if distance(ship.x, ship.y, ax, ay) > dc.throw_range:
        return
    world.next_charge_id += 1
    world.depth_charges.append(DepthCharge(world.next_charge_id, ax, ay, set_depth, dc))
    state.charges -= 1


def _start_run(world: World, ship: Ship, p: EscortAIParams, dc: DepthChargeParams) -> None:
    """Begin a pattern: move the depth band on if the last pattern did nothing, then drop."""
    state, datum, sub = ship.escort, world.datum, world.player
    assert datum is not None
    if datum.attacks > 0 and sub.damage - datum.run_damage < dc.confirm_damage:
        datum.band = (datum.band + 1) % len(dc.bands)
    datum.run_damage = sub.damage
    datum.attacks += 1
    if datum.assumed:
        datum.blind_attacks += 1
    state.cooldown_until = world.time + dc.pattern_cooldown
    state.drop_left = dc.pattern_size
    state.run_started = world.time
    lo, hi = dc.bands[datum.band % len(dc.bands)]
    world.emit(
        "depth_charge_run",
        ship=ship.ship_id,
        charges=state.charges,
        band=datum.band,
        shallow=round(lo),
        deep=round(hi),
        assumed=datum.assumed,
    )
    _set_intent(world, ship, INTENT_ATTACKING)
    _drop(world, ship, p, dc)


def _sweep_line(world: World, ship: Ship, p: EscortAIParams) -> None:
    """Down the torpedo's track from the target toward the launch point, pinging both sides;
    at the far end the line becomes a stale point to search around."""
    datum = world.datum
    assert datum is not None and datum.kind == LINE
    rad = math.radians(datum.heading)
    along = (ship.x - datum.x) * math.sin(rad) + (ship.y - datum.y) * math.cos(rad)
    if along >= datum.length - p.station_tolerance:
        fx, fy = datum.line_point(datum.length)
        world.datum = replace(
            datum,
            x=fx,
            y=fy,
            kind=POINT,
            t=world.time - FRESH_DATUM - 1.0,
            attacks=1,
            search_since=world.time,
        )
        return
    wx, wy = datum.line_point(max(along, 0.0) + 2.0 * p.station_tolerance)
    _goto(ship, wx, wy, p.approach_speed)
    _set_intent(world, ship, INTENT_SWEEPING)


def _hunt(world: World, ship: Ship, dt: float, p: EscortAIParams) -> None:
    state, datum, t = ship.escort, world.datum, world.time
    dc = world.rules.depth_charge
    assert datum is not None
    if state.drop_left > 0:  # mid-run: hold course and speed while the projectors fire
        ship.set_rudder(0.0)
        state.drop_timer -= dt
        if state.charges <= 0:
            state.drop_left = 0
        elif state.drop_timer <= 0.0:
            _drop(world, ship, p, dc)
        return
    if datum.kind == LINE:
        _sweep_line(world, ship, p)
        return
    age = t - datum.t
    fresh = age <= FRESH_DATUM
    # A stale fix is still worth one attack on the dead-reckoned position; after that, assume
    # the boat ran straight away from us and attack that a few times; then search.
    attack_worthy = (
        fresh
        or (age <= p.datum_attack_age and datum.attacks == 0 and not datum.assumed)
        or (datum.assumed and datum.blind_attacks < p.blind_attacks)
    )
    if (
        not attack_worthy
        and datum.attacks > 0
        and not datum.assumed
        and datum.blind_attacks == 0
        and p.blind_attacks > 0
    ):
        # The hunter has just run over the datum along its approach course; a boat fleeing
        # from it would have kept going the same way.
        px, py = datum.predict(t, p.lead_limit)
        away = ship.heading
        rad = math.radians(away)
        world.datum = datum = replace(
            datum,
            x=px,
            y=py,
            t=t,
            vx=math.sin(rad) * p.blind_lead_speed,
            vy=math.cos(rad) * p.blind_lead_speed,
            fixes=(),
            assumed=True,
        )
        world.emit("blind_lead", ship=ship.ship_id, heading=round(away))
        attack_worthy = True
    if attack_worthy:
        lead = _lead_limit(datum, p)
        nx, ny = datum.predict(t, lead)  # where the boat should be now
        d = distance(ship.x, ship.y, nx, ny)
        px, py = datum.predict(t + d / max(ship.speed, p.approach_speed), lead)
        near = distance(ship.x, ship.y, *datum.predict(t + FIRST_CHARGE_DELAY, lead))
        if near <= dc.throw_range and t >= state.cooldown_until and state.charges > 0:
            _start_run(world, ship, p, dc)
            return
        _goto(ship, px, py, p.attack_speed if d > p.approach_range else p.approach_speed)
        _set_intent(world, ship, INTENT_HUNTING)
        return
    if datum.assumed:  # the blind lead is spent: back to a plain stale point
        world.datum = datum = replace(datum, assumed=False, vx=0.0, vy=0.0)
    if datum.search_since is None:
        datum.search_since = t
    _set_intent(world, ship, INTENT_SEARCHING)
    pick(world.difficulty, "escort_search")(world, ship, p)


# --- strategies ----------------------------------------------------------------------------


def _search_radius(datum: Datum, t: float, p: EscortAIParams) -> float:
    since = datum.t if datum.search_since is None else datum.search_since
    return clamp(p.search_start + p.search_growth * (t - since), p.search_start, p.search_max)


@strategy("escort_search", "box")
def box_search(world: World, ship: Ship, p: EscortAIParams) -> None:
    """No recent fix: steam round a square around the datum that widens as the track gets
    older (the M2 search; it never points the cone through the middle)."""
    state, datum, t = ship.escort, world.datum, world.time
    assert datum is not None
    radius = _search_radius(datum, t, p)
    angle = state.search_leg * 90.0 + 45.0
    wx, wy = project(datum.x, datum.y, angle, radius)
    if distance(ship.x, ship.y, wx, wy) < p.station_tolerance * 0.8:
        state.search_leg += 1
    _goto(ship, wx, wy, p.search_speed)


SWEEP_ORDER = (0, 2, 1, 3)  # corners visited: two legs through the middle per circuit


@strategy("escort_search", "sweep")
def sweep_search(world: World, ship: Ship, p: EscortAIParams) -> None:
    """No recent fix: legs *through* the datum from alternating directions, so the sonar
    cone is pointed across the whole search area, which widens as the track gets older."""
    state, datum, t = ship.escort, world.datum, world.time
    assert datum is not None
    radius = _search_radius(datum, t, p)
    corner = SWEEP_ORDER[state.search_leg % 4]
    wx, wy = project(datum.x, datum.y, corner * 90.0 + 45.0, radius)
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
    evade = pick(world.difficulty, "escort_evade")
    for e in escorts:
        if e.escort.charges < 0:
            e.escort.charges = world.rules.depth_charge.magazine
        _ping(world, e, e.escort)
    _observe_torpedoes(world, escorts)
    datum = world.datum
    if datum is not None:
        reason = _hunt_over(world, escorts, p)
        if reason is not None:
            _stand_down(world, escorts, reason)
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
