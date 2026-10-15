import json

from jenesboat_v2 import main
from jenesboat_v2.events import parse


def events_from(out: str) -> list[dict]:
    return [ev for ev in (parse(line) for line in out.splitlines()) if ev]


def test_version(capsys):
    assert main(["--version"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("jenesboat-v2 ")
    assert "build dev" in out


def test_headless_script_moves_and_dives(capsys):
    script = json.dumps(
        [{"t": 0, "throttle": 1.0}, {"t": 5, "rudder": 1.0}, {"t": 8, "dive": True}]
    )
    assert main(["--headless", "--seconds", "30", "--seed", "7", "--script", script]) == 0
    evs = events_from(capsys.readouterr().out)
    kinds = [e["event"] for e in evs]
    assert kinds[0] == "ready"
    assert kinds[1] == "intel"
    assert kinds.count("order") == 3
    assert kinds[-1] == "final"
    final = evs[-1]
    assert final["t"] == 30.0
    assert final["seed"] == 7
    assert final["player"]["speed_kn"] > 5.0
    assert final["player"]["rudder"] == 1.0
    assert final["player"]["depth"] > 0.0
    assert len(final["ships"]) == 3


def test_headless_telegraph_order(capsys):
    script = json.dumps([{"t": 0, "telegraph": "ahead half"}])
    assert main(["--headless", "--seconds", "5", "--seed", "1", "--script", script]) == 0
    final = events_from(capsys.readouterr().out)[-1]
    assert final["player"]["throttle"] == 0.5
    assert final["player"]["telegraph"] == "AHEAD HALF"


def test_headless_fire_deep_and_time_scale_orders(capsys):
    script = json.dumps([{"t": 0, "fire": True}, {"t": 1, "deep": True}, {"t": 2, "time_scale": 4}])
    assert main(["--headless", "--seconds", "10", "--seed", "1", "--script", script]) == 0
    evs = events_from(capsys.readouterr().out)
    kinds = [e["event"] for e in evs]
    assert "fire" in kinds
    final = evs[-1]
    assert final["time_scale"] == 4
    assert final["t"] > 30.0  # 2 s at x1 then 8 s at x4
    assert final["player"]["target_depth"] == 60.0
    assert final["player"]["tubes"]["loaded"] == 3


def test_headless_trace_emits_states(capsys):
    assert main(["--headless", "--seconds", "3", "--trace"]) == 0
    kinds = [e["event"] for e in events_from(capsys.readouterr().out)]
    assert kinds.count("state") == 3
