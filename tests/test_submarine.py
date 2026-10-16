import math

from jenesboat_v2.sim import PERISCOPE_DEPTH
from jenesboat_v2.sim.params import HOUR, TYPE_VIIC
from jenesboat_v2.sim.submarine import new_submarine


def run(sub, seconds, dt=0.1):
    for _ in range(int(seconds / dt)):
        sub.step(dt)


def test_toggle_dive_goes_to_periscope_depth_then_back():
    sub = new_submarine()
    assert sub.surfaced and sub.depth_band == "surfaced"
    sub.toggle_dive()
    run(sub, PERISCOPE_DEPTH / sub.spec.dive_rate + 1)
    assert math.isclose(sub.depth, PERISCOPE_DEPTH)
    assert not sub.surfaced
    assert sub.depth_band == "periscope" and sub.periscope_usable
    sub.toggle_dive()
    run(sub, PERISCOPE_DEPTH / sub.spec.dive_rate + 1)
    assert sub.depth == 0.0
    assert sub.surfaced


def test_deep_order_and_toggle_back_to_periscope_depth():
    sub = new_submarine()
    sub.order_deep()
    run(sub, TYPE_VIIC.deep_depth / sub.spec.dive_rate + 1)
    assert math.isclose(sub.depth, TYPE_VIIC.deep_depth)
    assert sub.depth_band == "deep"
    assert not sub.periscope_usable
    sub.toggle_dive()  # from deep, Space comes up to periscope depth, not the surface
    assert sub.target_depth == PERISCOPE_DEPTH
    sub.toggle_dive()
    assert sub.target_depth == 0.0


def test_submerged_boat_is_slower():
    surfaced = new_submarine()
    surfaced.set_throttle(1.0)
    run(surfaced, 120)
    submerged = new_submarine()
    submerged.set_throttle(1.0)
    submerged.set_target_depth(PERISCOPE_DEPTH)
    run(submerged, 120)
    assert math.isclose(surfaced.speed, surfaced.params.max_speed)
    assert math.isclose(submerged.speed, TYPE_VIIC.submerged_speed)
    assert submerged.speed < surfaced.speed * 0.5


def test_target_depth_is_clamped():
    sub = new_submarine()
    sub.set_target_depth(1e6)
    assert sub.target_depth == sub.spec.max_depth
    sub.set_target_depth(-5)
    assert sub.target_depth == 0.0


def test_hydrophone_needs_depth_and_quiet():
    sub = new_submarine()
    assert not sub.hydrophone_usable  # surfaced
    sub.depth = PERISCOPE_DEPTH
    sub.speed = 2.0 * 0.514444
    assert sub.hydrophone_usable
    sub.speed = 6.0 * 0.514444
    assert not sub.hydrophone_usable


def test_battery_drains_submerged_and_recharges_surfaced():
    sub = new_submarine()
    sub.depth = sub.target_depth = PERISCOPE_DEPTH
    sub.set_throttle(1.0)
    run(sub, 600, dt=1.0)  # 10 min flat out
    expected = 1.0 - 600 / (TYPE_VIIC.battery_full_speed_hours * HOUR)
    assert math.isclose(sub.battery, expected, rel_tol=0.02)
    creeping = new_submarine()
    creeping.depth = creeping.target_depth = PERISCOPE_DEPTH
    run(creeping, 600, dt=1.0)
    assert creeping.battery > sub.battery
    sub.set_target_depth(0.0)
    sub.set_throttle(0.0)
    run(sub, 60, dt=1.0)
    level = sub.battery
    run(sub, 600, dt=1.0)
    assert sub.battery > level


def test_flat_battery_limits_submerged_speed():
    sub = new_submarine()
    sub.depth = sub.target_depth = PERISCOPE_DEPTH
    sub.battery = 0.0
    sub.set_throttle(1.0)
    run(sub, 120)
    assert math.isclose(
        sub.speed, TYPE_VIIC.submerged_speed * TYPE_VIIC.battery_empty_speed_fraction
    )
    assert sub.battery == 0.0


def test_snapshot_has_depth_fields():
    sub = new_submarine(x=1, y=2, heading=90)
    snap = sub.snapshot()
    assert snap["depth"] == 0.0
    assert snap["surfaced"] is True
    assert snap["heading"] == 90.0
    assert snap["band"] == "surfaced"
    assert snap["battery"] == 1.0
