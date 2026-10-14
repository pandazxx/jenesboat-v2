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
    assert main(["--headless", "--seconds", "30", "--script", script]) == 0
    evs = events_from(capsys.readouterr().out)
    kinds = [e["event"] for e in evs]
    assert kinds[0] == "ready"
    assert kinds.count("order") == 3
    assert kinds[-1] == "final"
    final = evs[-1]
    assert final["t"] == 30.0
    assert final["player"]["speed_kn"] > 5.0
    assert final["player"]["heading"] > 10.0
    assert final["player"]["depth"] > 0.0
    assert len(final["ships"]) == 4


def test_headless_trace_emits_states(capsys):
    assert main(["--headless", "--seconds", "3", "--trace"]) == 0
    kinds = [e["event"] for e in events_from(capsys.readouterr().out)]
    assert kinds.count("state") == 3
