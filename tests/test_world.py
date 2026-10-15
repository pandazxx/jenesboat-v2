import math

from jenesboat_v2.sim import KNOT, World, default_world, new_ship
from jenesboat_v2.sim.geo import angle_diff, bearing, distance
from jenesboat_v2.sim.params import DETECTION, FREIGHTER, MERCHANT_AI, TYPE_VIIC
from jenesboat_v2.sim.submarine import new_submarine


def run(world: World, seconds: float, dt: float = 0.1) -> None:
    for _ in range(int(round(seconds / dt))):
        world.step(dt)


def drain(world: World, event: str) -> list[dict]:
    return [e for e in world.events if e["event"] == event]


C = 10_000.0  # centre of the test square


def one_merchant(sub_x=5000.0, ship_x=0.0, course=90.0) -> World:
    """A 20 km square, one freighter under way at (C + ship_x, C), the boat surfaced at
    (C + sub_x, C)."""
    player = new_submarine(x=C + sub_x, y=C, heading=0.0)
    ship = new_ship("merchant-1", FREIGHTER, C + ship_x, C, course=course)
    return World(width=2 * C, height=2 * C, player=player, ships=[ship])


def test_default_world_is_an_unescorted_merchant_group():
    world = default_world()
    assert {s.kind for s in world.ships} == {"merchant"}
    assert len(world.ships) == 3


def test_unalerted_merchants_hold_course_and_speed():
    world = default_world()
    world.player.depth = world.player.target_depth = TYPE_VIIC.deep_depth  # invisible
    run(world, 60)
    for ship in world.ships:
        assert math.isclose(ship.heading, ship.course, abs_tol=0.5)
        assert math.isclose(ship.speed, ship.cruise_speed, rel_tol=0.05)
        assert ship.x > 600.0  # moved east
    assert drain(world, "alert") == []


def test_boat_is_kept_in_bounds():
    world = default_world()
    world.player.x = world.width + 5.0
    world.player.y = -5.0
    world.step(0.0)
    assert world.player.x == world.width
    assert world.player.y == 0.0


def test_surfaced_boat_in_range_alerts_the_merchant_after_spot_time():
    world = one_merchant(sub_x=5000.0)  # 5 km: inside the 6 km lookout range
    run(world, DETECTION.spot_time - 0.5)
    assert drain(world, "alert") == []
    run(world, 1.0)
    alerts = drain(world, "alert")
    assert len(alerts) == 1
    assert alerts[0]["reason"] == "sighted" and alerts[0]["ships"] == ["merchant-1"]
    ship = world.ship("merchant-1")
    assert ship.alerted(world.time)
    # Running: full throttle and turning away from the boat.
    run(world, 300)
    assert math.isclose(ship.speed, ship.params.max_speed, rel_tol=0.05)
    away = bearing(world.player.x, world.player.y, ship.x, ship.y)
    assert (
        abs(angle_diff(away, ship.heading))
        < MERCHANT_AI.zigzag_angle + MERCHANT_AI.spread_angle + 5
    )
    assert distance(world.player.x, world.player.y, ship.x, ship.y) > 5000.0
    assert len(drain(world, "alert")) == 1  # refreshed sightings do not spam


def test_boat_out_of_range_is_not_spotted():
    world = one_merchant(sub_x=7000.0)
    run(world, 30)
    assert drain(world, "alert") == []


def test_quiet_periscope_depth_boat_is_not_spotted_at_1500_m():
    world = one_merchant(sub_x=1500.0)
    world.player.depth = world.player.target_depth = TYPE_VIIC.periscope_depth
    run(world, 30)
    assert drain(world, "alert") == []
    world.player.x = C + 900.0  # inside the 1 km periscope range
    run(world, 10)
    assert len(drain(world, "alert")) == 1


def test_fast_periscope_depth_boat_is_spotted_further():
    world = one_merchant(sub_x=2500.0)
    world.player.depth = world.player.target_depth = TYPE_VIIC.periscope_depth
    world.player.speed = world.player.throttle = 1.0
    world.player.speed = 7.0 * KNOT
    run(world, 10)
    assert len(drain(world, "alert")) == 1


def test_deep_boat_is_never_spotted():
    world = one_merchant(sub_x=200.0)
    world.player.depth = world.player.target_depth = TYPE_VIIC.deep_depth
    run(world, 30)
    assert drain(world, "alert") == []


def test_alert_expires_and_the_merchant_returns_to_its_route():
    world = one_merchant(sub_x=5000.0)
    ship = world.ship("merchant-1")
    run(world, 5)
    assert ship.alerted(world.time)
    world.player.depth = world.player.target_depth = TYPE_VIIC.deep_depth  # lose contact
    run(world, MERCHANT_AI.alert_duration + 5, dt=0.5)
    assert not ship.alerted(world.time)
    run(world, 600, dt=0.5)
    assert math.isclose(ship.heading, ship.course, abs_tol=2.0)
    assert math.isclose(ship.speed, ship.cruise_speed, rel_tol=0.05)


def test_alert_group_spreads_the_whole_group():
    world = default_world()
    world.alert_group(world.player.x, world.player.y, "test", by="x")
    headings = set()
    run(world, 400)
    for ship in world.ships:
        assert ship.alerted(world.time)
        headings.add(round(ship.heading))
    assert len(headings) == 3  # spread biases send them different ways


def test_alerted_merchant_far_away_escapes():
    world = one_merchant(sub_x=9_000.0, ship_x=-9_000.0, course=270.0)  # 18 km apart
    ship = world.ship("merchant-1")
    ship.alert(0.0, world.player.x, world.player.y, 1e9)
    run(world, 600, dt=0.5)  # runs west over the edge of the map
    assert ship.escaped and not ship.active
    assert drain(world, "escaped") == [
        {"event": "escaped", "t": world.events[-1]["t"], "ship": "merchant-1"}
    ]


def test_contacts_visual_then_hydrophone_then_none():
    world = one_merchant(sub_x=10_000.0)
    world.step(0.1)
    assert [c.method for c in world.contacts] == ["visual"]
    gained = drain(world, "contact")
    assert gained[0]["ship"] == "merchant-1" and gained[0]["method"] == "visual"
    snap = world.snapshot()["contacts"][0]
    assert snap["range"] == 10_000.0 and snap["bearing"] == 270.0 and snap["type"] == "freighter"

    world.player.depth = world.player.target_depth = TYPE_VIIC.deep_depth
    world.step(0.1)
    assert [c.method for c in world.contacts] == ["hydrophone"]
    assert set(world.snapshot()["contacts"][0]) == {"id", "method", "bearing"}
    assert drain(world, "contact")[-1]["method"] == "hydrophone"

    world.player.speed = 6.0 * KNOT  # own noise masks the hydrophones
    world.step(0.1)
    assert world.contacts == []
    assert drain(world, "contact_lost") == [
        {"event": "contact_lost", "t": 0.3, "ship": "merchant-1"}
    ]


def test_snapshot_shape():
    snap = default_world().snapshot()
    assert set(snap) == {
        "t",
        "world",
        "player",
        "ships",
        "contacts",
        "torpedoes",
        "tonnage",
        "mission",
        "cue",
    }
    assert {s["id"] for s in snap["ships"]} == {"merchant-1", "merchant-2", "merchant-3"}
    assert {s["type"] for s in snap["ships"]} == {"freighter"}


def test_cue_points_at_intel_then_last_seen_then_nothing():
    world = one_merchant(sub_x=10_000.0)  # in sight from the start (10 km < 12 km)
    world.report_intel(C + 3000.0, C + 4000.0, 90.0, 1)
    assert world.events[-1]["event"] == "intel"
    assert world.cue()["kind"] == "intel"  # nothing in sight before the first step
    world.step(0.1)
    assert world.cue() is None  # a visual contact: the map speaks for itself
    world.player.depth = world.player.target_depth = TYPE_VIIC.deep_depth
    world.step(0.1)
    cue = world.cue()
    assert cue["kind"] == "last_seen" and cue["ship"] == "merchant-1"
    assert cue["course"] == 90.0 and cue["bearing"] == 270.0
    # Dead reckoned along the ship's course.
    run(world, 100.0)
    later = world.cue()
    assert later["x"] > cue["x"] and later["y"] == cue["y"]
    assert abs(later["x"] - world.ship("merchant-1").x) < 50.0
    world.ship("merchant-1").sunk = True
    assert world.cue()["kind"] == "intel"  # the last-seen ship is out of play
    world.intel = None
    assert world.cue() is None


def test_boat_leaves_a_track():
    world = default_world()
    world.player.set_throttle(1.0)
    run(world, 120)
    track = world.player_track
    assert len(track) > 5
    assert all(distance(*a, *b) >= 49.0 for a, b in zip(track, track[1:], strict=False))
    assert distance(*track[-1], world.player.x, world.player.y) < 60.0
