"""Flat-ocean geometry: ``x`` east, ``y`` north, bearings in degrees clockwise from north."""

from __future__ import annotations

import math


def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def wrap_degrees(deg: float) -> float:
    return deg % 360.0


def angle_diff(target: float, current: float) -> float:
    """Signed shortest turn from ``current`` to ``target`` in degrees (-180, 180]."""
    d = (target - current) % 360.0
    return d - 360.0 if d > 180.0 else d


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def bearing(ax: float, ay: float, bx: float, by: float) -> float:
    """True bearing from a to b."""
    return wrap_degrees(math.degrees(math.atan2(bx - ax, by - ay)))


def project(x: float, y: float, heading: float, dist: float) -> tuple[float, float]:
    rad = math.radians(heading)
    return x + math.sin(rad) * dist, y + math.cos(rad) * dist


def angle_on_bow(target_heading: float, bearing_from_target: float) -> float:
    """Angle between the target's bow and the line to the observer: 0 = it comes straight at
    you, +90 = you see its starboard side, 180 = it runs away.  Negative = port side."""
    return angle_diff(bearing_from_target, target_heading)


def ray_line_crossing(
    px: float, py: float, p_heading: float, qx: float, qy: float, q_heading: float
) -> tuple[float, float] | None:
    """Distances ``(s, r)`` along a ray from ``p`` and a line through ``q`` where they cross.

    ``s`` is the run along the ray (``None`` when behind it or the lines are parallel),
    ``r`` is signed along ``q``'s heading (negative = the crossing is behind ``q``).
    """
    ux, uy = math.sin(math.radians(p_heading)), math.cos(math.radians(p_heading))
    vx, vy = math.sin(math.radians(q_heading)), math.cos(math.radians(q_heading))
    det = ux * (-vy) - uy * (-vx)
    if abs(det) < 1e-9:
        return None
    dx, dy = qx - px, qy - py
    s = (dx * (-vy) - dy * (-vx)) / det
    r = (ux * dy - uy * dx) / det
    if s < 0:
        return None
    return s, r
