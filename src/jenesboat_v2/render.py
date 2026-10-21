"""raylib drawing.  Only this module and ``app`` touch pyray, so the sim stays testable.

The camera follows the boat.  Only what the boat knows is drawn: visual contacts as hull
boxes, hydrophone contacts as bearing lines, wrecks, running torpedoes, and the fire-control
helper (aiming line, crossing point and lead marker) for the selected target.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from jenesboat_v2._build_info import BUILD_ID
from jenesboat_v2.game import Game
from jenesboat_v2.sim.detection import HYDROPHONE, ship_detection_range
from jenesboat_v2.sim.geo import angle_on_bow, bearing, project
from jenesboat_v2.sim.scenario import INTEL_POSITION_ERROR

OCEAN = (12, 32, 60, 255)
GRID = (26, 60, 102, 255)
GRID_MINOR = (18, 44, 78, 255)
GRID_LABEL = (80, 112, 156, 255)
OWN_TRACK = (90, 110, 140, 255)
CUE = (230, 190, 110, 255)
CUE_BLUR = (230, 190, 110, 22)  # one layer; the blur is several of these stacked
BLUR_LAYERS = 6
EDGE = (60, 90, 130, 255)
HULL_MERCHANT = (200, 200, 200, 255)
HULL_SONAR = (120, 200, 160, 110)  # a ghost: position from the hydrophones, not seen
HULL_MILITARY = (240, 120, 90, 255)
WRECK = (110, 110, 120, 255)
SUB_SURFACED = (255, 230, 120, 255)
SUB_SUBMERGED = (140, 170, 210, 255)
WAKE = (90, 130, 170, 255)
TRACK = (120, 150, 190, 255)
TRACK_DIM = (70, 90, 120, 255)  # projected course of a contact that is not the target
HYDRO = (120, 200, 160, 255)
DEPTH_CHARGE = (255, 170, 60, 255)
TORPEDO = (255, 255, 255, 255)
AIM = (200, 180, 90, 160)
LEAD_OK = (120, 240, 120, 255)
LEAD_BAD = (240, 150, 90, 255)
BUBBLE = (200, 90, 90, 110)
HUD = (230, 230, 230, 255)
HUD_DIM = (150, 160, 170, 255)
ALERT = (255, 120, 90, 255)
PANEL_BG = (6, 18, 36, 200)

TRACK_LENGTH = 12_000.0  # m of projected track drawn ahead of the target
HUD_TOP = 104  # px reserved for the HUD text at the top
PANEL_BOTTOM = 150  # px, below the contact panel on the right
EDGE_MARGIN = 28  # px, where off-screen cue arrows sit
MINOR_GRID_MAX_ZOOM = 5.0  # m/px; closer than this a 200 m grid is drawn too


def _color(rl, rgba):
    return rl.Color(*rgba)


@dataclass(frozen=True)
class Pad:
    """Touch controls are on screen: the lower part of the left and right edges is covered
    by button clusters this wide (logical px), so the message log, scale bar and build tag
    go between them, the keyboard help line goes, and the legend sits in the middle."""

    left: float = 0.0
    right: float = 0.0


class Camera:
    def __init__(self, cx: float, cy: float, zoom: float, width: int, height: int) -> None:
        self.cx, self.cy, self.zoom, self.width, self.height = cx, cy, zoom, width, height

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return self.width / 2 + (x - self.cx) / self.zoom, self.height / 2 - (
            y - self.cy
        ) / self.zoom

    def px(self, metres: float) -> float:
        return metres / self.zoom


def draw(rl, game: Game, width: int, height: int, pad: Pad | None = None) -> None:
    """One frame in ``width`` x ``height`` logical px; ``pad`` when touch buttons are up."""
    world = game.world
    sub = world.player
    cam = Camera(sub.x, sub.y, game.zoom, width, height)

    rl.begin_drawing()
    rl.clear_background(_color(rl, OCEAN))
    _draw_grid(rl, cam, world.width, world.height)
    _draw_own_track(rl, cam, world.player_track, sub.x, sub.y)
    _draw_cue(rl, cam, world.cue())

    for ship in world.ships:
        if ship.sunk:
            _draw_wreck(rl, cam, ship.x, ship.y)
    target = game.target()
    for contact in world.contacts:
        if contact.x is None or contact.y is None:
            continue
        ship = world.ship(contact.ship_id)
        if contact.method == HYDROPHONE:
            # Confirmed on the hydrophones: the bearing line and a ghost of the ship.
            _draw_bearing_line(rl, cam, sub.x, sub.y, contact.bearing)
            color = HULL_SONAR
        else:
            color = HULL_MILITARY if ship.kind == "military" else HULL_MERCHANT
        selected = target is not None and contact.ship_id == target.ship_id
        _draw_dashed(
            rl, cam, ship.x, ship.y, ship.heading, TRACK_LENGTH, TRACK if selected else TRACK_DIM
        )
        _draw_hull(rl, cam, ship.x, ship.y, ship.heading, ship.speed, ship.params, color)
        if selected:
            sx, sy = cam.to_screen(ship.x, ship.y)
            rl.draw_circle_lines(
                int(sx), int(sy), max(10.0, cam.px(ship.params.length)), _color(rl, HUD)
            )

    for torp in world.torpedoes:
        _draw_torpedo(rl, cam, torp)
    for charge in world.depth_charges:
        cx, cy = cam.to_screen(charge.x, charge.y)
        rl.draw_circle_v(rl.Vector2(cx, cy), 3.0, _color(rl, DEPTH_CHARGE))

    _draw_fire_control(rl, cam, game)
    _draw_sub(rl, cam, game)
    _draw_hud(rl, game, width, height, pad)
    if game.show_legend:
        _draw_legend(rl, width, height, pad)
    rl.end_drawing()


def _draw_grid(rl, cam: Camera, world_w: float, world_h: float) -> None:
    """World-fixed grid: 1 km lines labelled with their km coordinate (so the map is seen
    to scroll under the boat even at slow speeds), plus 200 m lines when zoomed in."""
    if cam.zoom <= MINOR_GRID_MAX_ZOOM:
        _grid_lines(rl, cam, 200.0, GRID_MINOR, label=False)
    _grid_lines(rl, cam, 1000.0, GRID, label=True)
    # The edge of the map.
    ax, ay = cam.to_screen(0.0, world_h)
    bx, by = cam.to_screen(world_w, 0.0)
    rl.draw_rectangle_lines(int(ax), int(ay), int(bx - ax), int(by - ay), _color(rl, EDGE))


def _grid_lines(rl, cam: Camera, step: float, rgba, label: bool) -> None:
    x0 = math.floor((cam.cx - cam.width / 2 * cam.zoom) / step) * step
    x1 = cam.cx + cam.width / 2 * cam.zoom
    gx = x0
    while gx <= x1:
        sx, _ = cam.to_screen(gx, 0.0)
        rl.draw_line(int(sx), 0, int(sx), cam.height, _color(rl, rgba))
        if label:
            km = f"{gx / 1000:.0f}"
            rl.draw_text(km, int(sx) + 3, HUD_TOP, 12, _color(rl, GRID_LABEL))
        gx += step
    y0 = math.floor((cam.cy - cam.height / 2 * cam.zoom) / step) * step
    y1 = cam.cy + cam.height / 2 * cam.zoom
    gy = y0
    while gy <= y1:
        _, sy = cam.to_screen(0.0, gy)
        rl.draw_line(0, int(sy), cam.width, int(sy), _color(rl, rgba))
        if label and PANEL_BOTTOM < sy < cam.height - 70:
            km = f"{gy / 1000:.0f}"
            tw = rl.measure_text(km, 12)
            rl.draw_text(km, cam.width - tw - 3, int(sy) - 14, 12, _color(rl, GRID_LABEL))
        gy += step


def _draw_own_track(rl, cam: Camera, track: list[tuple[float, float]], x: float, y: float) -> None:
    """Dots where the boat has been: the clearest sign it is moving."""
    for px, py in track[-400:]:
        sx, sy = cam.to_screen(px, py)
        if 0 <= sx <= cam.width and 0 <= sy <= cam.height:
            rl.draw_pixel(int(sx), int(sy), _color(rl, OWN_TRACK))
    if track:
        ax, ay = cam.to_screen(*track[-1])
        bx, by = cam.to_screen(x, y)
        rl.draw_line_ex(rl.Vector2(ax, ay), rl.Vector2(bx, by), 1.0, _color(rl, OWN_TRACK))


def _draw_cue(rl, cam: Camera, cue: dict | None) -> None:
    """Where the enemy probably is while nothing is held on the sensors: a blurred circle
    (its size is the uncertainty) with a course tick when on screen, otherwise an arrow at
    the edge of the map area pointing the way."""
    if cue is None:
        return
    label = "INTEL" if cue["kind"] == "intel" else f"LAST SEEN {cue['ship']}"
    text = f"{label}  {cue['bearing']:03.0f}  {cue['range'] / 1000:.1f} km"
    radius_m = INTEL_POSITION_ERROR if cue["kind"] == "intel" else 1_000.0
    sx, sy = cam.to_screen(cue["x"], cue["y"])
    on_screen = 0 <= sx <= cam.width and HUD_TOP <= sy <= cam.height - 70
    if on_screen:
        radius = max(16.0, cam.px(radius_m))
        _draw_blur(rl, sx, sy, radius, CUE_BLUR)
        tx, ty = project(cue["x"], cue["y"], cue["course"], radius_m * 1.5)
        stx, sty = cam.to_screen(tx, ty)
        rl.draw_line_ex(rl.Vector2(sx, sy), rl.Vector2(stx, sty), 1.0, _color(rl, CUE))
        rl.draw_text(text, int(sx) + 8, int(sy) + 8, 14, _color(rl, CUE))
        return
    # Off-screen: an arrow on the edge of the map area, pointing the way.
    dx, dy = sx - cam.width / 2, sy - cam.height / 2
    norm = math.hypot(dx, dy) or 1.0
    ux, uy = dx / norm, dy / norm
    half_w = cam.width / 2 - EDGE_MARGIN
    half_h = (cam.height - HUD_TOP - 70) / 2 - EDGE_MARGIN
    mid_y = HUD_TOP + (cam.height - HUD_TOP - 70) / 2
    k = min(half_w / abs(ux) if ux else math.inf, half_h / abs(uy) if uy else math.inf)
    ex, ey = cam.width / 2 + ux * k, mid_y + uy * k
    tip = rl.Vector2(ex + ux * 12, ey + uy * 12)
    left = rl.Vector2(ex - uy * 7, ey + ux * 7)
    right = rl.Vector2(ex + uy * 7, ey - ux * 7)
    rl.draw_line_ex(left, tip, 2.0, _color(rl, CUE))
    rl.draw_line_ex(right, tip, 2.0, _color(rl, CUE))
    rl.draw_line_ex(left, right, 2.0, _color(rl, CUE))
    tw = rl.measure_text(text, 14)
    lx = min(max(int(ex) - tw // 2, 4), cam.width - tw - 4)
    ly = int(ey) + (14 if uy < 0 else -30)
    rl.draw_text(text, lx, ly, 14, _color(rl, CUE))


def _draw_blur(rl, sx: float, sy: float, radius: float, rgba) -> None:
    """A soft disc: translucent circles stacked from the full radius inward, so the centre
    is brightest and the edge fades out (draw_circle_gradient differs between raylib 5 and
    6, so it is avoided)."""
    for i in range(BLUR_LAYERS):
        r = radius * (1.0 - i / BLUR_LAYERS)
        rl.draw_circle_v(rl.Vector2(sx, sy), r, _color(rl, rgba))


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


def _draw_hud(rl, game: Game, width: int, height: int, pad: Pad | None) -> None:
    world = game.world
    sub = world.player
    tubes = sub.tubes
    line1 = (
        f"HDG {sub.heading:05.1f}   SPD {sub.speed_knots:5.1f} kn   "
        f"{sub.telegraph_label}   {sub.rudder_label}"
    )
    line1b = (
        f"POS {sub.x / 1000:.2f}E {sub.y / 1000:.2f}N   LOG {world.player_log / 1852:.2f} nm   "
        f"SUNK {world.tonnage:,} GRT"
        + (f" (+{world.bonus:,} escort)" if world.bonus else "")
        + (f"   HULL DAMAGE {sub.damage * 100:.0f}%" if sub.damage > 0 else "")
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
    mission = world.mission()
    line3 = (
        f"TUBES {tubes.loaded}/{tubes.params.tubes}  RES {tubes.reserves}{reload}   "
        f"TIME {'PAUSED' if game.paused else f'x{game.time_scale}'}   "
        f"HUNT {len(mission['sunk'])}/{mission['total']} sunk, {len(mission['escaped'])} away"
    )
    rl.draw_text(line1, 10, 10, 20, _color(rl, HUD))
    rl.draw_text(line2, 10, 34, 20, _color(rl, HUD))
    rl.draw_text(line3, 10, 58, 20, _color(rl, HUD))
    rl.draw_text(line1b, 10, 82, 16, _color(rl, HUD_DIM))

    _draw_contact_panel(rl, game, width)

    # The bottom band: messages above the scale bar and build tag.  With touch buttons up
    # it sits between the two clusters and there is no keyboard help line.
    left = 10 if pad is None else int(pad.left) + 10
    right = width - 10 if pad is None else width - int(pad.right) - 10
    bottom = height - 26 if pad is None else height - 8
    text_right = right - LEGEND_WIDTH - 10 if pad is None and game.show_legend else right
    rows = [
        _wrap(rl, f"{t / 60:5.1f}m  {text}", 16, text_right - left) for t, text in game.messages
    ]
    y = bottom - 18 * (sum(len(lines) for lines in rows) + 1)
    for lines in rows:
        for i, line in enumerate(lines):
            rl.draw_text(line, left + (0 if i == 0 else 56), y, 16, _color(rl, HUD_DIM))
            y += 18
    if pad is None:
        help_line = (
            "W/S telegraph  A/D rudder  Q midships  SPACE dive  C deep  F fire  T target  "
            "-/= zoom  1-6 time  P pause  L legend"
        )
        rl.draw_text(help_line, left, bottom, 16, _color(rl, HUD_DIM))
    scale_px = int(1000.0 / game.zoom)
    rl.draw_line(left, bottom - 14, left + scale_px, bottom - 14, _color(rl, HUD_DIM))
    rl.draw_text("1 km", left + 4 + scale_px, bottom - 22, 16, _color(rl, HUD_DIM))

    tag = f"build {BUILD_ID}  seed {game.seed}  {game.difficulty.title}  t={world.time:6.1f}s"
    tw = rl.measure_text(tag, 16)
    rl.draw_text(tag, right - tw, bottom - 22, 16, _color(rl, HUD_DIM))

    touch = pad is not None
    if game.confirming_restart:
        answer = "YES / NO" if touch else "Y / R: yes    N: no"
        text = f"Abandon this hunt and start a new one?   {answer}"
        tw = rl.measure_text(text, 24)
        rl.draw_rectangle(
            (width - tw) // 2 - 12, height // 2 - 52, tw + 24, 40, _color(rl, PANEL_BG)
        )
        rl.draw_text(text, (width - tw) // 2, height // 2 - 44, 24, _color(rl, ALERT))
    elif game.paused:
        text = "PAUSED  -  RUN to resume" if touch else "PAUSED  -  P to resume"
        tw = rl.measure_text(text, 24)
        rl.draw_text(text, (width - tw) // 2, height // 2 - 40, 24, _color(rl, HUD))
    if mission["status"] != "active":
        again = "NEW for a new hunt" if touch else "R for a new hunt"
        text = (
            f"HUNT OVER ({mission['reason']}): {len(mission['sunk'])} sunk, "
            f"{mission['tonnage']:,} GRT, {len(mission['escaped'])} got away   -   {again}"
        )
        tw = rl.measure_text(text, 20)
        rl.draw_text(text, (width - tw) // 2, height // 2 - 10, 20, _color(rl, HUD))


def _wrap(rl, text: str, size: int, max_width: float) -> list[str]:
    """Break ``text`` at spaces into lines no wider than ``max_width`` px."""
    lines: list[str] = []
    line = ""
    for word in text.split(" "):
        trial = f"{line} {word}" if line else word
        if line and rl.measure_text(trial, size) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


# (swatch kind, colour, text) rows of the legend; swatch kinds are drawn by _draw_swatch.
LEGEND = (
    ("dot", SUB_SURFACED, "you, surfaced (outline: submerged)"),
    ("ring", BUBBLE, "how far lookouts can see you"),
    ("dots", OWN_TRACK, "your track"),
    ("box", HULL_MERCHANT, "ship in sight (grey X: wreck)"),
    ("box", HULL_SONAR, "ship heard on the hydrophones (estimate)"),
    ("dash", HYDRO, "hydrophone bearing"),
    ("dash", TRACK, "contact's course, projected (bright + ring: target, T)"),
    ("line", AIM, "torpedo track if fired now"),
    ("ring", LEAD_BAD, "where it crosses the target's course"),
    ("dot", LEAD_BAD, "target when the torpedo gets there"),
    ("line", LEAD_BAD, "miss distance: green = fire"),
    ("dot", TORPEDO, "torpedo running"),
    ("box", HULL_MILITARY, "destroyer: sonar, depth charges (sink one for a bonus)"),
    ("dot", DEPTH_CHARGE, "depth charge sinking"),
    ("blur", CUE, "intel / last seen (arrow when off screen)"),
)
LEGEND_WIDTH = 420  # fits the longest row at 14 px
LEGEND_ROW = 18


def _draw_legend(rl, width: int, height: int, pad: Pad | None) -> None:
    """Symbol key in the lower right, above the build tag (L toggles it).  With touch
    buttons up it is centred instead, where no button covers it."""
    rows = len(LEGEND)
    panel_h = LEGEND_ROW * (rows + 1) + 10
    if pad is None:
        x0 = width - LEGEND_WIDTH - 10
        y0 = height - 56 - panel_h
        title = "LEGEND  (L to hide)"
    else:
        x0 = (width - LEGEND_WIDTH) // 2
        y0 = max(HUD_TOP, (height - panel_h) // 2)
        title = "LEGEND  (? to hide)"
    rl.draw_rectangle(x0, y0, LEGEND_WIDTH, panel_h, _color(rl, PANEL_BG))
    rl.draw_text(title, x0 + 8, y0 + 6, 14, _color(rl, HUD))
    y = y0 + 6 + LEGEND_ROW
    for kind, rgba, text in LEGEND:
        _draw_swatch(rl, kind, x0 + 20, y + 7, rgba)
        rl.draw_text(text, x0 + 40, y, 14, _color(rl, HUD_DIM))
        y += LEGEND_ROW


def _draw_swatch(rl, kind: str, cx: float, cy: float, rgba) -> None:
    color = _color(rl, rgba)
    if kind == "dot":
        rl.draw_circle_v(rl.Vector2(cx, cy), 4.0, color)
    elif kind == "ring":
        rl.draw_circle_lines(int(cx), int(cy), 6.0, color)
    elif kind == "box":
        rl.draw_rectangle_pro(rl.Rectangle(cx, cy, 16.0, 6.0), rl.Vector2(8.0, 3.0), 0.0, color)
    elif kind == "line":
        rl.draw_line_ex(rl.Vector2(cx - 10, cy), rl.Vector2(cx + 10, cy), 1.5, color)
    elif kind == "dash":
        for dx in (-10, -2, 6):
            rl.draw_line_ex(rl.Vector2(cx + dx, cy), rl.Vector2(cx + dx + 4, cy), 1.0, color)
    elif kind == "dots":
        for dx in (-9, -5, -1, 3, 7):
            rl.draw_pixel(int(cx + dx), int(cy), color)
    elif kind == "blur":
        _draw_blur(rl, cx, cy, 8.0, CUE_BLUR)


def _draw_contact_panel(rl, game: Game, width: int) -> None:
    world = game.world
    sub = world.player
    lines: list[tuple[str, tuple]] = []
    target = game.target()
    if target is not None and target.x is not None:
        ship = world.ship(target.ship_id)
        aob = angle_on_bow(target.heading or 0.0, bearing(target.x, target.y, sub.x, sub.y))
        side = "S" if aob >= 0 else "P"
        sonar = target.method == HYDROPHONE
        label = f"{'SONAR' if sonar else 'TGT'} {target.ship_id}"
        if game.selected == target.ship_id:
            label += " (T)"
        lines.append((label, HYDRO if sonar else HUD))
        lines.append((f"BRG {target.bearing:03.0f}  RNG {(target.range or 0) / 1000:4.1f} km", HUD))
        spd = (target.speed or 0.0) / 0.514444
        lines.append(
            (f"CRS {target.heading or 0:03.0f}  SPD {spd:4.1f} kn  AOB {abs(aob):3.0f}{side}", HUD)
        )
        if ship.alerted(world.time):
            lines.append(("RUNNING", ALERT))
        sol = game.solution()
        if sonar:
            lines.append(("sonar estimate: periscope needed to shoot", HUD_DIM))
        elif sol is None:
            lines.append(("no solution: tracks do not cross in range", HUD_DIM))
        else:
            ok = abs(sol.error) <= ship.params.length / 2
            glancing = sol.track_angle < world.rules.torpedo_hit.glance_angle
            when = (
                "GLANCE"
                if ok and glancing
                else "FIRE"
                if ok
                else "wait"
                if sol.error > 0
                else "late"
            )
            lead = f"lead {sol.error:+5.0f} m"
            text = (
                f"run {sol.run / 1000:3.1f} km  {sol.time:3.0f} s  {lead}  "
                f"trk {sol.track_angle:2.0f}  {when}"
            )
            color = LEAD_BAD if ok and glancing else LEAD_OK if ok else HUD_DIM
            lines.append((text, color))
        others = [c for c in game.contacts_by_range() if c.ship_id != target.ship_id]
        for c in others[:4]:
            how = "sonar" if c.method == HYDROPHONE else "seen"
            text = f"{c.ship_id}  {c.bearing:03.0f}  {(c.range or 0) / 1000:4.1f} km  {how}"
            lines.append((text, HYDRO if c.method == HYDROPHONE else HUD_DIM))
        if others:
            lines.append(("T: next target", HUD_DIM))
    else:
        lines.append(("no contact", HUD_DIM))
        cue = world.cue()
        if cue is not None:
            what = "intel" if cue["kind"] == "intel" else f"last seen {cue['ship']}"
            lines.append(
                (f"{what}: bearing {cue['bearing']:03.0f}, {cue['range'] / 1000:.1f} km", CUE)
            )
            lines.append((f"  course ~{cue['course']:03.0f}", CUE))
    y = 10
    for text, color in lines:
        tw = rl.measure_text(text, 18)
        rl.draw_text(text, width - tw - 10, y, 18, _color(rl, color))
        y += 22
