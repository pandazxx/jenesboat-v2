"""raylib drawing.  Only this module and ``app`` touch pyray, so the sim stays testable."""

from __future__ import annotations

import math

from jenesboat_v2._build_info import BUILD_ID
from jenesboat_v2.game import Game
from jenesboat_v2.sim import Vessel

OCEAN = (12, 32, 60, 255)
GRID = (20, 48, 84, 255)
HULL_MERCHANT = (200, 200, 200, 255)
HULL_MILITARY = (240, 120, 90, 255)
SUB_SURFACED = (255, 230, 120, 255)
SUB_SUBMERGED = (140, 170, 210, 255)
WAKE = (90, 130, 170, 255)
HUD = (230, 230, 230, 255)
HUD_DIM = (150, 160, 170, 255)


def _color(rl, rgba):
    return rl.Color(*rgba)


def draw(rl, game: Game, width: int, height: int) -> None:
    world = game.world
    scale = min(width / world.width, height / world.height)

    def to_screen(x: float, y: float) -> tuple[float, float]:
        return x * scale, height - y * scale

    rl.begin_drawing()
    rl.clear_background(_color(rl, OCEAN))

    grid_m = 500.0
    gx = 0.0
    while gx <= world.width:
        sx, _ = to_screen(gx, 0)
        rl.draw_line(int(sx), 0, int(sx), height, _color(rl, GRID))
        gx += grid_m
    gy = 0.0
    while gy <= world.height:
        _, sy = to_screen(0, gy)
        rl.draw_line(0, int(sy), width, int(sy), _color(rl, GRID))
        gy += grid_m

    for ship in world.ships:
        color = HULL_MILITARY if ship.kind == "military" else HULL_MERCHANT
        _draw_hull(rl, ship, to_screen, scale, color)

    sub = world.player
    sx, sy = to_screen(sub.x, sub.y)
    color = SUB_SURFACED if sub.surfaced else SUB_SUBMERGED
    radius = max(5.0, sub.params.length * scale * 0.5)
    if sub.surfaced:
        rl.draw_circle_v(rl.Vector2(sx, sy), radius, _color(rl, color))
    else:
        rl.draw_circle_lines(int(sx), int(sy), radius, _color(rl, color))
    rad = math.radians(sub.heading)
    tip = rl.Vector2(sx + math.sin(rad) * radius * 2.2, sy - math.cos(rad) * radius * 2.2)
    rl.draw_line_ex(rl.Vector2(sx, sy), tip, 2.0, _color(rl, color))

    _draw_hud(rl, game, width, height)
    rl.end_drawing()


def _draw_hull(rl, vessel: Vessel, to_screen, scale: float, rgba) -> None:
    sx, sy = to_screen(vessel.x, vessel.y)
    length = max(8.0, vessel.params.length * scale)
    beam = max(3.0, vessel.params.beam * scale)
    rect = rl.Rectangle(sx, sy, length, beam)
    origin = rl.Vector2(length / 2, beam / 2)
    # heading 0 points up the screen; rectangles are drawn along +x, so offset by -90.
    rl.draw_rectangle_pro(rect, origin, vessel.heading - 90.0, _color(rl, rgba))
    rad = math.radians(vessel.heading)
    wake_len = abs(vessel.speed) * scale * 6.0
    tail = rl.Vector2(sx - math.sin(rad) * wake_len, sy + math.cos(rad) * wake_len)
    rl.draw_line_ex(rl.Vector2(sx, sy), tail, 1.0, _color(rl, WAKE))


def _draw_hud(rl, game: Game, width: int, height: int) -> None:
    sub = game.world.player
    state = "SURFACED" if sub.surfaced else "SUBMERGED"
    line1 = (
        f"HDG {sub.heading:05.1f}   SPD {sub.speed_knots:5.1f} kn   "
        f"THR {sub.throttle:+.2f}   RUD {sub.rudder:+.1f}"
    )
    line2 = f"DEPTH {sub.depth:5.1f} m -> {sub.target_depth:5.1f} m   {state}"
    rl.draw_text(line1, 10, 10, 20, _color(rl, HUD))
    rl.draw_text(line2, 10, 34, 20, _color(rl, HUD))
    rl.draw_text(
        "W/S throttle   A/D rudder   SPACE dive/surface", 10, height - 26, 16, _color(rl, HUD_DIM)
    )
    tag = f"build {BUILD_ID}   t={game.world.time:6.1f}s"
    tw = rl.measure_text(tag, 16)
    rl.draw_text(tag, width - tw - 10, height - 26, 16, _color(rl, HUD_DIM))
