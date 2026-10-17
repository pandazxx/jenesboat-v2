import math

import pytest

from jenesboat_v2.sim import KNOT, World, new_ship
from jenesboat_v2.sim.geo import distance
from jenesboat_v2.sim.params import FREIGHTER, G7E, TANKER, TYPE_VIIC
from jenesboat_v2.sim.submarine import new_submarine
from jenesboat_v2.sim.weapons import Torpedo, Tubes, solution

C = 10_000.0


def run(obj, seconds, dt=0.1):
    for _ in range(int(round(seconds / dt))):
        obj.step(dt)


def events(world: World, name: str) -> list[dict]:
    return [e for e in world.events if e["event"] == name]


def world_with(ship_type=FREIGHTER, ship_dx=1000.0, ship_course=0.0, sub_heading=90.0) -> World:
    """Boat at the centre heading ``sub_heading`` at firing depth (20 m: below what lookouts can
    see, so the ship does not run); a stopped ship ``ship_dx`` east of it."""
    player = new_submarine(x=C, y=C, heading=sub_heading)
    player.depth = player.target_depth = TYPE_VIIC.fire_max_depth
    ship = new_ship("target", ship_type, C + ship_dx, C, course=ship_course, speed=0.0)
    return World(width=2 * C, height=2 * C, player=player, ships=[ship])


def test_tubes_fire_and_reload_from_reserves():
    tubes = Tubes(G7E)
    assert tubes.loaded == G7E.tubes and tubes.reserves == G7E.reserves
    for _ in range(G7E.tubes):
        assert tubes.fire()
    assert not tubes.fire()
    run(tubes, G7E.reload_time + 1)
    assert tubes.loaded == 1 and tubes.reserves == G7E.reserves - 1
    run(tubes, G7E.reload_time * (G7E.reserves + 2))
    assert tubes.loaded == G7E.tubes
    assert tubes.reserves == G7E.reserves - G7E.tubes
    assert not tubes.reloading


def test_torpedo_runs_straight_arms_and_expires():
    torp = Torpedo(1, 0.0, 0.0, 90.0, G7E)
    assert not torp.armed
    run(torp, G7E.arm_distance / G7E.speed + 1)
    assert torp.armed and torp.alive
    assert torp.y == pytest.approx(0.0, abs=1e-6) and torp.x > G7E.arm_distance
    run(torp, G7E.max_run / G7E.speed)
    assert not torp.alive
    assert torp.start_x == 0.0 and torp.run >= G7E.max_run


def test_boat_fires_from_the_bow_along_its_heading():
    sub = new_submarine(x=100.0, y=200.0, heading=90.0)
    torp = sub.fire()
    assert torp is not None
    assert torp.x == pytest.approx(100.0 + sub.params.length / 2)
    assert torp.y == pytest.approx(200.0)
    assert torp.heading == 90.0
    assert sub.tubes.loaded == G7E.tubes - 1
    assert sub.snapshot()["tubes"]["loaded"] == G7E.tubes - 1


def test_boat_cannot_fire_when_deep():
    sub = new_submarine()
    sub.depth = TYPE_VIIC.deep_depth
    assert not sub.can_fire
    assert sub.fire() is None
    assert sub.tubes.loaded == G7E.tubes


def test_torpedo_hits_and_sinks_a_freighter_and_scares_the_group():
    world = world_with(ship_dx=1000.0)
    other = new_ship("other", FREIGHTER, C + 1000.0, C + 2000.0, course=0.0)
    world.ships.append(other)
    assert world.fire() is not None
    assert events(world, "fire")[0]["torpedo"] == 1
    run(world, 1000.0 / G7E.speed + 5)
    target = world.ship("target")
    assert target.hits == 1 and target.sunk and not target.active
    assert events(world, "hit")[0]["ship"] == "target"
    assert events(world, "sunk")[0] == {
        "event": "sunk",
        "t": events(world, "sunk")[0]["t"],
        "ship": "target",
        "kind": "merchant",
        "tonnage": FREIGHTER.tonnage,
        "total": FREIGHTER.tonnage,
        "bonus": 0,
    }
    assert world.tonnage == FREIGHTER.tonnage
    assert world.torpedoes == []
    alert = events(world, "alert")[0]
    assert alert["reason"] == "torpedo" and alert["ships"] == ["other"]
    # The threat point is back along the torpedo track, i.e. west of the hit.
    assert other.threat_x < target.x
    # The wreck slows to a stop and stays on the map.
    run(world, 120)
    assert target.speed == 0.0 and target in world.ships


def test_tanker_needs_two_hits():
    world = world_with(ship_type=TANKER, ship_dx=1000.0)
    world.fire()
    world.fire()
    run(world, 1000.0 / G7E.speed + 10)
    tanker = world.ship("target")
    assert tanker.hits == 2 and tanker.sunk
    assert len(events(world, "hit")) == 2
    assert world.tonnage == TANKER.tonnage


def test_torpedo_does_not_arm_inside_arming_distance():
    world = world_with(ship_dx=150.0)
    world.fire()
    run(world, 30)
    assert world.ship("target").hits == 0
    assert events(world, "torpedo_lost") == []  # still running past the ship


def test_miss_runs_out_and_is_reported():
    world = world_with(ship_dx=1000.0, sub_heading=0.0)  # pointing north, ship is east
    world.fire()
    run(world, G7E.max_run / G7E.speed + 5)
    assert world.torpedoes == []
    assert events(world, "torpedo_lost") == [
        {"event": "torpedo_lost", "t": events(world, "torpedo_lost")[0]["t"], "torpedo": 1}
    ]
    assert world.ship("target").hits == 0


def test_fire_refused_is_reported():
    world = world_with()
    world.player.tubes.loaded = 0
    assert world.fire() is None
    assert events(world, "fire_refused")[0]["reason"] == "empty"


def test_solution_leads_a_crossing_target():
    # Boat at the origin pointing north; target 1 km west of the track, 2 km north, going east.
    sol = solution(0.0, 0.0, 0.0, G7E, -1000.0, 2000.0, 90.0, 8.0 * KNOT)
    assert sol is not None
    assert sol.run == pytest.approx(2000.0)
    assert (sol.cross_x, sol.cross_y) == pytest.approx((0.0, 2000.0))
    assert sol.time == pytest.approx(2000.0 / G7E.speed)
    travel = 8.0 * KNOT * sol.time
    assert sol.target_x == pytest.approx(-1000.0 + travel)
    assert sol.error == pytest.approx(1000.0 - travel)  # still short of the crossing
    assert sol.error > 0
    # Fire when the target is exactly ``travel`` short of the crossing: error ~ 0.
    sol2 = solution(0.0, 0.0, 0.0, G7E, -travel, 2000.0, 90.0, 8.0 * KNOT)
    assert sol2.error == pytest.approx(0.0, abs=1e-6)


def test_solution_none_when_out_of_range_or_behind():
    assert solution(0.0, 0.0, 0.0, G7E, -1000.0, 9000.0, 90.0, 4.0) is None
    assert solution(0.0, 0.0, 0.0, G7E, -1000.0, -500.0, 90.0, 4.0) is None
    assert solution(0.0, 0.0, 0.0, G7E, 500.0, 500.0, 0.0, 4.0) is None  # parallel


def test_zero_error_solution_actually_hits():
    """Fire with error ~0 at a moving target and the torpedo must hit the hull."""
    world = world_with(ship_dx=0.0, sub_heading=0.0)
    ship = world.ship("target")
    ship.x, ship.y = C - 1000.0, C + 2000.0
    ship.heading = ship.course = 90.0
    ship.speed = ship.cruise_speed = FREIGHTER.cruise_speed
    ship.throttle = ship.cruise_speed / ship.params.max_speed
    # Run the world until the solution error crosses zero, then fire.
    for _ in range(3000):
        sol = solution(
            world.player.x, world.player.y, 0.0, G7E, ship.x, ship.y, ship.heading, ship.speed
        )
        if sol is not None and sol.error <= 0:
            break
        world.step(0.1)
    assert world.fire() is not None
    run(world, 2000.0 / G7E.speed + 20)
    assert ship.hits == 1
    assert distance(world.player.x, world.player.y, ship.x, ship.y) > 1000.0


def test_snapshot_lists_running_torpedoes():
    world = world_with()
    world.fire()
    world.step(0.1)
    snap = world.snapshot()
    assert len(snap["torpedoes"]) == 1
    assert set(snap["torpedoes"][0]) == {"id", "x", "y", "heading", "run", "armed", "alive"}
    assert snap["tonnage"] == 0
    assert math.isclose(snap["player"]["tubes"]["loaded"], G7E.tubes - 1)
