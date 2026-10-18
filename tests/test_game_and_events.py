import json

import pytest

from jenesboat_v2 import events
from jenesboat_v2.game import TIME_SCALES, ZOOM_LEVELS, Controls, Game, describe
from jenesboat_v2.sim import default_world
from jenesboat_v2.sim.geo import angle_diff
from jenesboat_v2.sim.params import TELEGRAPH, TELEGRAPH_STOP


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


def test_telegraph_steps_and_rudder_holds(captured):
    game = Game(world=default_world(), state_interval=float("inf"))
    sub = game.world.player
    start = sub.heading
    assert sub.telegraph == TELEGRAPH_STOP and sub.telegraph_label == "STOP"
    game.apply(Controls(throttle_up=True), 0.1)
    assert sub.telegraph_label == "AHEAD SLOW" and sub.throttle == 0.25
    for _ in range(10):  # extra presses stop at the last position
        game.apply(Controls(throttle_up=True), 0.1)
    assert sub.telegraph_label == "AHEAD FLANK" and sub.throttle == 1.0
    for _ in range(20):
        game.apply(Controls(throttle_down=True), 0.1)
    assert sub.telegraph_label == TELEGRAPH[0][0] == "ASTERN FULL" and sub.throttle == -1.0
    for _ in range(6):
        game.apply(Controls(throttle_up=True), 0.1)
    assert sub.telegraph_label == "AHEAD FLANK"
    # The rudder ramps while D is held and stays put when it is released.
    for _ in range(10):
        game.apply(Controls(starboard=True), 0.1)
        game.update(0.1)
    assert sub.rudder == pytest.approx(0.5)
    assert sub.rudder_label in ("RUDDER 17 STBD", "RUDDER 18 STBD")  # 0.5 * 35 = 17.5
    for _ in range(30):
        game.apply(Controls(), 0.1)
        game.update(0.1)
    assert sub.rudder == pytest.approx(0.5)
    assert sub.speed > 0.0
    assert 0.0 < angle_diff(sub.heading, start) < 180.0
    game.apply(Controls(rudder_center=True), 0.1)
    assert sub.rudder == 0.0 and sub.rudder_label == "RUDDER AMIDSHIPS"
    for _ in range(30):
        game.apply(Controls(port=True), 0.1)
    assert sub.rudder == -1.0 and sub.rudder_label == "RUDDER 35 PORT"
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
    assert game.messages[0][1].startswith("Objective: sink the 3 merchants")
    assert game.messages[1][1].startswith("BdU:")
    game.apply(Controls(fire=True), 0.1)
    game.apply(Controls(restart=True), 0.1)
    assert game.restarts == 0 and game.confirming_restart  # asked first
    game.apply(Controls(confirm=True), 0.1)
    assert game.world is not first
    assert game.seed == 6 and game.restarts == 1
    assert game.world.player.tubes.loaded == 4
    assert [events.parse(line)["event"] for line in captured].count("restart") == 1
    assert [m[1][:9] for m in game.messages] == ["Objective", "BdU: 3 me"]


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
    sonar = game.target()  # deep and slow: the hydrophones still hold them
    assert sonar is not None and sonar.method == "hydrophone"
    assert game.solution() is None  # but there is no firing solution without the periscope
    game.world.player.speed = 6.0 * 0.514444  # too fast for the hydrophones
    game.update(0.1)
    assert game.target() is None


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
    end = {"sunk": ["a"], "escaped": [], "tonnage": 4500, "reason": "all merchants sunk"}
    assert describe("mission_end", end) == (
        "mission over (all merchants sunk): 1 sunk (4,500 GRT), 0 got away"
    )
    assert describe("state", {}) is None
    assert describe("escort_alarm", {"by": "destroyer-1", "reason": "sonar"}) == (
        "ESCORT: destroyer-1 pinged us"
    )
    assert "hunting" in describe("escort_split", {"hunters": ["d1"], "screens": ["d2"]})
    assert "back to formation" in describe("escort_stand_down", {})
    assert "depth charge run" in describe("depth_charge_run", {"ship": "d1", "charges": 20})
    assert describe("depth_charge", {"damage": 0.0}) is None
    assert describe("depth_charge", {"damage": 0.2}) == "DEPTH CHARGE close!"
    assert describe("damage", {"level": 0.37, "destroyed": False}) == "hull damage 37%"
    bonus = describe("sunk", {"ship": "d", "kind": "military", "tonnage": 1800})
    assert bonus == "d SUNK: escort bonus 1,800 GRT"


def test_snapshot_is_json_serialisable():
    json.dumps(Game(seed=1).snapshot())


def test_pause_freezes_the_world_but_not_the_view(captured):
    game = Game(seed=3, state_interval=1.0)
    game.update(0.5)
    t = game.world.time
    game.apply(Controls(pause=True), 0.1)
    assert game.paused
    assert events.parse(captured[-1]) == {"event": "pause", "paused": True, "t": 0.5}
    for _ in range(20):
        game.apply(Controls(zoom_in=True, throttle_up=True), 0.1)
        game.update(0.1)
    assert game.world.time == t  # nothing moved, no state events
    assert game.state_events == 0
    assert game.zoom < ZOOM_LEVELS[3] and game.world.player.telegraph_label == "AHEAD FLANK"
    assert game.snapshot()["paused"] is True
    game.apply(Controls(pause=True), 0.1)
    game.update(0.5)
    assert game.world.time == pytest.approx(t + 0.5)
    game.apply(Controls(pause=True), 0.1)
    game.apply(Controls(restart=True), 0.1)
    game.apply(Controls(confirm=True), 0.1)
    assert not game.paused  # a new hunt starts running


def test_target_selection_cycles_and_persists(captured):
    game = Game(world=default_world(), state_interval=float("inf"))
    game.update(0.1)
    ids = [c.ship_id for c in game.contacts_by_range()]
    assert ids[0] == "merchant-3" and len(ids) == 3  # nearest first
    assert game.target().ship_id == "merchant-3" and game.selected is None
    game.apply(Controls(next_target=True), 0.1)
    assert game.selected == ids[1] and game.target().ship_id == ids[1]
    game.apply(Controls(next_target=True), 0.1)
    game.apply(Controls(next_target=True), 0.1)
    assert game.target().ship_id == ids[0]  # wrapped around
    assert game.select_target("merchant-1") and game.target().ship_id == "merchant-1"
    for _ in range(50):
        game.update(0.1)
    assert game.target().ship_id == "merchant-1"  # sticks while held
    assert not game.select_target("nobody")
    game.world.ship("merchant-1").sunk = True
    game.update(0.1)
    assert game.target().ship_id == "merchant-3"  # lost: back to the nearest
    assert game.select_target(None) and game.selected is None
    game.world.player.depth = game.world.player.target_depth = 60.0
    game.world.player.speed = 6.0 * 0.514444
    game.update(0.1)
    assert game.next_target() is None and game.target() is None


def test_restart_asks_first_and_freezes_the_world(captured):
    game = Game(seed=5, state_interval=float("inf"))
    game.apply(Controls(restart=True), 0.1)
    t = game.world.time
    game.update(1.0)
    assert game.confirming_restart and game.world.time == t
    game.apply(Controls(throttle_up=True, fire=True), 0.1)  # other orders wait
    assert game.world.player.throttle == 0.0 and game.world.torpedoes == []
    game.apply(Controls(cancel=True), 0.1)
    assert not game.confirming_restart and game.restarts == 0 and game.seed == 5
    game.update(1.0)
    assert game.world.time > t
    game.apply(Controls(restart=True), 0.1)
    game.apply(Controls(restart=True), 0.1)  # R again confirms
    assert game.restarts == 1 and not game.confirming_restart


def test_restart_needs_no_confirmation_once_the_hunt_is_over(captured):
    game = Game(seed=5, state_interval=float("inf"))
    game.world.mission_over = True
    game.apply(Controls(restart=True), 0.1)
    assert game.restarts == 1


def test_events_go_to_the_js_console_only_when_there_is_one(capsys, monkeypatch):
    lines = []

    class Console:
        def log(self, line):
            lines.append(line)

    monkeypatch.setattr(events, "_js_console", Console())
    monkeypatch.setattr(events, "_js_console_resolved", True)
    events.emit("ping", n=1)
    assert lines == ['JENESBOAT {"event":"ping","n":1}']
    assert capsys.readouterr().out == ""  # not printed as well: pygbag echoes stdout there
