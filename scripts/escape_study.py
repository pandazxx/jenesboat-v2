#!/usr/bin/env python3
"""Escape study: can a boat that a destroyer has just found get away?

A balance harness for ``docs/ESCAPE_BALANCE.md``.  A destroyer has the boat on sonar at
``range`` metres (the convoy is 2 km behind it); the boat, at periscope depth, runs one of a
few fixed evasion recipes.  Over a dozen seeds the script counts how often the boat is lost,
how much damage it takes, how many depth charge runs it suffers and how the engagement ends
(the boat is lost, the escorts lose the track, they give up, or the clock runs out).

    uv run python scripts/escape_study.py                      # current rules, patrol
    uv run python scripts/escape_study.py --difficulty veteran --seeds 20
    uv run python scripts/escape_study.py --proposal           # the rules proposed in the doc

``--placement inside`` starts the boat on the far side of the convoy from the hunter (found
while attacking), so the merchants' noise shadows are between them.

``--story deep_creep_away --ranges 3000,1000`` prints one escape (first found at 3 km, else
1 km) and one loss (1 km, else 3 km) of that recipe as the Markdown tables used on #34.

``--proposal`` monkeypatches ``sim.escort`` with the candidate rules of the design note
(``Proposal`` below) so they can be measured before they are implemented; the implementation
PRs are expected to move each rule into ``sim/params.py`` and delete the patch here.
"""

from __future__ import annotations

import argparse
import math
import random
from collections import Counter
from dataclasses import dataclass

from jenesboat_v2.sim import escort as E
from jenesboat_v2.sim import params as P
from jenesboat_v2.sim.escort import HUNT, Datum
from jenesboat_v2.sim.geo import angle_diff, bearing, clamp, distance, project, wrap_degrees
from jenesboat_v2.sim.params import DESTROYER, FREIGHTER, KNOT
from jenesboat_v2.sim.submarine import new_submarine
from jenesboat_v2.sim.world import World, new_ship

C = 20_000.0
RECIPES = (
    "sit",
    "deep_sit",
    "deep_creep_away",
    "deep_flank_away",
    "deep_flank_90",
    "deep_sprint_then_creep",
    "knuckle",
)
RANGES = (1_000, 2_000, 3_000)


# --- the engagement ------------------------------------------------------------------------


PLACEMENT = "outside"  # or "inside": the convoy lies between the hunter and the boat


def setup(seed: int, range_m: float, difficulty: P.Difficulty) -> World:
    """The boat at periscope depth, just pinged by the nearest of the level's destroyers,
    which is ``range_m`` away and already hunting.  ``PLACEMENT`` puts the convoy 2 km
    behind the destroyer (``outside``: the boat was found outside the screen) or 600 m
    from the boat toward the destroyer (``inside``: found while attacking, the merchants
    between the hunter and the boat)."""
    rules = difficulty.rules
    rng = random.Random(seed)
    sub = new_submarine(x=C, y=C, heading=rng.uniform(0.0, 360.0))
    sub.depth = sub.target_depth = P.TYPE_VIIC.periscope_depth
    brg = rng.uniform(0.0, 360.0)
    if PLACEMENT == "inside":  # the convoy centre 600 m from the boat, toward the hunter
        cx, cy = project(C, C, brg, 600.0)
    else:
        cx, cy = project(C, C, brg, range_m + 2_000.0)
    ships = []
    for i in range(3):
        x, y = project(cx, cy, brg + 90.0, 800.0 * (i - 1))
        course = wrap_degrees(brg + 90.0)
        ships.append(new_ship(f"merchant-{i}", FREIGHTER, x, y, course, spread=i - 1))
    for i in range(rules.scenario.escorts):
        side = 1.0 if i % 2 == 0 else -1.0
        off = 0.0 if i == 0 else side * 15.0 * (i // 2 + 1)
        x, y = project(C, C, brg + off, range_m + (0.0 if i == 0 else 600.0 * (i // 2 + 1)))
        course = wrap_degrees(brg + 180.0)
        ships.append(new_ship(f"destroyer-{i + 1}", DESTROYER, x, y, course, speed=12 * KNOT))
    world = World(width=2 * C, height=2 * C, player=sub, ships=ships, difficulty=difficulty)
    world.rng = random.Random(rng.random())
    world.datum = Datum(sub.x, sub.y, 0.0, "sonar", fixes=((0.0, sub.x, sub.y),))
    world.__dict__["_sighted"] = True  # the boat was at periscope depth when found
    ships[3].escort.mode = HUNT
    return world


def steer(sub, heading: float) -> None:
    sub.set_rudder(clamp(angle_diff(heading, sub.heading) / 10.0, -1.0, 1.0))


def orders(recipe: str, world: World, t: float, start_heading: float) -> None:
    """The player's standing orders, applied every tick."""
    sub = world.player
    hunter = next(s for s in world.ships if s.kind == "military")
    away = bearing(hunter.x, hunter.y, sub.x, sub.y)
    if recipe == "sit":  # periscope depth, stopped: the player does nothing
        sub.set_throttle(0.0)
    elif recipe == "deep_sit":
        sub.set_target_depth(60.0)
        sub.set_throttle(0.0)
    elif recipe == "deep_creep_away":
        sub.set_target_depth(60.0)
        sub.set_throttle(0.25)
        steer(sub, away)
    elif recipe == "deep_flank_away":
        sub.set_target_depth(60.0)
        sub.set_throttle(1.0)
        steer(sub, away)
    elif recipe == "deep_flank_90":
        sub.set_target_depth(60.0)
        sub.set_throttle(1.0)
        steer(sub, wrap_degrees(start_heading + 90.0))
    elif recipe == "deep_sprint_then_creep":  # 90 s flank across the line of sight, then creep
        sub.set_target_depth(60.0)
        if t < 90.0:
            sub.set_throttle(1.0)
            steer(sub, wrap_degrees(start_heading + 90.0))
        else:
            sub.set_throttle(0.25)
            steer(sub, wrap_degrees(start_heading + 150.0))
    elif recipe == "knuckle":  # a minute of sprint across, a minute of creep away, repeat
        sub.set_target_depth(60.0)
        if int(t // 60.0) % 2 == 0:
            sub.set_throttle(1.0)
            steer(sub, wrap_degrees(away + 90.0))
        else:
            sub.set_throttle(0.25)
            steer(sub, away)
    else:
        raise SystemExit(f"unknown recipe {recipe!r}; recipes: {', '.join(RECIPES)}")


def run(
    seed: int, range_m: float, recipe: str, difficulty: P.Difficulty, seconds=1_800.0, dt=0.5
) -> dict:
    world = setup(seed, range_m, difficulty)
    sub = world.player
    start_heading = sub.heading
    runs = stand_down = 0
    while world.time < seconds:
        orders(recipe, world, world.time, start_heading)
        world.step(dt)
        for e in world.events:
            if e["event"] == "damage":
                world.__dict__["_dmg_since_run"] = True
            elif e["event"] == "depth_charge_run":
                runs += 1
            elif e["event"] == "escort_stand_down":
                stand_down += 1
        world.events.clear()
        if sub.destroyed or stand_down:
            break
    if sub.destroyed:
        reason = "lost"
    elif world.__dict__.get("_gave_up"):
        reason = "gave_up"
    elif stand_down:
        reason = "lost_track"
    else:
        reason = "timeout"
    return {
        "lost": sub.destroyed,
        "damage": sub.damage,
        "runs": runs,
        "t": world.time,
        "end": reason,
    }


# --- the proposed rules (prototype, see docs/ESCAPE_BALANCE.md) ------------------------------


@dataclass(frozen=True)
class Proposal:
    baffle_angle: float = 50.0  # deg either side of the stern the set cannot hear
    depth_blind_ratio: float = 3.0  # echo lost inside depth * ratio (the beam cannot tilt down)
    sure_fraction: float = 0.4  # a ping inside this fraction of the reach is a sure fix (kept, Q1)
    area_base: float = 25.0  # m, radius of the fix's uncertainty area at zero range (Q2)
    area_per_km: float = 50.0  # m of radius per km of range (175 m at 3 km)
    noise_base: float = 150.0  # m, noise radius of a stopped or sunk friendly ship (Q3)
    noise_per_knot: float = 30.0  # m of noise radius per knot of that ship's speed
    own_noise_factor: float = 0.25  # reach while sprinting (sheet: 0.4)
    settle_time: float = 20.0  # s after slowing below own_noise_speed before the set works
    assumed_depth: float = 40.0  # m, the depth guessed for a sonar-only contact
    depth_step: float = 25.0  # m deeper each run that did no damage
    layer_spread: float = 15.0  # m, the pattern is layered estimate +- this (sheet: 25)
    run_over: bool = True  # release each charge when the ship reaches its aim point
    run_max_time: float = 40.0  # s, a run that cannot reach its aim points is abandoned
    pattern_cooldown: float = 120.0  # s between runs (sheet: 45)
    hunt_leash: float = 10_000.0  # m from the convoy a hunter will not go beyond
    max_hunt_time: float = 1_800.0  # s after the alarm the escorts give up


PROPOSALS = {
    "cadet": Proposal(
        baffle_angle=60.0,
        depth_blind_ratio=4.0,
        assumed_depth=30.0,
        hunt_leash=6_000.0,
        max_hunt_time=900.0,
    ),
    "patrol": Proposal(),
    "veteran": Proposal(
        baffle_angle=40.0,
        depth_blind_ratio=2.5,
        sure_fraction=0.5,
        depth_step=20.0,
        pattern_cooldown=90.0,
        hunt_leash=15_000.0,
        max_hunt_time=3_600.0,
    ),
}
PROP = PROPOSALS["patrol"]
_ORIGINAL = (E._ping, E._drop, E.step)


def _ping(world: World, ship, state) -> None:
    sonar = world.rules.sonar
    if world.time < state.next_ping:
        return
    state.next_ping = world.time + sonar.ping_interval
    sub = world.player
    mem = ship.__dict__
    # Reach: the sheet's range, the creep bonus, own noise; the old fleet-noise rule is gone
    # (Q3), the shadows below replace it.
    reach = sonar.range
    if abs(sub.speed) <= sonar.quiet_speed:
        reach *= sonar.quiet_factor
    sprinting = settling = False
    if abs(ship.speed) > sonar.own_noise_speed:  # sprinting: nearly deaf, and the set must settle
        reach *= PROP.own_noise_factor
        mem["_fast_until"] = world.time + PROP.settle_time
        sprinting = True
    elif world.time < mem.get("_fast_until", -1.0):
        reach = 0.0
        settling = True
    state.sonar_range = reach
    d = distance(ship.x, ship.y, sub.x, sub.y)
    blind = max(sonar.min_range, sub.depth * PROP.depth_blind_ratio)
    brg = bearing(ship.x, ship.y, sub.x, sub.y)
    shadow = in_shadow(world, ship, brg, d)
    sure = PROP.sure_fraction * reach
    chance = 1.0 if d <= sure else clamp((reach - d) / max(reach - sure, 1e-9), 0.0, 1.0)
    if settling:
        why = "set settling after the sprint"
    elif d < blind:
        why = f"boat under the keel (blind zone {blind:.0f} m)"
    elif d > reach:
        why = f"out of reach ({reach:.0f} m{', sprinting' if sprinting else ''})"
    elif abs(angle_diff(brg, ship.heading)) > 180.0 - PROP.baffle_angle:
        why = "boat in the baffles astern"
    elif shadow is not None:
        why = f"boat behind {shadow}'s noise"
    elif world.rng.random() > chance:
        why = f"faint echo missed ({chance:.0%} chance at {d:.0f} of {reach:.0f} m)"
    else:
        why = None
    if why is not None:
        mem["_ping_why"] = "no echo: " + why
        return
    # The fix is a random point in the uncertainty area, which grows with range (Q2).
    radius = PROP.area_base + PROP.area_per_km * d / 1000.0
    r = radius * math.sqrt(world.rng.random())
    fx, fy = project(sub.x, sub.y, world.rng.uniform(0.0, 360.0), r)
    mem["_ping_why"] = "echo"
    mem["_fix_radius"] = radius
    E.report(world, fx, fy, "sonar", ship.ship_id)


def in_shadow(world: World, ship, brg: float, d: float) -> str | None:
    """The id of the friendly ship whose noise hides the boat (bearing ``brg``, range ``d``
    from the pinging ship), or ``None``.  Each ship, afloat or not, casts a sector beyond
    itself whose half-angle is set by its noise radius (base plus speed) at its range."""
    for other in world.ships:
        if other is ship:
            continue
        od = distance(ship.x, ship.y, other.x, other.y)
        if od < 1.0 or od >= d:
            continue
        noise = PROP.noise_base + PROP.noise_per_knot * (
            0.0 if other.sunk else abs(other.speed) / KNOT
        )
        half = math.degrees(math.atan(noise / od))
        if abs(angle_diff(bearing(ship.x, ship.y, other.x, other.y), brg)) <= half:
            return other.ship_id
    return None


def _drop(world: World, ship, p, depth_params) -> None:
    """As ``escort._drop``, but layered around the escorts' *estimate* of the depth, and (with
    ``run_over``) each charge is held until the ship can reach its aim point."""
    state, sub, datum, mem = ship.escort, world.player, world.datum, world.__dict__
    assert datum is not None
    est = mem.get("_depth_est")
    if est is None:  # a sighting means the boat was shallow when last seen; else a guess
        est = sub.spec.periscope_depth if mem.get("_sighted") else PROP.assumed_depth
    n = depth_params.pattern_size
    k = n - state.drop_left
    if k == 0 and ship.__dict__.get("_run_k") != 0:
        if mem.get("_runs", 0) > 0 and not mem.get("_dmg_since_run"):
            est = min(est + PROP.depth_step, sub.spec.max_depth)
        mem["_runs"] = mem.get("_runs", 0) + 1
        mem["_dmg_since_run"] = False
    mem["_depth_est"] = est
    layer = k / (n - 1) if n > 1 else 0.5
    set_depth = clamp(
        est + PROP.layer_spread * (2.0 * layer - 1.0), depth_params.min_depth, sub.spec.max_depth
    )
    ax, ay = datum.predict(world.time + set_depth / depth_params.sink_rate, p.lead_limit)
    if PROP.run_over:
        if ship.__dict__.get("_run_k") != k:
            ship.__dict__["_run_k"], ship.__dict__["_run_t0"] = k, world.time
        rad = math.radians(ship.heading)
        ahead = (ax - ship.x) * math.sin(rad) + (ay - ship.y) * math.cos(rad)
        if distance(ship.x, ship.y, ax, ay) > depth_params.throw_range and ahead > 0.0:
            if world.time - ship.__dict__["_run_t0"] < PROP.run_max_time:
                state.drop_timer = 0.5  # not there yet: hold course, try again shortly
            else:
                state.drop_left = 0  # cannot get there: abandon the run
                ship.__dict__["_run_k"] = None
            return
    state.drop_left -= 1
    if state.drop_left == 0:
        ship.__dict__["_run_k"] = None
    state.drop_timer = depth_params.drop_interval
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
    world.depth_charges.append(E.DepthCharge(world.next_charge_id, ax, ay, set_depth, depth_params))
    state.charges -= 1


def _step(world: World, dt: float, p=None) -> None:
    """``escort.step`` plus the hunt leash, the time limit and the longer rack reload."""
    p = world.rules.escort_ai if p is None else p
    escorts = [s for s in world.active_ships if s.kind == "military"]
    before = {e.ship_id: e.escort.cooldown_until for e in escorts}
    mem = world.__dict__
    if world.datum is not None:
        mem.setdefault("_alarm_t", world.time)
        merchants = [s for s in world.active_ships if s.kind == "merchant"]
        strayed = False
        if merchants:
            cx = sum(s.x for s in merchants) / len(merchants)
            cy = sum(s.y for s in merchants) / len(merchants)
            strayed = any(
                e.escort.mode == HUNT and distance(e.x, e.y, cx, cy) > PROP.hunt_leash
                for e in escorts
            )
        if strayed or world.time - mem["_alarm_t"] > PROP.max_hunt_time:
            E._stand_down(world, escorts)
            mem["_gave_up"] = True
    else:
        mem.pop("_alarm_t", None)
    _ORIGINAL[2](world, dt, p)
    for e in escorts:
        if e.escort.cooldown_until != before[e.ship_id]:
            e.escort.cooldown_until = world.time + PROP.pattern_cooldown


def install(level: str) -> None:
    global PROP
    PROP = PROPOSALS[level]
    E._ping, E._drop, E.step = _ping, _drop, _step


def uninstall() -> None:
    E._ping, E._drop, E.step = _ORIGINAL


# --- the report ----------------------------------------------------------------------------


def table(difficulty: P.Difficulty, recipes, ranges, seeds: int, proposal: bool) -> None:
    rules = "PROPOSED" if proposal else "CURRENT"
    summary = rules_summary(difficulty, proposal)
    print(f"\n## {difficulty.name}, {rules} rules, found {PLACEMENT}, {summary}")
    head = f"{'recipe':24s} {'range':>5s} {'lost':>5s} {'dmg':>5s} {'runs':>5s} {'t_end':>6s}"
    print(f"{head}  how it ended")
    for recipe in recipes:
        for range_m in ranges:
            res = [run(seed, range_m, recipe, difficulty) for seed in range(seeds)]
            n = len(res)
            ends = ", ".join(f"{k} {v}" for k, v in sorted(Counter(r["end"] for r in res).items()))
            print(
                f"{recipe:24s} {range_m:5d} {sum(r['lost'] for r in res) / n:5.2f} "
                f"{sum(r['damage'] for r in res) / n:5.2f} {sum(r['runs'] for r in res) / n:5.1f} "
                f"{sum(r['t'] for r in res) / n:6.0f}  {ends}"
            )


def rules_summary(difficulty: P.Difficulty, proposal: bool) -> str:
    r = difficulty.rules
    base = f"{r.scenario.escorts} escorts, sonar {r.sonar.range:.0f} m"
    if not proposal:
        return base
    prop = PROPOSALS[difficulty.name]
    return (
        f"{base}, leash {prop.hunt_leash / 1000:.0f} km / {prop.max_hunt_time / 60:.0f} min, "
        f"blind x{prop.depth_blind_ratio:.1f}, baffle {prop.baffle_angle:.0f} deg, "
        f"area {prop.area_base:.0f} m + {prop.area_per_km:.0f} m/km, shadows"
    )


# --- stories: one engagement as a table (the format agreed on #34) ---------------------------

STORY_HEAD = (
    "| time | boat | hunter | range / bearing | boat does | hunter does | hunter's sonar "
    "| hunter's track on the boat |\n|---|---|---|---|---|---|---|---|\n"
)
TITLES = {
    "sit": "Stay at periscope depth, stop",
    "deep_sit": "Go deep (60 m), stop",
    "deep_creep_away": "Go deep, creep (AHEAD SLOW) straight away from the hunter",
    "deep_flank_away": "Go deep, AHEAD FLANK straight away from the hunter",
    "deep_flank_90": "Go deep, AHEAD FLANK 90 deg off the original heading",
    "deep_sprint_then_creep": "Go deep, 90 s AHEAD FLANK across, then AHEAD SLOW 150 deg off",
    "knuckle": "Go deep, alternate 60 s AHEAD FLANK across the bearing / 60 s AHEAD SLOW away",
}


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def _hunter_state(h, world: World) -> str:
    kn = h.speed / KNOT
    if h.escort.drop_left > 0:
        what = "dropping"
    elif kn > 15.5:
        what = "sprint"
    elif h.escort.mode != HUNT:
        what = h.escort.mode
    elif world.datum is not None and world.time - world.datum.t <= E.FRESH_DATUM:
        what = "closing"
    else:
        what = "searching"
    return f"{what} {kn:.0f} kn"


def _track(world: World, h) -> str:
    if world.datum is None:
        return "-"
    parts = [f"fix {world.time - world.datum.t:.0f} s old"]
    if world.datum.reason == "sonar" and "_fix_radius" in h.__dict__:
        parts.append(f"ring {h.__dict__['_fix_radius']:.0f} m")
    est = world.__dict__.get("_depth_est")
    if est is not None:
        parts.append(f"depth guess {est:.0f} m")
    return ", ".join(parts)


def story(recipe: str, range_m: float, seed: int, difficulty: P.Difficulty) -> tuple[list, dict]:
    """Play one engagement under the installed rules and return the table rows and the
    outcome.  A row for every change on either side, and one a minute otherwise."""
    world = setup(seed, range_m, difficulty)
    sub, h = world.player, world.ships[3]
    h.__dict__["_ping_why"] = "no ping yet"
    start_heading = sub.heading
    rows: list[tuple] = []
    runs = 0
    run: dict | None = None
    prev_contact = None
    hist: list[str] = []
    last_ping = None
    next_sample = 60.0
    first = True
    pb = (sub.throttle, sub.target_depth)

    def flush(t: float, boat_txt: list[str], hunter_txt: list[str]) -> None:
        d = distance(h.x, h.y, sub.x, sub.y)
        rel = abs(angle_diff(bearing(h.x, h.y, sub.x, sub.y), h.heading))
        rows.append(
            (
                mmss(t),
                f"{sub.depth:.0f} m, {sub.telegraph_label} {abs(sub.speed) / KNOT:.1f} kn",
                _hunter_state(h, world),
                f"{d:.0f} m / {rel:.0f} deg off the bow",
                "; ".join(boat_txt) or "-",
                "; ".join(hunter_txt) or "-",
                h.__dict__["_ping_why"],
                _track(world, h),
            )
        )

    while world.time < 1_800.0:
        orders(recipe, world, world.time, start_heading)
        t = world.time
        boat_txt: list[str] = []
        hunter_txt: list[str] = []
        if first:
            boat_txt.append("found at periscope depth by the hunter's sonar")
            hunter_txt.append("has the first fix, turns toward it to hunt")
            first = False
        if (sub.throttle, sub.target_depth) != pb:
            if sub.target_depth != pb[1]:
                boat_txt.append(f"orders {sub.target_depth:.0f} m")
            if sub.throttle != pb[0]:
                boat_txt.append(f"rings {sub.telegraph_label}")
            pb = (sub.throttle, sub.target_depth)
        depth_before = sub.depth
        state_before = _hunter_state(h, world).split()[0]
        drop_before = h.escort.drop_left
        world.step(0.5)
        if depth_before != sub.target_depth and sub.depth == sub.target_depth:
            boat_txt.append(f"reaches {sub.depth:.0f} m")
        state_after = _hunter_state(h, world).split()[0]
        if state_after != state_before and "dropping" not in (state_before, state_after):
            if state_after == "sprint":
                hunter_txt.append("sprints at 20 kn for the predicted position (set deafened)")
            elif state_after == "closing" and state_before == "searching":
                hunter_txt.append("fix fresh again: steers for the predicted position at 14 kn")
            elif state_after == "closing":
                hunter_txt.append("slows to 14 kn so the set can hear, closes on the prediction")
            elif state_after == "searching":
                hunter_txt.append("no fix for 60 s: box search at 12 kn around the last fix")
            elif state_after == "formation":
                hunter_txt.append("returns to formation")
        for e in world.events:
            if e["event"] == "damage":
                world.__dict__["_dmg_since_run"] = True
            elif e["event"] == "depth_charge_run":
                runs += 1
                run = {
                    "charges0": e["charges"],  # the magazine before the run's first drop
                    "dropped": None,
                    "bursts": [],
                    "dmg0": sub.damage,
                }
                hunter_txt.append(
                    f"starts run {runs}: predicted position within 150 m, holds course"
                )
            elif e["event"] == "depth_charge" and run is not None:
                run["bursts"].append((e["depth"], math.hypot(e["x"] - sub.x, e["y"] - sub.y)))
            elif e["event"] == "escort_stand_down":
                why = (
                    "leash: hunter 10 km from the convoy"
                    if world.__dict__.get("_gave_up")
                    else "track lost 300 s"
                )
                hunter_txt.append(f"escorts stand down ({why})")
        world.events.clear()
        if run is not None and run["bursts"]:  # a burst's damage lands after its event
            done = run["dropped"] is not None and len(run["bursts"]) >= run["dropped"]
            if sub.destroyed or done:
                depths = sorted(b[0] for b in run["bursts"])
                near = min(b[1] for b in run["bursts"])
                hunter_txt.append(
                    f"pattern of run {runs} bursts: {len(run['bursts'])} charges set "
                    f"{depths[0]:.0f}-{depths[-1]:.0f} m (boat at {sub.depth:.0f} m), nearest "
                    f"{near:.0f} m off the hull; hull {run['dmg0']:.0%} -> {sub.damage:.0%}"
                )
                if sub.destroyed:
                    boat_txt.append("boat lost")
                run = None
        if run is not None and run["dropped"] is None and h.escort.drop_left == 0 and drop_before:
            run["dropped"] = run["charges0"] - h.escort.charges
            if run["dropped"] == 0:
                hunter_txt.append(
                    f"run {runs} abandoned: aim points out of reach for 40 s, nothing dropped"
                )
                run = None
            else:
                rest = "" if run["dropped"] == 6 else " (the rest aimed beyond 150 m)"
                hunter_txt.append(
                    f"run {runs}: {run['dropped']} of 6 charges dropped{rest}, rack reloading 120 s"
                )
        ping = (h.__dict__["_ping_why"], h.escort.next_ping)
        if ping != last_ping:  # a new ping result
            last_ping = ping
            contact = "echo" if ping[0] == "echo" else ping[0].split(":")[1].split("(")[0].strip()
            hist.append(contact)
            del hist[:-2]
            if contact == "echo" and prev_contact != "echo":
                if prev_contact is not None:
                    hunter_txt.append("regains the echo")
                prev_contact = "echo"
            elif contact != "echo" and prev_contact == "echo" and hist[0] != "echo":
                hunter_txt.append(f"loses the echo: {hist[0]}")  # two misses in a row
                prev_contact = hist[0]
            elif prev_contact is None:
                prev_contact = contact
        if boat_txt or hunter_txt:
            flush(t, boat_txt, hunter_txt)
            next_sample = t + 60.0
        elif t >= next_sample:
            flush(t, [], [])
            next_sample = t + 60.0
        if sub.destroyed or (rows and "stand down" in rows[-1][5]):
            break
    end = (
        "boat lost"
        if sub.destroyed
        else ("escorts gave up" if world.__dict__.get("_gave_up") else "track lost")
    )
    info = {
        "end": end,
        "t": world.time,
        "dmg": sub.damage,
        "runs": runs,
        "charges": world.rules.depth_charge.magazine - max(h.escort.charges, 0),
        "battery": sub.battery,
    }
    return rows, info


def find_seed(recipe: str, ranges, outcome: str, seeds: int, difficulty: P.Difficulty):
    """The first (range, seed) whose engagement ends as ``outcome`` ('escaped' or 'lost')."""
    for range_m in ranges:
        for seed in range(seeds):
            r = run(seed, range_m, recipe, difficulty)
            if (r["end"] == "lost") == (outcome == "lost"):
                return range_m, seed
    return None


def render_story(recipe: str, ranges, seeds: int, difficulty: P.Difficulty) -> str:
    out = [f"## {TITLES.get(recipe, recipe)} (`{recipe}`), found {PLACEMENT}\n"]
    for outcome, order in (("escaped", ranges), ("lost", list(reversed(ranges)))):
        pick = find_seed(recipe, order, outcome, seeds, difficulty)
        if pick is None:
            out.append(
                f"### {outcome.capitalize()}: no case\n\nNever happened in {seeds} seeds at "
                f"{', '.join(str(r) for r in ranges)} m.\n"
            )
            continue
        rows, info = story(recipe, pick[0], pick[1], difficulty)
        out.append(f"### {outcome.capitalize()}: found at {pick[0] / 1000:g} km, seed {pick[1]}\n")
        out.append(
            f"**Outcome:** {info['end']} at {mmss(info['t'])}; hull damage {info['dmg']:.0%}; "
            f"{info['runs']} runs, {info['charges']} charges dropped; "
            f"battery {info['battery']:.0%}.\n"
        )
        out.append(STORY_HEAD + "".join("| " + " | ".join(r) + " |\n" for r in rows))
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--difficulty", default="patrol", help="comma-separated levels, or 'all'")
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--recipes", default=",".join(RECIPES))
    ap.add_argument("--ranges", default=",".join(str(r) for r in RANGES))
    ap.add_argument("--proposal", action="store_true", help="measure the proposed rules")
    ap.add_argument(
        "--story",
        default=None,
        metavar="RECIPE",
        help="print one escape and one loss of RECIPE as Markdown tables (first level only)",
    )
    ap.add_argument(
        "--placement",
        choices=("outside", "inside"),
        default="outside",
        help="found outside the screen (default) or inside the convoy (merchants between)",
    )
    args = ap.parse_args()
    global PLACEMENT
    PLACEMENT = args.placement
    names = list(P.DIFFICULTIES) if args.difficulty == "all" else args.difficulty.split(",")
    recipes = args.recipes.split(",")
    ranges = [int(r) for r in args.ranges.split(",")]
    for name in names:
        if args.proposal:
            install(name)
        try:
            if args.story:
                print(render_story(args.story, ranges, args.seeds, P.DIFFICULTIES[name]))
                break
            table(P.DIFFICULTIES[name], recipes, ranges, args.seeds, args.proposal)
        finally:
            uninstall()


if __name__ == "__main__":
    main()
