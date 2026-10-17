"""render.draw must run against the pyray API in every game state (no window needed: a stub
records the calls, so typos in attribute names or bad arithmetic show up here, not in CI)."""

from jenesboat_v2 import render
from jenesboat_v2.game import Controls, Game
from jenesboat_v2.sim import default_world
from jenesboat_v2.sim.params import TYPE_VIIC

# Positional argument counts of the pyray functions the renderer is allowed to use.  These
# signatures are the same in raylib 5 (the browser wheel) and 6 (native); anything else
# (e.g. draw_circle_gradient, which changed between the two) must not be called.
PYRAY_ARITY = {
    "begin_drawing": 0,
    "end_drawing": 0,
    "clear_background": 1,
    "draw_line": 5,
    "draw_line_ex": 4,
    "draw_pixel": 3,
    "draw_circle_v": 3,
    "draw_circle_lines": 4,
    "draw_rectangle_pro": 4,
    "draw_rectangle_lines": 5,
    "draw_rectangle": 5,
    "draw_text": 5,
}


class FakeRL:
    def __init__(self):
        self.calls: list[str] = []

    def Color(self, *rgba):  # noqa: N802 - mirrors pyray
        assert len(rgba) == 4 and all(0 <= c <= 255 for c in rgba)
        return rgba

    def Vector2(self, x, y):  # noqa: N802
        return (float(x), float(y))

    def Rectangle(self, x, y, w, h):  # noqa: N802
        return (float(x), float(y), float(w), float(h))

    def measure_text(self, text, size):
        return len(text) * size // 2

    def __getattr__(self, name):
        if name in PYRAY_ARITY:

            def record(*args):
                assert len(args) == PYRAY_ARITY[name], f"{name} called with {len(args)} args"
                self.calls.append(name)

            return record
        raise AttributeError(f"{name}: not in the allowed pyray call table")


def draw(game: Game, legend: bool = False) -> list[str]:
    """Render once and return the pyray calls; the legend is off unless asked for, so tests
    can count map symbols."""
    game.show_legend = legend
    rl = FakeRL()
    render.draw(rl, game, 960, 540)
    assert rl.calls[0] == "begin_drawing" and rl.calls[-1] == "end_drawing"
    return rl.calls


def test_draws_a_fresh_hunt_with_no_contacts():
    calls = draw(Game(seed=1, state_interval=float("inf")))
    assert "draw_circle_v" in calls  # the surfaced boat
    assert "draw_rectangle_pro" not in calls  # nothing in sight


def test_draws_contacts_track_fire_control_and_torpedoes():
    game = Game(world=default_world(), state_interval=float("inf"))
    game.update(0.1)
    game.apply(Controls(fire=True), 0.1)
    game.update(0.1)
    calls = draw(game)
    assert calls.count("draw_rectangle_pro") == 3  # three freighters in sight
    assert "draw_circle_lines" in calls  # the crossing marker / visibility bubble


def test_draws_hydrophone_bearings_wrecks_and_mission_over():
    game = Game(world=default_world(), state_interval=float("inf"))
    sub = game.world.player
    sub.depth = sub.target_depth = TYPE_VIIC.deep_depth
    for ship in game.world.ships[:2]:
        ship.sunk = True
    game.world.ships[2].escaped = True
    game.update(0.1)
    assert game.world.mission()["status"] == "complete"
    calls = draw(game)
    assert "draw_line_ex" in calls
    assert "draw_text" in calls


def test_every_zoom_level_draws():
    game = Game(seed=2, state_interval=float("inf"))
    for _ in range(6):
        game.apply(Controls(zoom_in=True), 0.1)
        draw(game)
    for _ in range(6):
        game.apply(Controls(zoom_out=True), 0.1)
        draw(game)


def test_draws_the_intel_cue_on_and_off_screen_and_the_last_seen_cue():
    game = Game(seed=1, state_interval=float("inf"))
    off = draw(game)  # the 14 km intel marker is off-screen at 20 m/px: an edge arrow
    assert "draw_text" in off
    intel = game.world.intel
    game.world.player.x, game.world.player.y = intel["x"] + 500.0, intel["y"]
    on = draw(game)
    assert "draw_text" in on and "draw_line_ex" in on  # dashed circle, course tick, label
    contact = Game(world=default_world(), state_interval=float("inf"))
    contact.update(0.1)
    contact.world.player.depth = contact.world.player.target_depth = TYPE_VIIC.deep_depth
    contact.world.player.speed = 6.0 * 0.514444  # deep and noisy: no sensor holds them
    contact.update(0.1)
    assert contact.world.cue()["kind"] == "last_seen"
    draw(contact)


def test_close_zoom_draws_the_minor_grid_and_the_own_track():
    game = Game(world=default_world(), state_interval=float("inf"))
    game.world.player.set_throttle(1.0)
    for _ in range(600):
        game.update(0.1)
    far = draw(game)
    for _ in range(3):
        game.apply(Controls(zoom_in=True), 0.1)
    near = draw(game)
    assert near.count("draw_line") >= 15  # 200 m grid lines across a 1.9 x 1.1 km view
    assert "draw_pixel" in near and "draw_pixel" in far  # the boat's own track


def test_draws_sonar_ghosts_and_the_sonar_target_panel():
    game = Game(world=default_world(), state_interval=float("inf"))
    game.world.player.depth = game.world.player.target_depth = TYPE_VIIC.deep_depth
    game.update(0.1)
    assert game.target().method == "hydrophone"
    calls = draw(game)
    assert calls.count("draw_rectangle_pro") == 3  # ghost hulls at the estimated positions


def test_legend_is_on_by_default_and_l_toggles_it():
    game = Game(seed=1, state_interval=float("inf"))
    assert game.show_legend
    with_legend = draw(game, legend=True)
    assert "draw_rectangle" in with_legend  # the legend background
    game.apply(Controls(legend=True), 0.1)
    assert not game.show_legend
    without = draw(game, legend=game.show_legend)
    assert "draw_rectangle" not in without
    assert with_legend.count("draw_text") > without.count("draw_text")
    game.apply(Controls(legend=True), 0.1)
    assert game.show_legend


def test_paused_banner():
    game = Game(seed=1, state_interval=float("inf"))
    game.apply(Controls(pause=True), 0.1)
    assert "draw_text" in draw(game)


def test_every_contact_gets_a_projected_course_and_the_target_a_ring():
    game = Game(world=default_world(), state_interval=float("inf"))
    game.update(0.1)
    calls = draw(game)
    assert calls.count("draw_rectangle_pro") == 3
    assert calls.count("draw_circle_lines") >= 2  # target ring + lookout circle


def test_draws_escort_depth_charges_damage_and_the_destroyer_legend():
    from jenesboat_v2.sim.weapons import DepthCharge

    game = Game(seed=3, state_interval=float("inf"))
    sub = game.world.player
    game.world.depth_charges.append(DepthCharge(1, sub.x + 200.0, sub.y, 40.0))
    sub.damage = 0.4
    game.world.bonus = 1_800
    plain = draw(game)
    assert plain.count("draw_circle_v") >= 2  # the boat and the sinking charge
    assert len(draw(game, legend=True)) > len(plain)


def test_restart_prompt_is_drawn():
    game = Game(seed=1, state_interval=float("inf"))
    base = draw(game)
    game.apply(Controls(restart=True), 0.1)
    assert len(draw(game)) > len(base) - 1 and "draw_rectangle" in draw(game)
