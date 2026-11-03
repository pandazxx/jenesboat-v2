#!/usr/bin/env python3
"""Escape study: can a boat that a destroyer has just found get away?

The balance harness of ``docs/ESCAPE_BALANCE.md`` (#34, #37).  A destroyer has found the boat
at ``range`` metres (``--opening sighted``: its lookouts saw the periscope, an exact fix and a
shallow depth band; ``--opening sonar``: a sonar fix with its ring); the boat, at periscope
depth, runs one of a few fixed evasion recipes, one per player archetype where a recipe can
stand for it.  Over a dozen seeds the script counts how often the boat is lost, how much
damage it takes, how many depth charge runs it suffers and how the hunt ended (the boat is
lost, the escorts lose the track, give up on the leash or the clock, or the 30 minutes run
out with the boat still hunted).

    uv run python scripts/escape_study.py                      # patrol, found outside
    uv run python scripts/escape_study.py --difficulty all --seeds 20
    uv run python scripts/escape_study.py --placement inside   # found while attacking
    uv run python scripts/escape_study.py --story veteran --ranges 1500   # one engagement

The rules are the real ones (``sim/params.py``); the ``--proposal`` patch of the first two
prototypes is gone.
"""

from __future__ import annotations

import argparse
import math
import random
from collections import Counter

from jenesboat_v2.sim import escort as E
from jenesboat_v2.sim import params as P
from jenesboat_v2.sim.escort import HUNT
from jenesboat_v2.sim.geo import angle_diff, bearing, clamp, distance, project, wrap_degrees
from jenesboat_v2.sim.params import DESTROYER, FREIGHTER, KNOT
from jenesboat_v2.sim.submarine import new_submarine
from jenesboat_v2.sim.world import World, new_ship

C = 20_000.0
RECIPES = (
    "sit",  # reckless: stays at periscope depth, scope up
    "deep_sit",
    "deep_creep_away",
    "deep_flank_away",
    "deep_flank_90",
    "deep_sprint_then_creep",
    "knuckle",
    "veteran",  # across, then stern-on, slow, under the layer
    "panic",  # 150 m and flank, straight away, for ever
)
RANGES = (1_000, 2_000, 3_000)
OPENING = "sighted"  # or "sonar"
LAYER = 70.0  # m, the thermocline in every study hunt


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
    world.layer_depth = LAYER
    if OPENING == "sighted":  # the periscope seen: exact, shallow band
        E.report(world, sub.x, sub.y, "sighted", ships[3].ship_id)
    else:  # a sonar fix with its ring at this range
        sonar = rules.sonar
        ring = sonar.area_base + sonar.area_span * range_m / sonar.range
        E.report(world, sub.x, sub.y, "sonar", ships[3].ship_id, ring=ring)
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
    elif recipe == "veteran":  # story 2: across for a minute, then stern-on, slow, under the layer
        sub.scope_wanted = False
        sub.set_target_depth(LAYER + 20.0)
        if t < 60.0:
            sub.set_throttle(1.0)
            steer(sub, wrap_degrees(start_heading + 90.0))
        else:
            sub.set_throttle(0.25)
            steer(sub, away)  # stern to the hunter
    elif recipe == "panic":  # story 5: deeper and deeper, flank, straight away from the finder
        sub.scope_wanted = False
        sub.set_target_depth(150.0)
        sub.set_throttle(1.0)
        steer(sub, world.__dict__.setdefault("_away0", away))
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
            if e["event"] == "depth_charge_run":
                runs += 1
            elif e["event"] == "escort_stand_down":
                stand_down += 1
                why = e["reason"]
        world.events.clear()
        if sub.destroyed or stand_down:
            break
    if sub.destroyed:
        reason = "lost"
    elif stand_down:
        reason = {"lost": "lost_track"}.get(why, why)
    else:
        reason = "timeout"
    return {
        "lost": sub.destroyed,
        "damage": sub.damage,
        "runs": runs,
        "t": world.time,
        "end": reason,
    }


# --- the report ----------------------------------------------------------------------------


def table(difficulty: P.Difficulty, recipes, ranges, seeds: int) -> None:
    summary = rules_summary(difficulty)
    print(f"\n## {difficulty.name}, {OPENING} at range, found {PLACEMENT}, {summary}")
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


def rules_summary(difficulty: P.Difficulty) -> str:
    r = difficulty.rules
    return (
        f"{r.scenario.escorts} escorts, sonar {r.sonar.range:.0f} m, arc {r.sonar.arc:.0f} deg, "
        f"leash {r.escort_ai.hunt_leash / 1000:.0f} km / {r.escort_ai.max_hunt_time / 60:.0f} min"
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
    "veteran": "Veteran: 60 s AHEAD FLANK across, then stern-on, AHEAD SLOW, under the layer",
    "panic": "Panic: 150 m, AHEAD FLANK, straight away",
}


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def _hunter_state(h, world: World) -> str:
    kn = h.speed / KNOT
    what = h.escort.intent
    if h.escort.drop_left > 0:
        what = "dropping"
    elif kn > 15.5 and h.escort.mode == HUNT:
        what = "sprint"
    return f"{what} {kn:.0f} kn"


def _track(world: World, h) -> str:
    if world.datum is None:
        return "-"
    d = world.datum
    if d.kind == E.LINE:
        return f"torpedo line, {d.length:.0f} m"
    parts = [f"fix {world.time - d.t:.0f} s old"]
    if d.ring > 0:
        parts.append(f"ring {d.ring:.0f} m")
    if d.assumed:
        parts.append("assumed flight")
    lo, hi = world.rules.depth_charge.bands[d.band % len(world.rules.depth_charge.bands)]
    parts.append(f"band {lo:.0f}-{hi:.0f} m")
    return ", ".join(parts)


def story(recipe: str, range_m: float, seed: int, difficulty: P.Difficulty) -> tuple[list, dict]:
    """Play one engagement and return the table rows and the
    outcome.  A row for every change on either side, and one a minute otherwise."""
    world = setup(seed, range_m, difficulty)
    sub, h = world.player, world.ships[3]
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
                h.escort.echo_why,
                _track(world, h),
            )
        )

    while world.time < 1_800.0:
        orders(recipe, world, world.time, start_heading)
        t = world.time
        boat_txt: list[str] = []
        hunter_txt: list[str] = []
        if first:
            how = "sighted (periscope seen)" if OPENING == "sighted" else "found by sonar"
            boat_txt.append(f"{how} at periscope depth")
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
            told = {
                "sprint": "sprints at 20 kn for the predicted position (set deafened)",
                "hunting": "steers for the predicted position",
                "searching": "nothing to attack: sweeps the search area at 12 kn",
                "sweeping": "sweeps down the torpedo track",
                "returning": "returns to formation",
                "formation": "back on station",
            }
            if state_after in told:
                hunter_txt.append(told[state_after])
        for e in world.events:
            if e["event"] == "depth_charge_run":
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
                hunter_txt.append(f"escorts stand down ({e['reason']})")
            elif e["event"] == "blind_lead":
                kn = world.rules.escort_ai.max_track_speed / KNOT
                hunter_txt.append(f"assumes we ran straight on {e['heading']:03d} at {kn:.1f} kn")
            elif e["event"] == "echo_lost":
                pass  # the sonar column shows it
            elif e["event"] == "run_abandoned":
                hunter_txt.append(f"run {runs} abandoned: aim points out of reach")
            elif e["event"] == "hull_stress":
                boat_txt.append(f"hull groaning at {e['depth']} m (safe {e['safe_depth']} m)")
            elif e["event"] == "layer":
                boat_txt.append(f"crosses the layer at {e['depth']} m")
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
                    f"run {runs}: {run['dropped']} of 6 charges dropped{rest}, rack reloading"
                )
        ping = (h.escort.echo_why, h.escort.next_ping)
        if ping != last_ping:  # a new ping result
            last_ping = ping
            contact = "echo" if ping[0] == "echo" else ping[0].split("(")[0].strip()
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
    down = [r for r in rows if "stand down" in r[5]]
    end = "boat lost" if sub.destroyed else (down[-1][5] if down else "still hunted at 30 min")
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
    ap.add_argument(
        "--opening",
        choices=("sighted", "sonar"),
        default="sighted",
        help="how the boat was found: its periscope seen (default) or a sonar fix",
    )
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
    global PLACEMENT, OPENING
    PLACEMENT = args.placement
    OPENING = args.opening
    names = list(P.DIFFICULTIES) if args.difficulty == "all" else args.difficulty.split(",")
    recipes = args.recipes.split(",")
    ranges = [int(r) for r in args.ranges.split(",")]
    for name in names:
        if args.story:
            print(render_story(args.story, ranges, args.seeds, P.DIFFICULTIES[name]))
            break
        table(P.DIFFICULTIES[name], recipes, ranges, args.seeds)


if __name__ == "__main__":
    main()
