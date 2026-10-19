"""Issue #22: escorts hear a torpedo and comb its track (the ``escort_evade = comb``
strategy), and a torpedo meeting a hull nearly along its axis is a glancing blow."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from jenesboat_v2.game import Game, describe
from jenesboat_v2.sim import params as P
from jenesboat_v2.sim.escort import HUNT, Datum, closest_approach, comb_heading
from jenesboat_v2.sim.geo import angle_diff, distance, project, track_angle
from jenesboat_v2.sim.params import DESTROYER, FREIGHTER, KNOT, TORPEDO_HIT, Level
from jenesboat_v2.sim.submarine import new_submarine
from jenesboat_v2.sim.weapons import Torpedo, solution
from jenesboat_v2.sim.world import World, new_ship

C = 20_000.0


def level(evade: str = "comb", glance_chance: float = 1.0) -> Level:
    """Patrol with the evasion strategy and the glance chance pinned, and an exact sonar fix,
    so each test isolates one rule and a hunter steers a straight line."""
    rules = replace(
        P.PATROL.rules,
        torpedo_hit=replace(TORPEDO_HIT, glance_chance=glance_chance),
        sonar=replace(P.SONAR_ASDIC, position_error=0.0),
    )
    return replace(
        P.PATROL,
        name="test",
        rules=rules,
        strategies=replace(P.PATROL.strategies, escort_evade=evade),
    )


def charging_destroyer(evade: str, range_m: float = 1_500.0, glance_chance: float = 1.0) -> World:
    """A destroyer steaming straight at the boat at 20 kn (it has the boat on sonar and is
    hunting it); the boat at periscope depth, stopped, pointing at it: the #22 shot, down the
    throat."""
    speed = 20.0 * KNOT
    d = new_ship("destroyer-1", DESTROYER, C, C + range_m, course=180.0, speed=speed)
    sub = new_submarine(x=C, y=C, heading=0.0)
    sub.depth = sub.target_depth = P.TYPE_VIIC.periscope_depth
    world = World(
        width=2 * C, height=2 * C, player=sub, ships=[d], level=level(evade, glance_chance)
    )
    # It has had the boat on sonar for a while: hunting, straight at it, no station-keeping
    # wobble in the first seconds.
    world.datum = Datum(sub.x, sub.y, 0.0, "sonar")
    d.escort.mode = HUNT
    return world


def run(world: World, seconds: float, dt: float = 0.1) -> list[dict]:
    seen: list[dict] = []
    for _ in range(int(seconds / dt)):
        world.step(dt)
        seen.extend(world.events)
        world.events.clear()
        if not world.torpedoes and seconds > 60:
            break
    return seen


def kinds(evs: list[dict]) -> list[str]:
    return [e["event"] for e in evs]


# --- the shot down the throat -----------------------------------------------------------------


def test_without_the_strategy_the_down_the_throat_shot_is_a_sure_hit():
    world = charging_destroyer("none")
    assert world.fire() is not None
    evs = run(world, 300)
    assert "torpedo_seen" not in kinds(evs)
    assert "hit" in kinds(evs) and world.ship("destroyer-1").sunk


def test_a_combing_destroyer_hears_the_torpedo_and_dodges_it():
    world = charging_destroyer("comb")
    d = world.ship("destroyer-1")
    assert world.fire() is not None
    evs: list[dict] = []
    swing, flank = 0.0, False
    while world.torpedoes and world.time < 400:
        world.step(0.1)
        evs.extend(world.events)
        world.events.clear()
        if d.escort.evading is not None:  # while dodging: hard over and flank speed
            swing = max(swing, abs(angle_diff(d.heading, 180.0)))
            flank = flank or d.throttle == 1.0
    seen = next(e for e in evs if e["event"] == "torpedo_seen")
    assert seen["ship"] == "destroyer-1" and seen["torpedo"] == 1
    assert seen["cpa"] < P.TORPEDO_EVASION.threat_width
    assert "hit" not in kinds(evs) and "glance" not in kinds(evs)
    assert "torpedo_lost" in kinds(evs) and not d.sunk
    assert swing >= P.TORPEDO_EVASION.comb_angle * 0.8 and flank


def test_the_helm_answers_only_after_the_reaction_time():
    world = charging_destroyer("comb")
    d = world.ship("destroyer-1")
    world.fire()
    evs = run(world, 15)  # closing at ~25 m/s, the torpedo is inside 1.2 km after ~12 s
    assert "torpedo_seen" in kinds(evs)
    assert d.escort.evading == 1 and world.time < d.escort.evade_at  # heard, not yet acting
    assert abs(angle_diff(d.heading, 180.0)) < 2.0
    run(world, P.TORPEDO_EVASION.reaction_time + 5)
    assert abs(angle_diff(d.heading, 180.0)) > 5.0 and d.throttle == 1.0


def test_after_the_torpedo_has_passed_the_destroyer_goes_back_to_its_business():
    world = charging_destroyer("comb")
    d = world.ship("destroyer-1")
    world.fire()
    run(world, 300)
    assert d.escort.evading is None
    evs = run(world, 120)
    assert "torpedo_seen" not in kinds(evs)
    assert d.escort.mode in ("formation", "hunt")  # it is doing something other than dodging


def test_a_torpedo_that_will_pass_wide_is_left_alone():
    world = charging_destroyer("comb")
    d = world.ship("destroyer-1")
    heading_before = d.heading
    world.torpedoes.append(Torpedo(9, C + 600.0, C, 0.0))  # 600 m to one side, parallel
    evs = run(world, 120)
    assert "torpedo_seen" not in kinds(evs)
    assert abs(angle_diff(d.heading, heading_before)) < 5.0


def test_a_torpedo_too_far_to_hear_is_not_noticed_until_it_is_close():
    world = charging_destroyer("comb", range_m=2_000.0)
    world.fire()
    evs = run(world, 15)  # closing at ~25 m/s: still more than 1.2 km apart
    assert "torpedo_seen" not in kinds(evs)
    evs = run(world, 45)
    assert "torpedo_seen" in kinds(evs)


def test_a_steam_torpedo_wake_is_seen_further_than_an_electric_one_is_heard():
    world = charging_destroyer("comb", range_m=1_800.0)
    world.torpedoes.append(Torpedo(5, C, C, 0.0, P.G7A))  # wake seen at 1.5 km x 1.5 lookout
    evs = run(world, 5)
    assert "torpedo_seen" in kinds(evs)
    quiet = charging_destroyer("comb", range_m=1_800.0)
    quiet.torpedoes.append(Torpedo(6, C, C, 0.0, P.G7E))  # wakeless: heard at 1.2 km only
    assert "torpedo_seen" not in kinds(run(quiet, 5))


# --- the geometry helpers -------------------------------------------------------------------------


def test_closest_approach_and_passing():
    ship = new_ship("d", DESTROYER, 0.0, 1_000.0, course=180.0, speed=10.0)
    torp = Torpedo(1, 0.0, 0.0, 0.0)  # straight at it
    cpa, t = closest_approach(ship, torp)
    assert cpa == pytest.approx(0.0, abs=1e-6)
    assert t == pytest.approx(1_000.0 / (10.0 + torp.speed))
    ship.x = 200.0  # offset 200 m, same courses: passes 200 m away
    cpa, t = closest_approach(ship, torp)
    assert cpa == pytest.approx(200.0) and t > 0
    torp.y = 2_000.0  # already past the ship and running away
    assert closest_approach(ship, torp)[1] < 0


def test_comb_heading_opens_the_distance_to_the_side_the_ship_is_on():
    torp = Torpedo(1, 0.0, 0.0, 0.0)  # running north
    right = new_ship("r", DESTROYER, 50.0, 1_000.0, course=180.0)  # east of the track, bow-on
    h = comb_heading(right, torp, 30.0)
    assert h == pytest.approx(150.0)  # toward the torpedo, 30 deg off, eastward component
    left = new_ship("l", DESTROYER, -50.0, 1_000.0, course=180.0)
    assert comb_heading(left, torp, 30.0) == pytest.approx(210.0)
    running = new_ship("a", DESTROYER, 50.0, 1_000.0, course=10.0)  # already running with it
    assert comb_heading(running, torp, 30.0) == pytest.approx(30.0)
    dead_on = new_ship("x", DESTROYER, 0.0, 1_000.0, course=185.0)  # on the track, bow a bit west
    h = comb_heading(dead_on, torp, 30.0)
    assert h == pytest.approx(210.0)  # opens to the west, where the bow already points
    # Every answer has a lateral component away from the track line.
    for ship, h in ((right, 150.0), (left, 210.0)):
        assert math.copysign(1, math.sin(math.radians(h))) == math.copysign(1, ship.x)


# --- the glancing blow ---------------------------------------------------------------------------


def test_track_angle_is_off_the_ships_axis():
    assert track_angle(0.0, 90.0) == 90.0
    assert track_angle(0.0, 180.0) == 0.0  # bow-on
    assert track_angle(0.0, 0.0) == 0.0  # stern-on
    assert track_angle(45.0, 90.0) == 45.0
    assert track_angle(350.0, 170.0) == pytest.approx(0.0)


def freighter_world(torpedo_heading: float, glance_chance: float) -> World:
    """A freighter lying stopped, bow east; a torpedo 400 m from its centre on the given
    heading, aimed at it, already armed."""
    ship = new_ship("freighter-1", FREIGHTER, C, C, course=90.0, speed=0.0)
    sub = new_submarine(x=C, y=C - 8_000.0)
    sub.depth = sub.target_depth = 30.0
    world = World(
        width=2 * C, height=2 * C, player=sub, ships=[ship], level=level("none", glance_chance)
    )
    x, y = project(C, C, torpedo_heading + 180.0, 400.0)
    t = Torpedo(1, x, y, torpedo_heading)
    t.run = P.G7E.arm_distance
    world.torpedoes.append(t)
    return world


def test_a_beam_shot_always_detonates():
    world = freighter_world(0.0, glance_chance=0.0)
    evs = run(world, 60)
    hit = next(e for e in evs if e["event"] == "hit")
    assert hit["angle"] == 90 and world.ship("freighter-1").sunk


def test_a_shot_from_dead_ahead_can_glance_off_and_still_raises_the_alarm():
    world = freighter_world(270.0, glance_chance=0.0)  # running west, into the bow
    evs = run(world, 60)
    glance = next(e for e in evs if e["event"] == "glance")
    assert glance["ship"] == "freighter-1" and glance["angle"] == 0
    assert "hit" not in kinds(evs) and not world.ship("freighter-1").sunk
    assert not world.torpedoes  # the dud is spent
    assert world.ship("freighter-1").alerted(world.time)  # the clang was heard
    assert "alert" in kinds(evs)


def test_glance_chance_one_means_every_hit_counts_and_chance_is_seeded():
    world = freighter_world(270.0, glance_chance=1.0)
    assert "hit" in kinds(run(world, 60))
    outcomes = set()
    for seed in range(20):
        world = freighter_world(270.0, glance_chance=0.5)
        world.rng.seed(seed)
        outcomes.add("hit" if "hit" in kinds(run(world, 60)) else "glance")
    assert outcomes == {"hit", "glance"}


def test_a_shot_just_outside_the_glance_angle_detonates():
    angle = TORPEDO_HIT.glance_angle + 1.0
    world = freighter_world(270.0 + angle, glance_chance=0.0)
    evs = run(world, 60)
    assert "hit" in kinds(evs) and next(e for e in evs if e["event"] == "hit")["angle"] == 31


# --- the fire-control helper tells the player ---------------------------------------------------


def test_the_solution_carries_the_track_angle():
    sol = solution(0.0, 0.0, 0.0, P.G7E, -1_000.0, 2_000.0, 90.0, 8.0 * KNOT)
    assert sol is not None and sol.track_angle == 90.0
    # Nearly head-on (dead head-on has parallel tracks and no crossing to speak of).
    sol = solution(0.0, 0.0, 0.0, P.G7E, 0.0, 2_000.0, 170.0, 8.0 * KNOT)
    assert sol is not None and sol.track_angle == pytest.approx(10.0)
    assert sol.snapshot()["track_angle"] == 10


def test_messages_for_the_new_events():
    assert describe("glance", {"torpedo": 2, "ship": "destroyer-1", "angle": 8}) == (
        "torpedo 2 glanced off destroyer-1 (8 deg off its axis): no detonation"
    )
    assert describe("torpedo_seen", {"ship": "destroyer-2", "torpedo": 3}) == (
        "destroyer-2 heard torpedo 3 and turns to comb its track"
    )


# --- the levels ----------------------------------------------------------------------------------


def test_levels_select_the_strategy_and_the_glance_chance():
    assert P.CADET.strategies.escort_evade == "none"
    assert (
        P.PATROL.strategies.escort_evade == "veteran" or P.PATROL.strategies.escort_evade == "comb"
    )
    assert P.VETERAN.strategies.escort_evade == "comb"
    assert P.CADET.rules.torpedo_hit.glance_chance == 1.0
    assert P.PATROL.rules.torpedo_hit.glance_chance == 0.5
    assert P.VETERAN.rules.torpedo_hit.glance_chance == 0.25
    assert P.TORPEDO_EVASION.hear_range < P.SONAR_ASDIC.range  # a torpedo is loud, not that loud
    assert 0 < P.TORPEDO_HIT.glance_angle < 90


def test_a_hunt_at_patrol_has_dodging_destroyers_and_the_hud_shows_the_track_angle():
    game = Game(seed=2, state_interval=float("inf"), difficulty="patrol")
    world = game.world
    d = next(s for s in world.ships if s.kind == "military")
    sub = world.player
    sub.x, sub.y = project(d.x, d.y, d.heading, 1_200.0)
    sub.heading = (d.heading + 180.0 + 10.0) % 360.0  # nearly down its throat
    sub.depth = sub.target_depth = P.TYPE_VIIC.periscope_depth
    game.update(0.1)
    game.select_target(d.ship_id)
    sol = game.solution()
    assert sol is not None and sol.track_angle < TORPEDO_HIT.glance_angle
    assert game.snapshot()["solution"]["track_angle"] == round(sol.track_angle)
    game.fire()
    for _ in range(600):
        game.update(0.1)
    assert d.escort.evading == 1 or any("comb" in m for _, m in game.messages)
    assert distance(sub.x, sub.y, d.x, d.y) > 0
