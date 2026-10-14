import math

import pytest

from jenesboat_v2.sim.geo import (
    angle_on_bow,
    bearing,
    distance,
    project,
    ray_line_crossing,
)


def test_bearing_and_distance():
    assert bearing(0, 0, 0, 10) == 0.0
    assert bearing(0, 0, 10, 0) == 90.0
    assert bearing(0, 0, 0, -10) == 180.0
    assert bearing(0, 0, -10, 0) == 270.0
    assert distance(0, 0, 3, 4) == 5.0


def test_project_round_trips():
    x, y = project(100.0, 100.0, 45.0, math.sqrt(2) * 10)
    assert x == pytest.approx(110.0)
    assert y == pytest.approx(110.0)


def test_angle_on_bow():
    # Target heads north; we are due east of it -> we see its starboard side.
    assert angle_on_bow(0.0, 90.0) == 90.0
    assert angle_on_bow(0.0, 270.0) == -90.0
    assert angle_on_bow(90.0, 90.0) == 0.0  # coming straight at us
    assert angle_on_bow(90.0, 270.0) == 180.0  # running away


def test_ray_line_crossing():
    # Ray north from the origin; line east through (0, 1000) starting at (-500, 1000).
    s, r = ray_line_crossing(0, 0, 0.0, -500, 1000, 90.0)
    assert s == pytest.approx(1000.0)
    assert r == pytest.approx(500.0)
    # Target already past the crossing: r negative.
    s, r = ray_line_crossing(0, 0, 0.0, 500, 1000, 90.0)
    assert r == pytest.approx(-500.0)
    # Crossing behind the ray, or parallel.
    assert ray_line_crossing(0, 0, 0.0, 0, -1000, 90.0) is None
    assert ray_line_crossing(0, 0, 0.0, 100, 100, 180.0) is None
