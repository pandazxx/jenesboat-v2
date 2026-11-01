"""Issue #37: the hunt rework.  The sonar's effective reach, cone, shadows and ring fixes
are covered in ``test_escort.py``; here: the attack cycle (datum attack, blind lead, depth
bands, run-over release), the ways a hunt ends, the torpedo line, the explosion cloud, the
periscope state, the safe depth, radar, the thermocline, and the player-facing plumbing."""

from __future__ import annotations

import math
from dataclasses import replace

from jenesboat_v2 import events
from jenesboat_v2.game import Controls, Game, describe
from jenesboat_v2.sim import World, hunting_scenario, new_ship
from jenesboat_v2.sim import params as P
from jenesboat_v2.sim.detection import ship_detection_range
from jenesboat_v2.sim.escort import (
    HUNT,
    INTENT_ATTACKING,
    INTENT_HUNTING,
    INTENT_SEARCHING,
    LINE,
    Datum,
)
from jenesboat_v2.sim.geo import distance, project
from jenesboat_v2.sim.params import DESTROYER, FREIGHTER, KNOT
from jenesboat_v2.sim.submarine import new_submarine
from jenesboat_v2.sim.weapons import Torpedo

C = 20_000.0


def convoy(escorts: int = 1, difficulty: P.Difficulty = P.PATROL) -> World:
    """Three freighters east, the escorts on station, the boat 800 m ahead of destroyer-1 and
    300 m to starboard (inside its cone), stopped at 30 m, heading north."""
    ships = [
        new_ship(f"merchant-{i}", FREIGHTER, C + 800.0 * (i - 1), C, course=90.0, spread=i - 1)
        for i in range(3)
    ]
    ai = difficulty.rules.escort_ai
    for i in range(escorts):
        side = 1.0 if i % 2 == 0 else -1.0
        ships.append(
            new_ship(
                f"destroyer-{i + 1}",
                DESTROYER,
                C + ai.station_ahead,
                C - side * ai.station_abeam,
                course=90.0,
            )
        )
    sub = new_submarine(x=C + 2_000.0, y=C - 1_800.0, heading=0.0)
    sub.depth = sub.target_depth = 30.0
    world = World(width=2 * C, height=2 * C, player=sub, ships=ships, difficulty=difficulty)
    world.layer_depth = None
    return world


def run(world: World, seconds: float, dt: float = 0.1) -> list[dict]:
    seen: list[dict] = []
    for _ in range(int(seconds / dt)):
        world.step(dt)
        seen.extend(world.events)
        world.events.clear()
    return seen


def kinds(evs: list[dict]) -> list[str]:
    return [e["event"] for e in evs]


def hunter(world: World):
    return next(s for s in world.ships if s.kind == "military" and s.escort.mode == HUNT)


# --- the attack cycle ----------------------------------------------------------------------


def test_a_fresh_fix_is_attacked_and_the_run_is_laid_as_the_ship_reaches_the_aim_points():
    world = convoy()
    evs = run(world, 240)
    runs = [e for e in evs if e["event"] == "depth_charge_run"]
    assert runs and runs[0]["band"] == 1 and runs[0]["shallow"] == 40 and runs[0]["deep"] == 80
    bursts = [e for e in evs if e["event"] == "depth_charge"]
    assert len(bursts) >= 3
    assert all(40 <= b["depth"] <= 80 for b in bursts)
    assert INTENT_ATTACKING in {e.get("intent") for e in evs if e["event"] == "escort_intent"}


def test_the_depth_band_moves_on_after_a_pattern_that_did_nothing_and_stays_after_a_hit():
    world = convoy()
    sub = world.player
    sub.depth = sub.target_depth = 140.0  # far below the medium band
    evs = run(world, 900)
    bands = [e["band"] for e in evs if e["event"] == "depth_charge_run"]
    assert len(bands) >= 2 and bands[0] == 1 and bands[1] == 2  # medium missed: deep next
    # A run that hurts confirms its band.
    datum = Datum(sub.x, sub.y, world.time, "sonar", band=2, attacks=1, run_damage=0.0)
    sub.damage = 0.3  # the last pattern did 30 %
    world.datum = datum
    from jenesboat_v2.sim.escort import _start_run

    h = hunter(world)
    h.escort.cooldown_until = -math.inf
    _start_run(world, h, world.rules.escort_ai, world.rules.depth_charge)
    assert world.datum.band == 2


def test_a_stale_fix_gets_one_datum_attack_then_a_blind_lead_along_the_approach_course():
    world = convoy()
    run(world, 40)
    assert world.datum is not None
    sub = world.player
    sub.x, sub.y = C + 2_000.0, C - 10_000.0  # the boat is gone: no more echoes
    names: list[str] = []
    lead = None
    for _ in range(60):  # up to 600 s, stopping the moment the blind lead is announced
        evs = run(world, 10)
        names += kinds(evs)
        lead = next((e for e in evs if e["event"] == "blind_lead"), None)
        if lead is not None:
            break
    assert "depth_charge_run" in names  # the datum attack on the dead-reckoned position
    assert lead is not None
    datum = world.datum
    assert datum is not None and datum.assumed
    speed = math.hypot(datum.vx, datum.vy)
    assert math.isclose(speed, world.rules.escort_ai.max_track_speed)
    heading = math.degrees(math.atan2(datum.vx, datum.vy)) % 360
    assert abs((heading - lead["heading"] + 180) % 360 - 180) < 2
    # Straight away from where the finder was when it found the boat.
    fx, fy = datum.origin_from
    ox, oy, _ = datum.origin
    from jenesboat_v2.sim.geo import bearing

    assert abs((bearing(fx, fy, ox, oy) - lead["heading"] + 180) % 360 - 180) < 30


def test_after_the_blind_attacks_the_hunter_searches_and_the_track_is_lost():
    world = convoy()
    run(world, 40)
    world.player.x, world.player.y = C + 2_000.0, C - 10_000.0
    evs = run(world, 2_000)
    assumed = [e for e in evs if e["event"] == "depth_charge_run" and e["assumed"]]
    assert 1 <= len(assumed) <= world.rules.escort_ai.blind_attacks
    assert INTENT_SEARCHING in {e.get("intent") for e in evs if e["event"] == "escort_intent"}
    down = next(e for e in evs if e["event"] == "escort_stand_down")
    assert down["reason"] == "lost"
    assert world.datum is None


def test_a_run_whose_aim_points_stay_out_of_reach_is_abandoned():
    world = convoy()
    h = hunter(world) if world.datum else world.ships[3]
    h.escort.mode = HUNT
    sub = world.player
    # A datum that runs away from the ship at an impossible speed: the aim points recede.
    world.datum = Datum(h.x + 400.0, h.y, world.time, "sonar", vx=30.0, vy=0.0, assumed=True)
    h.heading = 90.0
    h.speed = 7.0
    from jenesboat_v2.sim.escort import _start_run

    _start_run(world, h, world.rules.escort_ai, world.rules.depth_charge)
    assert h.escort.drop_left > 0
    evs = run(world, world.rules.depth_charge.run_max_time + 5)
    assert "run_abandoned" in kinds(evs)
    assert h.escort.drop_left == 0
    assert sub.damage == 0.0


# --- shadows and clouds --------------------------------------------------------------------


def test_a_pattern_leaves_a_cloud_that_hides_the_boat_and_then_clears():
    world = convoy()
    evs = run(world, 240)
    assert "depth_charge" in kinds(evs)
    assert world.clouds, "the bursts left no cloud"
    cloud = world.clouds[0]
    assert cloud.radius == world.rules.sonar.cloud_radius
    assert cloud.until > world.time
    # Everything bursting near it fed the same cloud rather than making more.
    assert len(world.clouds) <= 2
    run(world, world.rules.sonar.cloud_duration + 5)
    assert all(c.until > world.time for c in world.clouds)  # the old one has gone


# --- how a hunt ends -----------------------------------------------------------------------


def test_the_hunt_ends_on_the_leash_and_on_the_clock():
    world = convoy()
    run(world, 40)
    assert world.datum is not None
    escorts = [s for s in world.ships if s.kind == "military"]
    h = escorts[0]
    cx, cy = world.hunt_from
    h.x, h.y = cx + world.rules.escort_ai.hunt_leash + 500.0, cy
    evs = run(world, 1)
    down = next(e for e in evs if e["event"] == "escort_stand_down")
    assert down["reason"] == "leash" and world.datum is None

    world = convoy()
    run(world, 40)
    world.hunt_since = world.time - world.rules.escort_ai.max_hunt_time - 1
    evs = run(world, 1)
    assert next(e for e in evs if e["event"] == "escort_stand_down")["reason"] == "time"


def test_empty_racks_end_the_hunt():
    world = convoy()
    run(world, 40)
    for s in world.ships:
        if s.kind == "military":
            s.escort.charges = 0
    evs = run(world, 1)
    assert next(e for e in evs if e["event"] == "escort_stand_down")["reason"] == "charges"


# --- the torpedo line ----------------------------------------------------------------------


def test_an_observed_torpedo_gives_the_escorts_its_track_and_the_hunter_sweeps_it():
    world = convoy()
    sub = world.player
    sub.x, sub.y = C + 1_200.0 + 5_000.0, C - 1_500.0  # 5 km east of destroyer-1, out of reach
    d = world.ships[3]
    t = Torpedo(1, d.x + 1_000.0, d.y, 270.0)  # a torpedo 1 km east, running west at the ship
    t.run = 2_000.0
    world.torpedoes.append(t)
    evs = run(world, 30)
    assert "torpedo_line" in kinds(evs)
    datum = world.datum
    assert datum is not None and datum.kind == LINE and datum.band == 0
    assert math.isclose(datum.heading, 90.0)  # back along the track: east
    assert datum.length == t.params.max_run
    run(world, 120)
    h = hunter(world)
    assert h.escort.intent in ("sweeping", INTENT_HUNTING, INTENT_ATTACKING, INTENT_SEARCHING)


# --- the boat ------------------------------------------------------------------------------


def test_the_periscope_is_lowered_by_going_deep_and_raised_only_by_order():
    sub = new_submarine()
    sub.set_target_depth(P.TYPE_VIIC.periscope_depth)
    for _ in range(200):
        sub.step(0.1)
    assert sub.scope_up and sub.periscope_usable
    assert sub.toggle_scope() is False and not sub.scope_up
    assert ship_detection_range(sub, DESTROYER) == 0.0  # nothing shows above the water
    assert sub.toggle_scope() is True and not sub.scope_up  # it takes a few seconds to rise
    for _ in range(int(P.TYPE_VIIC.scope_raise_time / 0.1) + 2):
        sub.step(0.1)
    assert sub.scope_up and ship_detection_range(sub, DESTROYER) > 0.0
    sub.order_deep()
    for _ in range(700):
        sub.step(0.1)
    assert not sub.scope_wanted and not sub.scope_up
    sub.toggle_dive()  # back up to periscope depth: the scope stays down
    for _ in range(700):
        sub.step(0.1)
    assert sub.at_periscope_depth and not sub.scope_up
    assert sub.snapshot()["scope"] == "down"


def test_below_the_safe_depth_the_hull_takes_damage_and_says_so():
    world = convoy(escorts=0)
    sub = world.player
    assert sub.safe_depth == sub.spec.max_depth
    sub.damage = 0.4  # a near miss earlier: safe to 90 m
    assert math.isclose(sub.safe_depth, 90.0)
    sub.depth = sub.target_depth = 130.0  # 40 m too deep
    evs = run(world, 10.5)
    stress = [e for e in evs if e["event"] == "hull_stress"]
    assert stress and stress[0]["safe_depth"] == 90
    expected = 0.4 + sub.spec.overdepth_rate * 40.0 / 20.0 * 10.5
    assert math.isclose(sub.damage, expected, rel_tol=0.05)
    sub.set_target_depth(60.0)
    run(world, 80)
    before = sub.damage
    run(world, 10)
    assert sub.damage == before  # above the safe depth again: no more


def test_radar_finds_a_surfaced_boat_at_veteran_and_is_handled_like_a_sighting():
    world = convoy(escorts=1, difficulty=P.VETERAN)
    sub = world.player
    sub.depth = sub.target_depth = 0.0
    sub.x, sub.y = C + 1_200.0, C - 1_500.0 - 15_000.0  # 15 km from destroyer-1: beyond lookouts
    evs = run(world, 1)
    alarm = next(e for e in evs if e["event"] == "escort_alarm")
    assert alarm["reason"] == "radar"
    assert world.datum is not None and world.datum.ring == 0.0 and world.datum.band == 0
    patrol = convoy(escorts=1)
    patrol.player.depth = patrol.player.target_depth = 0.0
    patrol.player.x, patrol.player.y = C + 1_200.0, C - 1_500.0 - 15_000.0
    assert "escort_alarm" not in kinds(run(patrol, 1))


def test_the_thermocline_is_drawn_per_hunt_and_told_once_the_boat_crosses_it():
    world = hunting_scenario(5, difficulty=P.PATROL)
    assert world.layer_depth is not None
    assert P.SEA.layer_min <= world.layer_depth <= P.SEA.layer_max
    assert world.snapshot()["layer"] is None  # unknown until crossed
    sub = world.player
    sub.depth = sub.target_depth = world.layer_depth + 5.0
    evs = run(world, 0.5)
    assert next(e for e in evs if e["event"] == "layer")["depth"] == world.layer_depth
    assert world.snapshot()["layer"] == world.layer_depth
    # Some veteran hunts have no layer at all.
    assert any(hunting_scenario(s, difficulty=P.VETERAN).layer_depth is None for s in range(30))


# --- the player's side ---------------------------------------------------------------------


def test_the_scope_control_and_the_new_messages():
    log: list[str] = []
    events.set_sink(log.append)
    try:
        game = Game(seed=1, state_interval=float("inf"))
        sub = game.world.player
        sub.set_target_depth(P.TYPE_VIIC.periscope_depth)
        game.update(20.0)
        game.apply(Controls(scope=True), 0.1)
        assert not sub.scope_wanted
        assert game.messages[-1][1] == "periscope down"
        assert any(e and e["event"] == "scope" for e in map(events.parse, log))
    finally:
        events.set_sink(None)
    assert "lost the echo" in describe("echo_lost", {"ship": "d1", "why": "boat behind the cloud"})
    assert "charges set 40-80 m" in describe(
        "depth_charge_run", {"ship": "d1", "charges": 30, "band": 1, "shallow": 40, "deep": 80}
    )
    assert "on a guess" in describe(
        "depth_charge_run",
        {"ship": "d1", "charges": 30, "band": 1, "shallow": 40, "deep": 80, "assumed": True},
    )
    assert "will not leave the convoy" in describe("escort_stand_down", {"reason": "leash"})
    assert "HULL GROANING" in describe(
        "hull_stress", {"depth": 130, "safe_depth": 90, "level": 0.45, "destroyed": False}
    )
    assert "thermocline" in describe("layer", {"depth": 70})
    assert "assumes we ran off on 225" in describe("blind_lead", {"ship": "d1", "heading": 225})
    assert "sweep" in describe("torpedo_line", {"by": "d1"})
    assert describe("escort_intent", {"ship": "d1", "intent": "formation"}) is None
    assert describe("escort_intent", {"ship": "d1", "intent": "searching"}) == "d1 is searching"


def test_the_battle_log_can_be_written_to_a_file(tmp_path):
    path = tmp_path / "battle.jsonl"
    events.log_to_file(str(path))
    try:
        events.emit("ready", build="test")
        events.emit("state", t=1.0)
    finally:
        events.log_to_file(None)
    lines = path.read_text().splitlines()
    assert len(lines) == 2 and all(line.startswith(events.PREFIX) for line in lines)
    assert events.parse(lines[0])["event"] == "ready"


def test_the_snapshot_carries_what_the_hud_draws():
    world = convoy()
    run(world, 240)
    snap = world.snapshot()
    assert snap["datum"] is not None and set(snap["datum"]) >= {"ring", "kind", "band", "assumed"}
    assert isinstance(snap["clouds"], list) and snap["echo_reach"] >= 0
    d = next(s for s in snap["ships"] if s["kind"] == "military")
    assert set(d) >= {"intent", "echo", "sonar_m"}
    assert snap["player"]["scope"] in ("up", "down", "rising")
    assert snap["player"]["safe_depth"] == round(150 * (1 - world.player.damage))


def test_sweep_search_points_the_cone_through_the_search_area():
    from jenesboat_v2.sim.escort import sweep_search

    world = convoy()
    h = world.ships[3]
    h.escort.mode = HUNT
    world.datum = Datum(h.x + 2_000.0, h.y, world.time - 400.0, "sonar", search_since=world.time)
    p = world.rules.escort_ai
    visited = set()
    for _ in range(12_000):
        sweep_search(world, h, p)
        h.step(0.1)
        visited.add(h.escort.search_leg % 4)
        if len(visited) == 4:
            break
    assert visited == {0, 1, 2, 3}
    # Two of the four legs cross the middle: at some point the ship passed within 200 m of it.
    world.datum = Datum(h.x + 2_000.0, h.y, world.time - 400.0, "sonar", search_since=world.time)
    h.escort.search_leg = 0
    nearest = math.inf
    for _ in range(12_000):
        sweep_search(world, h, p)
        h.step(0.1)
        nearest = min(nearest, distance(h.x, h.y, world.datum.x, world.datum.y))
        if h.escort.search_leg >= 2:
            break
    assert nearest < p.search_start  # within the first box's radius, inside the cone


def test_levels_dial_the_hunt(_=None):
    cadet, patrol, veteran = P.CADET.rules, P.PATROL.rules, P.VETERAN.rules
    assert cadet.sonar.arc < patrol.sonar.arc < veteran.sonar.arc
    assert cadet.sonar.cloud_duration > patrol.sonar.cloud_duration > veteran.sonar.cloud_duration
    assert (
        cadet.escort_ai.blind_attacks
        < patrol.escort_ai.blind_attacks
        < veteran.escort_ai.blind_attacks
    )
    assert (
        cadet.escort_ai.max_hunt_time
        < patrol.escort_ai.max_hunt_time
        < veteran.escort_ai.max_hunt_time
    )
    assert cadet.depth_charge.pattern_cooldown > patrol.depth_charge.pattern_cooldown
    assert patrol.depth_charge.pattern_cooldown > veteran.depth_charge.pattern_cooldown
    assert replace(P.PATROL.strategies).escort_search == "sweep"
    assert project(0.0, 0.0, 90.0, 1.0)[0] > 0  # keep the import honest
    assert KNOT > 0
