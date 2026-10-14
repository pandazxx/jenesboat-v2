import math

from jenesboat_v2.sim import KNOT, hunting_scenario
from jenesboat_v2.sim.geo import angle_diff, distance, ray_line_crossing
from jenesboat_v2.sim.params import TANKER
from jenesboat_v2.sim.scenario import (
    CONTACT_RANGE,
    INTEL_COURSE_ERROR,
    INTEL_POSITION_ERROR,
    PASS_OFFSET,
    WORLD_SIZE,
)


def test_same_seed_same_world():
    a, b = hunting_scenario(42), hunting_scenario(42)
    assert a.snapshot() == b.snapshot()
    assert hunting_scenario(43).snapshot() != a.snapshot()


def test_group_is_out_of_sight_but_on_a_route_past_the_boat():
    for seed in range(20):
        world = hunting_scenario(seed)
        sub = world.player
        assert (sub.x, sub.y) == (WORLD_SIZE / 2, WORLD_SIZE / 2)
        assert len(world.ships) == 3 and sum(s.type is TANKER for s in world.ships) == 1
        assert world.contacts == [] and world.mission()["status"] == "active"
        for ship in world.ships:
            d = distance(sub.x, sub.y, ship.x, ship.y)
            assert CONTACT_RANGE - 1500 < d < CONTACT_RANGE + 1500
            assert math.isclose(ship.speed, 8.0 * KNOT)
            assert 0 < ship.x < WORLD_SIZE and 0 < ship.y < WORLD_SIZE
            # The route passes within PASS_OFFSET (+ formation width) of the boat, ahead of it.
            cross = ray_line_crossing(ship.x, ship.y, ship.heading, sub.x, sub.y, ship.heading + 90)
            assert cross is not None
            along, side = cross
            assert along > 0 and abs(side) < PASS_OFFSET + 1500


def test_intel_is_roughly_right():
    for seed in range(20):
        world = hunting_scenario(seed)
        intel = next(e for e in world.events if e["event"] == "intel")
        centre_x = sum(s.x for s in world.ships) / 3
        centre_y = sum(s.y for s in world.ships) / 3
        assert (
            distance(intel["x"], intel["y"], centre_x, centre_y) < INTEL_POSITION_ERROR * 1.5 + 300
        )
        course = world.ships[0].course
        assert abs(angle_diff(intel["course"], course)) <= INTEL_COURSE_ERROR + 1
        assert intel["ships"] == 3 and 0 <= intel["bearing"] < 360
