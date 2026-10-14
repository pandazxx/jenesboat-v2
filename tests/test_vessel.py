import math

from jenesboat_v2.sim import KNOT, Vessel, VesselParams
from jenesboat_v2.sim.vessel import angle_diff, wrap_degrees

PARAMS = VesselParams(max_speed=10.0, acceleration=1.0, turn_rate=10.0)


def run(vessel: Vessel, seconds: float, dt: float = 0.1) -> None:
    for _ in range(int(seconds / dt)):
        vessel.step(dt)


def test_full_ahead_reaches_max_speed_and_moves_north():
    v = Vessel(params=PARAMS)
    v.set_throttle(1.0)
    run(v, 20)
    assert math.isclose(v.speed, 10.0)
    assert v.x == 0.0
    assert v.y > 0.0


def test_throttle_and_rudder_are_clamped():
    v = Vessel(params=PARAMS)
    v.set_throttle(5.0)
    v.set_rudder(-7.0)
    assert v.throttle == 1.0
    assert v.rudder == -1.0


def test_astern_is_slower_than_ahead():
    v = Vessel(params=PARAMS)
    v.set_throttle(-1.0)
    run(v, 20)
    assert math.isclose(v.speed, -5.0)
    assert v.y < 0.0


def test_starboard_rudder_turns_clockwise_once_moving():
    v = Vessel(params=PARAMS, speed=10.0, throttle=1.0)
    v.set_rudder(1.0)
    run(v, 1)
    assert 9.0 < v.heading < 11.0
    assert v.x > 0.0


def test_no_turn_without_way():
    v = Vessel(params=PARAMS)
    v.set_rudder(1.0)
    run(v, 1)
    assert v.heading == 0.0


def test_heading_wraps_and_angle_diff_is_shortest():
    assert wrap_degrees(370.0) == 10.0
    assert wrap_degrees(-10.0) == 350.0
    assert angle_diff(10.0, 350.0) == 20.0
    assert angle_diff(350.0, 10.0) == -20.0


def test_speed_in_knots():
    v = Vessel(params=PARAMS, speed=KNOT * 8)
    assert math.isclose(v.speed_knots, 8.0)
