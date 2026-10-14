import json

import pytest

from jenesboat_v2 import events
from jenesboat_v2.game import Controls, Game


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
    states = [events.parse(line) for line in captured]
    assert len(states) == 2
    assert states[-1]["event"] == "state"
    assert states[-1]["player"]["speed_kn"] == 0.0


def test_controls_ramp_throttle_and_steer(captured):
    game = Game(state_interval=float("inf"))
    for _ in range(40):
        game.apply(Controls(throttle_up=True, starboard=True), 0.1)
        game.update(0.1)
    sub = game.world.player
    assert sub.throttle == 1.0
    assert sub.rudder == 1.0
    assert sub.speed > 0.0
    assert 0.0 < sub.heading < 180.0
    game.apply(Controls(dive_toggle=True), 0.1)
    assert sub.target_depth > 0.0
    assert captured == []


def test_snapshot_is_json_serialisable():
    json.dumps(Game().snapshot())
