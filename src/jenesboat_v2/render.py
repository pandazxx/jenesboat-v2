"""raylib drawing.  Only this module and ``app`` touch pyray, so the sim stays testable.

The camera follows the boat.  Only what the boat knows is drawn: visual contacts as hull
boxes, hydrophone contacts as bearing lines, wrecks, running torpedoes, and the fire-control
helper (aiming line, crossing point and lead marker) for the selected target.
"""

from __future__ import annotations

import math

from jenesboat_v2._build_info import BUILD_ID
from jenesboat_v2.game import Game
from jenesboat_v2.sim.detection import HYDROPHONE, VISUAL, ship_detection_range
from jenesboat_v2.sim.geo import angle_on_bow, bearing, project

OCEAN = (12, 32, 60, 255)
GRID = (20, 48, 84, 255)
EDGE = (60, 90, 130, 255)
HULL_MERCHANT = (200, 200, 200, 255)
HULL_MILITARY = (240, 120, 90, 255)
WRECK = (110, 110, 120, 255)
SUB_SURFACED = (255, 230, 120, 255)
SUB_SUBMERGED = (140, 170, 210, 255)
WAKE = (90, 130, 170, 255)
TRACK = (120, 150, 190, 255)
HYDRO = (120, 200, 160, 255)
TORPEDO = (255, 255, 255, 255)
AIM = (200, 180, 90, 160)
LEAD_OK = (120, 240, 120, 255)
LEAD_BAD = (240, 150, 90, 255)
BUBBLE = (200, 90, 90, 110)
HUD = (230, 230, 230, 255)
HUD_DIM = (150, 160, 170, 255)
ALERT = (255, 120, 90, 255)

TRACK_LENGTH = 12_000.0  # m of projected track drawn ahead of the target


def _color(rl, rgba):
    return rl.Color(*rgba)


class Camera:
    def __init__(self, cx: float, cy: float, zoom: float, width: int, height: int) -> None:
        self.cx, self.cy, self.zoom, self.width, self.height = cx, cy, zoom, width, height

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return self.width / 2 + (x - self.cx) / self.zoom, self.height / 2 - (
            y - self.cy
        ) / self.zoom

    def px(self, metres: float) -> float:
        return metres / self.zoom


def draw(rl, game: Game, width: int, height: int) -> None:
    world = game.world
    sub = world.player
    cam = Camera(sub.x, sub.y, game.zoom, width, height)

    rl.begin_drawing()
    rl.clear_background(_color(rl, OCEAN))
    _draw_grid(rl, cam, world.width, world.height)

    for ship in world.ships:
        if ship.sunk:
            _draw_wreck(rl, cam, ship.x, ship.y)
    for contact in world.contacts:
        if contact.method == HYDROPHONE:
            _draw_bearing_line(rl, cam, sub.x, sub.y, contact.bearing)
    target = game.target()
    for contact in world.contacts:
        if contact.method == VISUAL and contact.x is not None:
            ship = world.ship(contact.ship_id)
            color = HULL_MILITARY if ship.kind == "military" else HULL_MERCHANT
            if target is not None and contact.ship_id == target.ship_id:
                _draw_dashed(rl, cam, ship.x, ship.y, ship.heading, TRACK_LENGTH, TRACK)
            _draw_hull(rl, cam, ship.x, ship.y, ship.heading, ship.speed, ship.params, color)

    for torp in world.torpedoes:
        _draw_torpedo(rl, cam, torp)

    _draw_fire_control(rl, cam, game)
    _draw_sub(rl, cam, game)
    _draw_hud(rl, game, width, height)
    rl.end_drawing()


def _draw_grid(rl, cam: Camera, world_w: float, world_h: float) -> None:
    step = 1000.0
    x0 = math.floor((cam.cx - cam.width / 2 * cam.zoom) / step) * step
    x1 = cam.cx + cam.width / 2 * cam.zoom
    gx = x0
    while gx <= x1:
        sx, _ = cam.to_screen(gx, 0.0)
        rl.draw_line(int(sx), 0, int(sx), cam.height, _color(rl, GRID))
        gx += step
    y0 = math.floor((cam.cy - cam.height / 2 * cam.zoom) / step) * step
    y1 = cam.cy + cam.height / 2 * cam.zoom
    gy = y0
    while gy <= y1:
        _, sy = cam.to_screen(0.0, gy)
        rl.draw_line(0, int(sy), cam.width, int(sy), _color(rl, GRID))
        gy += step
    # The edge of the map.
    ax, ay = cam.to_screen(0.0, world_h)
    bx, by = cam.to_screen(world_w, 0.0)
    rl.draw_rectangle_lines(int(ax), int(ay), int(bx - ax), int(by - ay), _color(rl, EDGE))


def _draw_hull(rl, cam: Camera, x, y, heading, speed, params, rgba) -> None:
    sx, sy = cam.to_screen(x, y)
    length = max(8.0, cam.px(params.length))
    beam = max(3.0, cam.px(params.beam))
    rect = rl.Rectangle(sx, sy, length, beam)
    origin = rl.Vector2(length / 2, beam / 2)
    # heading 0 points up the screen; rectangles are drawn along +x, so offset by -90.
    rl.draw_rectangle_pro(rect, origin, heading - 90.0, _color(rl, rgba))
    rad = math.radians(heading)
    wake_len = max(0.0, cam.px(abs(speed) * 60.0))  # one minute of travel
    tail = rl.Vector2(sx - math.sin(rad) * wake_len, sy + math.cos(rad) * wake_len)
    rl.draw_line_ex(rl.Vector2(sx, sy), tail, 1.0, _color(rl, WAKE))


def _draw_wreck(rl, cam: Camera, x, y) -> None:
    sx, sy = cam.to_screen(x, y)
    r = 5
    rl.draw_line(int(sx - r), int(sy - r), int(sx + r), int(sy + r), _color(rl, WRECK))
    rl.draw_line(int(sx - r), int(sy + r), int(sx + r), int(sy - r), _color(rl, WRECK))


def _draw_bearing_line(rl, cam: Camera, x, y, brg) -> None:
    _draw_dashed(rl, cam, x, y, brg, 20_000.0, HYDRO, dash=400.0)


def _draw_dashed(rl, cam: Camera, x, y, heading, length, rgba, dash: float = 300.0) -> None:
    run = 0.0
    while run < length:
        ax, ay = project(x, y, heading, run)
        bx, by = project(x, y, heading, min(length, run + dash))
        sax, say = cam.to_screen(ax, ay)
        sbx, sby = cam.to_screen(bx, by)
        rl.draw_line_ex(rl.Vector2(sax, say), rl.Vector2(sbx, sby), 1.0, _color(rl, rgba))
        run += 2 * dash


def _draw_torpedo(rl, cam: Camera, torp) -> None:
    sx, sy = cam.to_screen(torp.x, torp.y)
    ox, oy = cam.to_screen(torp.start_x, torp.start_y)
    rl.draw_line_ex(rl.Vector2(ox, oy), rl.Vector2(sx, sy), 1.0, _color(rl, TRACK))
    rl.draw_circle_v(rl.Vector2(sx, sy), 2.5, _color(rl, TORPEDO))


def _draw_fire_control(rl, cam: Camera, game: Game) -> None:
    sub = game.world.player
    if not sub.can_fire:
        return
    bx, by = project(sub.x, sub.y, sub.heading, sub.params.length / 2)
    ex, ey = project(bx, by, sub.heading, sub.tubes.params.max_run)
    sbx, sby = cam.to_screen(bx, by)
    sex, sey = cam.to_screen(ex, ey)
    rl.draw_line_ex(rl.Vector2(sbx, sby), rl.Vector2(sex, sey), 1.0, _color(rl, AIM))
    sol = game.solution()
    target = game.target()
    if sol is None or target is None:
        return
    ship = game.world.ship(target.ship_id)
    ok = abs(sol.error) <= ship.params.length / 2
    color = LEAD_OK if ok else LEAD_BAD
    cx, cy = cam.to_screen(sol.cross_x, sol.cross_y)
    rl.draw_circle_lines(int(cx), int(cy), 5.0, _color(rl, color))
    tx, ty = cam.to_screen(sol.target_x, sol.target_y)
    rl.draw_circle_v(rl.Vector2(tx, ty), 3.0, _color(rl, color))
    rl.draw_line_ex(rl.Vector2(cx, cy), rl.Vector2(tx, ty), 1.0, _color(rl, color))


def _draw_sub(rl, cam: Camera, game: Game) -> None:
    sub = game.world.player
    sx, sy = cam.to_screen(sub.x, sub.y)
    color = SUB_SURFACED if sub.surfaced else SUB_SUBMERGED
    radius = max(5.0, cam.px(sub.params.length) * 0.5)
    if sub.surfaced:
        rl.draw_circle_v(rl.Vector2(sx, sy), radius, _color(rl, color))
    else:
        rl.draw_circle_lines(int(sx), int(sy), radius, _color(rl, color))
    rad = math.radians(sub.heading)
    tip = rl.Vector2(sx + math.sin(rad) * radius * 2.2, sy - math.cos(rad) * radius * 2.2)
    rl.draw_line_ex(rl.Vector2(sx, sy), tip, 2.0, _color(rl, color))
    # How far a merchant's lookouts would see us right now: the bubble to keep ships out of.
    seen = max(
        (ship_detection_range(sub, s.type, game.world.light) for s in game.world.active_ships),
        default=0.0,
    )
    if seen > 0:
        rl.draw_circle_lines(int(sx), int(sy), cam.px(seen), _color(rl, BUBBLE))


def _draw_hud(rl, game: Game, width: int, height: int) -> None:
    world = game.world
    sub = world.player
    tubes = sub.tubes
    line1 = (
        f"HDG {sub.heading:05.1f}   SPD {sub.speed_knots:5.1f} kn   "
        f"THR {sub.throttle:+.2f}   RUD {sub.rudder:+.1f}"
    )
    line2 = (
        f"DEPTH {sub.depth:5.1f} m -> {sub.target_depth:5.1f} m   {sub.depth_band.upper()}"
        f"   BATT {sub.battery * 100:3.0f}%"
    )
    reload = (
        f" (reload {tubes.params.reload_time - tubes.reload_timer:3.0f}s)"
        if tubes.reloading
        else ""
    )
    line3 = (
        f"TUBES {tubes.loaded}/{tubes.params.tubes}  RES {tubes.reserves}{reload}   "
        f"TIME x{game.time_scale}   SUNK {world.tonnage:,} GRT"
    )
    rl.draw_text(line1, 10, 10, 20, _color(rl, HUD))
    rl.draw_text(line2, 10, 34, 20, _color(rl, HUD))
    rl.draw_text(line3, 10, 58, 20, _color(rl, HUD))

    _draw_contact_panel(rl, game, width)

    y = height - 26 - 18 * (len(game.messages) + 1)
    for t, text in game.messages:
        rl.draw_text(f"{t / 60:5.1f}m  {text}", 10, y, 16, _color(rl, HUD_DIM))
        y += 18
    rl.draw_text(
        "W/S thr  A/D rud  SPACE dive/surf  C deep  F fire  -/= zoom  1-4 time  R new",
        10,
        height - 26,
        16,
        _color(rl, HUD_DIM),
    )
    scale_px = int(1000.0 / game.zoom)
    rl.draw_line(10, height - 40, 10 + scale_px, height - 40, _color(rl, HUD_DIM))
    rl.draw_text("1 km", 14 + scale_px, height - 48, 16, _color(rl, HUD_DIM))

    tag = f"build {BUILD_ID}  seed {game.seed}  t={world.time:6.1f}s"
    tw = rl.measure_text(tag, 16)
    rl.draw_text(tag, width - tw - 10, height - 48, 16, _color(rl, HUD_DIM))

    mission = world.mission()
    if mission["status"] != "active":
        text = (
            f"MISSION OVER: {len(mission['sunk'])} sunk, {mission['tonnage']:,} GRT, "
            f"{len(mission['escaped'])} escaped   -   R for a new hunt"
        )
        tw = rl.measure_text(text, 20)
        rl.draw_text(text, (width - tw) // 2, height // 2 - 10, 20, _color(rl, HUD))


def _draw_contact_panel(rl, game: Game, width: int) -> None:
    world = game.world
    sub = world.player
    lines: list[tuple[str, tuple]] = []
    target = game.target()
    if target is not None and target.x is not None:
        ship = world.ship(target.ship_id)
        aob = angle_on_bow(target.heading or 0.0, bearing(target.x, target.y, sub.x, sub.y))
        side = "S" if aob >= 0 else "P"
        lines.append((f"TGT {target.ship_id}", HUD))
        lines.append((f"BRG {target.bearing:03.0f}  RNG {(target.range or 0) / 1000:4.1f} km", HUD))
        spd = (target.speed or 0.0) / 0.514444
        lines.append(
            (f"CRS {target.heading or 0:03.0f}  SPD {spd:4.1f} kn  AOB {abs(aob):3.0f}{side}", HUD)
        )
        if ship.alerted(world.time):
            lines.append(("RUNNING", ALERT))
        sol = game.solution()
        if sol is None:
            lines.append(("no solution: tracks do not cross in range", HUD_DIM))
        else:
            ok = abs(sol.error) <= ship.params.length / 2
            when = "FIRE" if ok else ("wait" if sol.error > 0 else "late")
            lead = f"lead {sol.error:+5.0f} m"
            text = f"run {sol.run / 1000:3.1f} km  {sol.time:3.0f} s  {lead}  {when}"
            lines.append((text, LEAD_OK if ok else HUD_DIM))
    else:
        hydro = [c for c in world.contacts if c.method == HYDROPHONE]
        if hydro:
            lines.append((f"hydrophone: {len(hydro)} contact(s)", HYDRO))
            for c in hydro[:3]:
                lines.append((f"  {c.ship_id} bearing {c.bearing:03.0f}", HYDRO))
        else:
            lines.append(("no contact", HUD_DIM))
    y = 10
    for text, color in lines:
        tw = rl.measure_text(text, 18)
        rl.draw_text(text, width - tw - 10, y, 18, _color(rl, color))
        y += 22
