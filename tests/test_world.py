import math

from jenesboat_v2.sim import default_world


def test_convoy_holds_course_and_speed():
    world = default_world()
    for _ in range(600):
        world.step(0.1)
    for ship in world.ships:
        assert math.isclose(ship.heading, ship.course, abs_tol=0.5)
        assert math.isclose(ship.speed, ship.cruise_speed, rel_tol=0.05)
        assert ship.x > 600.0  # moved east


def test_world_wraps_positions():
    world = default_world()
    world.player.x = world.width + 5.0
    world.player.y = -5.0
    world.step(0.0)
    assert 0.0 <= world.player.x < world.width
    assert 0.0 <= world.player.y < world.height


def test_snapshot_shape():
    snap = default_world().snapshot()
    assert set(snap) == {"t", "world", "player", "ships"}
    assert {s["id"] for s in snap["ships"]} == {
        "merchant-1",
        "merchant-2",
        "merchant-3",
        "escort-1",
    }
    assert {s["kind"] for s in snap["ships"]} == {"merchant", "military"}
