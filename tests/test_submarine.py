import math

from jenesboat_v2.sim import PERISCOPE_DEPTH
from jenesboat_v2.sim.submarine import new_submarine


def run(sub, seconds, dt=0.1):
    for _ in range(int(seconds / dt)):
        sub.step(dt)


def test_toggle_dive_goes_to_periscope_depth_then_back():
    sub = new_submarine()
    assert sub.surfaced
    sub.toggle_dive()
    run(sub, PERISCOPE_DEPTH / sub.dive_rate + 1)
    assert math.isclose(sub.depth, PERISCOPE_DEPTH)
    assert not sub.surfaced
    sub.toggle_dive()
    run(sub, PERISCOPE_DEPTH / sub.dive_rate + 1)
    assert sub.depth == 0.0
    assert sub.surfaced


def test_submerged_boat_is_slower():
    surfaced = new_submarine()
    surfaced.set_throttle(1.0)
    run(surfaced, 120)
    submerged = new_submarine()
    submerged.set_throttle(1.0)
    submerged.set_target_depth(PERISCOPE_DEPTH)
    run(submerged, 120)
    assert math.isclose(surfaced.speed, surfaced.params.max_speed)
    assert submerged.speed < surfaced.speed * 0.5
    assert submerged.speed > 0.0


def test_target_depth_is_clamped():
    sub = new_submarine()
    sub.set_target_depth(1e6)
    assert sub.target_depth == sub.max_depth
    sub.set_target_depth(-5)
    assert sub.target_depth == 0.0


def test_snapshot_has_depth_fields():
    sub = new_submarine(x=1, y=2, heading=90)
    snap = sub.snapshot()
    assert snap["depth"] == 0.0
    assert snap["surfaced"] is True
    assert snap["heading"] == 90.0
