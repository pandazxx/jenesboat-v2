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


def setup(seed: int, range_m: float, difficulty: P.Difficulty) -> World:
    """The boat at periscope depth, just pinged by the nearest of the level's destroyers,
    which is ``range_m`` away and already hunting; the convoy 2 km behind the destroyer."""
    rules = difficulty.rules
    rng = random.Random(seed)
    sub = new_submarine(x=C, y=C, heading=rng.uniform(0.0, 360.0))
    sub.depth = sub.target_depth = P.TYPE_VIIC.periscope_depth
    brg = rng.uniform(0.0, 360.0)
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
    sure_fraction: float = 0.4  # a ping inside this fraction of the reach is a sure fix
    own_noise_factor: float = 0.25  # reach while sprinting (sheet: 0.4)
    settle_time: float = 20.0  # s after slowing below own_noise_speed before the set works
    loud_speed: float = 5.0 * KNOT  # a boat faster than this is heard further
    loud_factor: float = 1.3
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
    reach = E.sonar_range(world, ship, sonar)
    sub = world.player
    mem = ship.__dict__
    if abs(ship.speed) > sonar.own_noise_speed:  # sprinting: nearly deaf, and the set must settle
        reach = reach / sonar.own_noise_factor * PROP.own_noise_factor
        mem["_fast_until"] = world.time + PROP.settle_time
    elif world.time < mem.get("_fast_until", -1.0):
        reach = 0.0
    if abs(sub.speed) > PROP.loud_speed:
        reach *= PROP.loud_factor
    state.sonar_range = reach
    d = distance(ship.x, ship.y, sub.x, sub.y)
    blind = max(sonar.min_range, sub.depth * PROP.depth_blind_ratio)
    if d < blind or d > reach:
        return
    relative = abs(angle_diff(bearing(ship.x, ship.y, sub.x, sub.y), ship.heading))
    if relative > 180.0 - PROP.baffle_angle:  # in the baffles astern
        return
    sure = PROP.sure_fraction * reach
    chance = 1.0 if d <= sure else clamp((reach - d) / (reach - sure), 0.0, 1.0)
    if world.rng.random() > chance:
        return
    ex = world.rng.uniform(-sonar.position_error, sonar.position_error)
    ey = world.rng.uniform(-sonar.position_error, sonar.position_error)
    E.report(world, sub.x + ex, sub.y + ey, "sonar", ship.ship_id)


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
    print(f"\n## {difficulty.name}, {rules} rules, {rules_summary(difficulty, proposal)}")
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
        f"blind x{prop.depth_blind_ratio:.1f}, baffle {prop.baffle_angle:.0f} deg"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--difficulty", default="patrol", help="comma-separated levels, or 'all'")
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--recipes", default=",".join(RECIPES))
    ap.add_argument("--ranges", default=",".join(str(r) for r in RANGES))
    ap.add_argument("--proposal", action="store_true", help="measure the proposed rules")
    args = ap.parse_args()
    names = list(P.DIFFICULTIES) if args.difficulty == "all" else args.difficulty.split(",")
    recipes = args.recipes.split(",")
    ranges = [int(r) for r in args.ranges.split(",")]
    for name in names:
        if args.proposal:
            install(name)
        try:
            table(P.DIFFICULTIES[name], recipes, ranges, args.seeds, args.proposal)
        finally:
            uninstall()


if __name__ == "__main__":
    main()
