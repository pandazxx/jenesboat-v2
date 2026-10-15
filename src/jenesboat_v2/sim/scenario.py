"""Seeded hunting scenarios: an unescorted merchant group somewhere out there."""

from __future__ import annotations

import random

from jenesboat_v2.sim.geo import bearing, project, wrap_degrees
from jenesboat_v2.sim.params import FREIGHTER, TANKER
from jenesboat_v2.sim.submarine import new_submarine
from jenesboat_v2.sim.world import World, new_ship

WORLD_SIZE = 40_000.0  # m, square
CONTACT_RANGE = 14_000.0  # m from the boat to the group at the start (beyond the lookouts)
PASS_OFFSET = 4_000.0  # m, the route passes within this of the boat's start, either side
SPACING = 800.0  # m between ships abreast
INTEL_POSITION_ERROR = 2_000.0  # m, each axis
INTEL_COURSE_ERROR = 15.0  # degrees


def hunting_scenario(seed: int | None = None) -> World:
    """The boat in the middle of an empty ocean; a group of merchants 14 km away on a route
    that will pass a few km from it.  The world starts with an ``intel`` event (the radio
    report that tells the player roughly where to look)."""
    rng = random.Random(seed)
    half = WORLD_SIZE / 2
    player = new_submarine(x=half, y=half, heading=rng.uniform(0.0, 360.0))

    direction = rng.uniform(0.0, 360.0)
    cx, cy = project(half, half, direction, CONTACT_RANGE)
    # The route aims at a point beside the boat so the player must still move to intercept.
    aim_x, aim_y = project(half, half, direction + 90.0, rng.uniform(-PASS_OFFSET, PASS_OFFSET))
    course = bearing(cx, cy, aim_x, aim_y)

    types = [FREIGHTER, FREIGHTER, TANKER]
    rng.shuffle(types)
    ships = []
    for i, ship_type in enumerate(types):
        abreast = (i - (len(types) - 1) / 2) * SPACING
        stagger = rng.uniform(-200.0, 200.0)
        x, y = project(cx, cy, course + 90.0, abreast)
        x, y = project(x, y, course, stagger)
        ships.append(new_ship(f"{ship_type.name}-{i + 1}", ship_type, x, y, course, spread=i - 1))

    world = World(width=WORLD_SIZE, height=WORLD_SIZE, player=player, ships=ships)
    rx = cx + rng.uniform(-INTEL_POSITION_ERROR, INTEL_POSITION_ERROR)
    ry = cy + rng.uniform(-INTEL_POSITION_ERROR, INTEL_POSITION_ERROR)
    reported_course = wrap_degrees(course + rng.uniform(-INTEL_COURSE_ERROR, INTEL_COURSE_ERROR))
    world.report_intel(rx, ry, reported_course, len(ships))
    return world
