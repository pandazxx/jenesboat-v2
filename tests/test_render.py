"""render.draw must run against the pyray API in every game state (no window needed: a stub
records the calls, so typos in attribute names or bad arithmetic show up here, not in CI)."""

from jenesboat_v2 import render
from jenesboat_v2.game import Controls, Game
from jenesboat_v2.sim import default_world
from jenesboat_v2.sim.params import TYPE_VIIC


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
        if name.startswith("draw_") or name in ("begin_drawing", "end_drawing", "clear_background"):

            def record(*args):
                self.calls.append(name)

            return record
        raise AttributeError(name)


def draw(game: Game) -> list[str]:
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
