"""The difficulty framework: difficulties are data, strategies plug into slots, the world runs
on its difficulty's rules, and a hunt can be started at a chosen difficulty from every entry
point."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from jenesboat_v2 import app, events, main
from jenesboat_v2.game import Controls, Game
from jenesboat_v2.sim import difficulty, hunting_scenario
from jenesboat_v2.sim import params as P
from jenesboat_v2.sim.escort import HUNT, escort_station
from jenesboat_v2.sim.geo import distance, project
from jenesboat_v2.sim.world import World

TEMPLATE = Path(__file__).resolve().parents[1] / "web" / "noctx.tmpl"


@pytest.fixture
def captured():
    lines: list[str] = []
    events.set_sink(lines.append)
    yield lines
    events.set_sink(None)


def parsed(lines: list[str]) -> list[dict]:
    return [e for e in map(events.parse, lines) if e]


def run(world: World, seconds: float) -> list[dict]:
    seen: list[dict] = []
    for _ in range(int(seconds / 0.1)):
        world.step(0.1)
        seen.extend(world.events)
        world.events.clear()
    return seen


class FakeBridge:
    """A page with the given globals (strings and numbers)."""

    def __init__(self, **values):
        self.values = values

    def get(self, name):
        value = self.values.get(name)
        return None if isinstance(value, str) else value

    def text(self, name):
        value = self.values.get(name)
        return value if isinstance(value, str) else None

    def call(self, name, *args):
        pass


# --- levels and the registry ---------------------------------------------------------------


def test_levels_are_named_data_and_the_default_is_patrol():
    assert difficulty.DIFFICULTY_NAMES == ("cadet", "patrol", "veteran")
    assert difficulty.get().name == difficulty.DEFAULT_DIFFICULTY == "patrol"
    assert difficulty.get("veteran") is P.VETERAN
    for name, level in P.DIFFICULTIES.items():
        assert level.name == name and level.title and level.description
    with pytest.raises(KeyError, match="unknown difficulty 'ace'"):
        difficulty.get("ace")
    assert "patrol:" in difficulty.describe()


def test_every_level_names_registered_strategies():
    registry = difficulty.available()
    assert set(registry) == set(difficulty.SLOTS)
    assert set(registry) == {"escort_search", "escort_evade", "merchant_flee"}
    for level in P.DIFFICULTIES.values():
        difficulty.check(level)
        for slot in difficulty.SLOTS:
            assert getattr(level.strategies, slot) in registry[slot]
            fn = difficulty.pick(level, slot)
            assert fn.strategy == (slot, getattr(level.strategies, slot))


def test_a_level_with_an_unknown_strategy_is_rejected_when_checked():
    bad = replace(P.PATROL, name="bad", strategies=replace(P.Strategies(), escort_evade="jump"))
    with pytest.raises(LookupError, match="difficulty 'bad': no strategy 'jump' for slot"):
        difficulty.check(bad)
    with pytest.raises(LookupError):
        hunting_scenario(1, difficulty=bad)


def test_registering_needs_a_known_slot_and_a_free_name():
    with pytest.raises(KeyError, match="unknown strategy slot"):
        difficulty.strategy("escort_dance", "waltz")
    with pytest.raises(ValueError, match="registered twice"):
        difficulty.strategy("escort_evade", "none")(lambda world, ship, dt: False)


def test_patrol_is_the_base_sheet_and_the_other_levels_differ_in_the_documented_ways():
    base = P.PATROL.rules
    assert base == P.Rules()
    cadet, veteran = P.CADET.rules, P.VETERAN.rules
    assert cadet.scenario.escorts < base.scenario.escorts < veteran.scenario.escorts
    assert cadet.sonar.range < base.sonar.range < veteran.sonar.range
    assert cadet.escort_ai.lose_track_time < base.escort_ai.lose_track_time
    assert base.escort_ai.lose_track_time < veteran.escort_ai.lose_track_time
    assert cadet.depth_charge.damage < base.depth_charge.damage < veteran.depth_charge.damage
    assert cadet.torpedo.reload_time < base.torpedo.reload_time < veteran.torpedo.reload_time
    # Only those blocks: the boat, the merchants and the detection table are the same.
    for name in ("submarine", "detection", "merchant_ai"):
        assert getattr(cadet, name) == getattr(base, name) == getattr(veteran, name)


# --- the world runs on its level -----------------------------------------------------------


def test_the_scenario_follows_the_level():
    for name, escorts in (("cadet", 1), ("patrol", 2), ("veteran", 3)):
        world = hunting_scenario(7, difficulty=difficulty.get(name))
        destroyers = [s for s in world.ships if s.kind == "military"]
        assert world.difficulty.name == name and len(destroyers) == escorts
        assert (
            world.player.tubes.params.reload_time == P.DIFFICULTIES[name].rules.torpedo.reload_time
        )
        assert all(d.escort.charges == world.rules.depth_charge.magazine for d in destroyers)
        assert world.snapshot()["difficulty"] == name
    assert len([s for s in hunting_scenario(7, escorts=0).ships if s.kind == "military"]) == 0


def test_three_escorts_get_three_different_stations():
    stations = [escort_station(0.0, 0.0, 0.0, rank) for rank in range(4)]
    for a in stations:
        for b in stations:
            assert a is b or distance(*a, *b) >= P.ESCORT_AI.station_abeam - 1e-6
    assert all(y == pytest.approx(P.ESCORT_AI.station_ahead) for _x, y in stations)
    assert [round(x) for x, _y in stations] == [1500, -1500, 3000, -3000]


def test_a_world_built_by_hand_runs_on_the_default_level():
    world = World(width=100.0, height=100.0, player=hunting_scenario(1).player)
    assert world.difficulty is P.PATROL and world.rules is P.PATROL.rules


def test_the_level_changes_what_the_escort_hears_and_how_long_it_remembers():
    def hunt(chosen):
        """The boat submerged 1.2 km off the bow of destroyer-1, stopped."""
        world = hunting_scenario(4, difficulty=chosen)
        d = world.ship("destroyer-1")
        sub = world.player
        sub.x, sub.y = project(d.x, d.y, d.heading, 1_200.0)
        sub.depth = sub.target_depth = 30.0
        return world, run(world, 60)

    _, cadet_events = hunt(P.CADET)
    world, veteran_events = hunt(P.VETERAN)
    assert "escort_alarm" in [e["event"] for e in cadet_events]
    assert "escort_alarm" in [e["event"] for e in veteran_events]
    hunter = next(d for d in world.ships if d.kind == "military" and d.escort.mode == HUNT)
    assert hunter.escort.sonar_range > P.SONAR_ASDIC.range * P.SONAR_ASDIC.interference_floor
    # Veteran escorts keep hunting long after cadet ones would have given up.
    world.player.x, world.player.y = world.player.x - 15_000.0, world.player.y - 15_000.0
    run(world, P.CADET.rules.escort_ai.lose_track_time + 30)
    assert world.datum is not None
    run(world, P.VETERAN.rules.escort_ai.lose_track_time)
    assert world.datum is None


# --- starting a hunt at a chosen level -----------------------------------------------------


def test_game_starts_at_the_chosen_level_and_restarts_keep_it(captured):
    game = Game(seed=3, state_interval=float("inf"), difficulty="cadet")
    assert game.difficulty.name == "cadet" and game.world.difficulty is P.CADET
    assert game.messages[0][1].startswith("Objective (Cadet):")
    assert game.snapshot()["difficulty"] == "cadet"
    game.apply(Controls(restart=True), 0.1)
    game.apply(Controls(confirm=True), 0.1)
    assert game.world.difficulty is P.CADET and game.seed == 4
    restart = next(e for e in parsed(captured) if e["event"] == "restart")
    assert restart["difficulty"] == "cadet"
    assert Game(seed=1, state_interval=float("inf")).difficulty.name == "patrol"
    with pytest.raises(KeyError):
        Game(seed=1, difficulty="ace")


def test_headless_cli_takes_a_difficulty(capsys):
    assert main(["--headless", "--seconds", "1", "--seed", "1", "--difficulty", "veteran"]) == 0
    evs = parsed(capsys.readouterr().out.splitlines())
    assert evs[0]["event"] == "ready" and evs[0]["difficulty"] == "veteran"
    final = evs[-1]
    assert final["difficulty"] == "veteran"
    assert sum(s["kind"] == "military" for s in final["ships"]) == 3
    assert main(["--headless", "--seconds", "1", "--seed", "1"]) == 0
    assert parsed(capsys.readouterr().out.splitlines())[-1]["difficulty"] == "patrol"
    with pytest.raises(SystemExit):
        main(["--headless", "--difficulty", "ace"])


def test_the_web_page_hands_the_url_level_to_the_game(captured):
    assert app.page_difficulty(None) is None
    assert app.page_difficulty(FakeBridge()) is None
    assert app.page_difficulty(FakeBridge(jb_difficulty="")) is None
    assert app.page_difficulty(FakeBridge(jb_difficulty="veteran")) == "veteran"
    assert app.page_difficulty(FakeBridge(jb_difficulty="ace")) is None  # reported, ignored
    warning = next(e for e in parsed(captured) if e["event"] == "warning")
    assert warning["what"] == "difficulty" and warning["value"] == "ace"
    page = TEMPLATE.read_text()
    assert 'jb_difficulty = new URLSearchParams(window.location.search).get("difficulty")' in page


def test_a_whole_snapshot_names_the_level_and_stays_json():
    data = Game(seed=1, state_interval=float("inf"), difficulty="veteran").snapshot()
    assert json.loads(json.dumps(data))["difficulty"] == "veteran"
