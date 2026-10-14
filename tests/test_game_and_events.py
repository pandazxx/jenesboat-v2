import json

import pytest

from jenesboat_v2 import events
from jenesboat_v2.game import TIME_SCALES, ZOOM_LEVELS, Controls, Game, describe
from jenesboat_v2.sim import default_world
from jenesboat_v2.sim.geo import angle_diff


@pytest.fixture
def captured():
    lines: list[str] = []
    events.set_sink(lines.append)
    yield lines
    events.set_sink(None)


def test_event_format_and_parse(captured):
    events.emit("ready", build="abc", n=1)
    assert captured == ['JENESBOAT {"build":"abc","event":"ready","n":1}']
    assert events.parse("noise " + captured[0]) == {"build": "abc", "event": "ready", "n": 1}
    assert events.parse("plain log line") is None
    assert events.parse("JENESBOAT not json") is None


def test_game_emits_state_at_interval(captured):
    game = Game(state_interval=1.0)
    for _ in range(25):
        game.update(0.1)
    states = [e for e in map(events.parse, captured) if e["event"] == "state"]
    assert len(states) == 2
    assert states[-1]["player"]["speed_kn"] == 0.0


def test_controls_ramp_throttle_and_steer(captured):
    game = Game(world=default_world(), state_interval=float("inf"))
    start = game.world.player.heading
    for _ in range(40):
        game.apply(Controls(throttle_up=True, starboard=True), 0.1)
        game.update(0.1)
    sub = game.world.player
    assert sub.throttle == 1.0
    assert sub.rudder == 1.0
    assert sub.speed > 0.0
    assert 0.0 < angle_diff(sub.heading, start) < 180.0
    game.apply(Controls(dive_toggle=True), 0.1)
    assert sub.target_depth > 0.0
    game.apply(Controls(deep=True), 0.1)
    assert sub.target_depth == sub.spec.deep_depth
    assert "state" not in [events.parse(line)["event"] for line in captured]


def test_fire_zoom_and_time_controls(captured):
    game = Game(seed=3, state_interval=float("inf"))
    assert game.zoom == ZOOM_LEVELS[game.zoom_index]
    game.apply(Controls(zoom_in=True), 0.1)
    assert game.zoom < ZOOM_LEVELS[3]
    for _ in range(10):
        game.apply(Controls(zoom_out=True), 0.1)
    assert game.zoom == ZOOM_LEVELS[-1]
    game.apply(Controls(time_scale=8), 0.1)
    assert game.time_scale == TIME_SCALES[-1]
    game.apply(Controls(time_scale=9), 0.1)  # not a known compression: ignored
    assert game.time_scale == TIME_SCALES[-1]
    game.apply(Controls(fire=True), 0.1)
    assert game.world.player.tubes.loaded == 3
    assert [events.parse(line)["event"] for line in captured][-1] == "fire"
    assert game.messages[-1][1].startswith("torpedo 1 away")


def test_time_compression_substeps_the_world(captured):
    game = Game(seed=3, state_interval=1.0)
    game.set_time_scale(4)
    game.update(0.5)  # 2 s of sim time in steps of <= 0.1 s
    assert game.world.time == pytest.approx(2.0)
    assert game.state_events == 1  # at most one state event per frame


def test_restart_makes_a_new_hunt(captured):
    game = Game(seed=5, state_interval=float("inf"))
    first = game.world
    assert game.messages[0][1].startswith("BdU:")
    game.apply(Controls(fire=True), 0.1)
    game.apply(Controls(restart=True), 0.1)
    assert game.world is not first
    assert game.seed == 6 and game.restarts == 1
    assert game.world.player.tubes.loaded == 4
    assert [events.parse(line)["event"] for line in captured].count("restart") == 1
    assert game.messages[-1][1].startswith("BdU:")


def test_target_and_solution_follow_the_nearest_visual_contact(captured):
    game = Game(world=default_world(), state_interval=float("inf"))
    game.update(0.1)
    target = game.target()
    assert target is not None and target.method == "visual"
    assert target.ship_id == "merchant-3"  # the eastern one is nearest the boat
    sol = game.solution()
    snap = game.snapshot()
    assert snap["target"] == "merchant-3"
    assert (snap["solution"] is None) == (sol is None)
    game.world.player.depth = game.world.player.target_depth = 60.0
    game.update(0.1)
    assert game.target() is None and game.solution() is None


def test_describe_covers_every_player_facing_event():
    assert "BdU" in describe("intel", {"ships": 3, "bearing": 45, "range": 14000.0, "course": 120})
    assert describe("contact", {"ship": "x", "method": "hydrophone", "bearing": 12.0}).endswith(
        "012"
    )
    assert (
        describe("alert", {"ships": ["a", "b"], "reason": "sighted"})
        == "a, b running: we were sighted"
    )
    assert describe("sunk", {"ship": "t", "tonnage": 9000, "total": 9000}) == "t SUNK, 9,000 GRT"
    assert describe("mission_end", {"sunk": ["a"], "escaped": [], "tonnage": 4500}).startswith(
        "mission over"
    )
    assert describe("state", {}) is None


def test_snapshot_is_json_serialisable():
    json.dumps(Game(seed=1).snapshot())
