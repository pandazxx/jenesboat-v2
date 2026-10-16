import math

from jenesboat_v2.sim import KNOT, Vessel, VesselParams
from jenesboat_v2.sim.vessel import angle_diff, wrap_degrees

# 10 m/s on a 57.3 m radius turns 10 deg/s (rate = v / r radians).
PARAMS = VesselParams(max_speed=10.0, acceleration=1.0, turn_radius=57.2958, max_turn_rate=10.0)


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


def test_turn_rate_grows_with_speed_and_is_capped():
    slow = Vessel(params=PARAMS, speed=5.0, rudder=1.0)
    fast = Vessel(params=PARAMS, speed=10.0, rudder=1.0)
    assert math.isclose(slow.turn_rate_now(), 5.0, rel_tol=1e-3)
    assert math.isclose(fast.turn_rate_now(), 10.0, rel_tol=1e-3)
    racing = Vessel(params=PARAMS, speed=50.0, rudder=1.0)
    assert racing.turn_rate_now() == PARAMS.max_turn_rate
    astern = Vessel(params=PARAMS, speed=-5.0, rudder=1.0)
    assert astern.turn_rate_now() < 0.0


def test_no_turn_without_way():
    v = Vessel(params=PARAMS)
    v.set_rudder(1.0)
    run(v, 1)
    assert v.heading == 0.0


def test_hull_box_contains_points_along_heading():
    v = Vessel(params=VesselParams(max_speed=1.0, length=100.0, beam=10.0), heading=90.0)
    assert v.contains(40.0, 0.0)  # 40 m ahead along east
    assert v.contains(0.0, 4.0)  # 4 m across
    assert not v.contains(60.0, 0.0)
    assert not v.contains(0.0, 8.0)
    assert v.contains(0.0, 8.0, margin=5.0)


def test_heading_wraps_and_angle_diff_is_shortest():
    assert wrap_degrees(370.0) == 10.0
    assert wrap_degrees(-10.0) == 350.0
    assert angle_diff(10.0, 350.0) == 20.0
    assert angle_diff(350.0, 10.0) == -20.0


def test_speed_in_knots():
    v = Vessel(params=PARAMS, speed=KNOT * 8)
    assert math.isclose(v.speed_knots, 8.0)


def test_telegraph_positions_and_names():
    from jenesboat_v2.sim.vessel import telegraph_by_name, telegraph_index

    v = Vessel(params=PARAMS)
    assert v.telegraph_label == "STOP"
    v.set_telegraph(telegraph_by_name("ahead half"))
    assert v.throttle == 0.5 and v.telegraph_label == "AHEAD HALF"
    v.set_throttle(0.6)  # a scripted throttle still reads as the nearest position
    assert v.telegraph_label == "AHEAD HALF" and telegraph_index(0.9) == 6
    v.telegraph_step(-10)
    assert v.telegraph_label == "ASTERN FULL"
    assert telegraph_by_name("warp 9") is None
    assert v.snapshot()["telegraph"] == "ASTERN FULL"
