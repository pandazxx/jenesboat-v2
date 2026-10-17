"""The whole loop, played by a scripted skipper: find the group, get ahead of it, dive, wait
and fire when the fire-control solution says so.  This is the automated twin of the M1
acceptance criteria ("a complete game play loop" and "medium challenge to score a hit")."""

from __future__ import annotations

import pytest

from jenesboat_v2 import events
from jenesboat_v2.game import Game
from jenesboat_v2.sim import hunting_scenario
from jenesboat_v2.sim.geo import angle_diff, bearing, distance, project, ray_line_crossing
from jenesboat_v2.sim.params import TYPE_VIIC

AMBUSH_OFFSET = 2_000.0  # m beside the group's track; the nearest ship passes ~1.2 km away
RUN_UP = 1_500.0  # m of straight approach so the boat arrives pointing at the track


def steer_toward(sub, x, y) -> None:
    sub.set_rudder(max(-1.0, min(1.0, angle_diff(bearing(sub.x, sub.y, x, y), sub.heading) / 10)))


def play(seed: int, max_minutes: float = 150.0, escorts: int = 0) -> list[dict]:
    log: list[dict] = []
    events.set_sink(lambda line: log.append(events.parse(line)))
    try:
        world = hunting_scenario(seed, escorts=escorts)
        game = Game(world=world, seed=seed, state_interval=float("inf"))
        sub = world.player
        # The skipper reads the intel and plots the group's track from the middle ship.
        lead = world.ships[1]
        track_heading = lead.heading
        cross = ray_line_crossing(lead.x, lead.y, track_heading, sub.x, sub.y, track_heading + 90)
        assert cross is not None
        along, side = cross
        pass_x, pass_y = project(lead.x, lead.y, track_heading, along)
        # Ambush point: beside the track, on the boat's side, with a straight run-up to it.
        toward_track = track_heading + (90.0 if side < 0 else -90.0)
        ambush = project(pass_x, pass_y, toward_track + 180.0, AMBUSH_OFFSET)
        run_up = project(*ambush, toward_track + 180.0, RUN_UP)

        phase = "run_up"
        fired_at = None
        while world.time < max_minutes * 60:
            if phase == "run_up":
                sub.set_throttle(1.0)
                steer_toward(sub, *run_up)
                if distance(sub.x, sub.y, *run_up) < 150:
                    phase = "ambush"
            elif phase == "ambush":
                steer_toward(sub, *ambush)
                if distance(sub.x, sub.y, *ambush) < 250:
                    sub.set_throttle(0.0)
                    sub.set_rudder(0.0)
                    sub.set_target_depth(TYPE_VIIC.periscope_depth)
                    phase = "wait"
            elif phase == "wait":
                sol = game.solution()
                if sol is not None and sol.error <= 0 and sol.run <= 3_000 and sub.can_fire:
                    assert game.fire()
                    fired_at = world.time
                    phase = "watch"
            elif phase == "watch":
                if world.time - fired_at > 400 or world.mission()["status"] != "active":
                    break
            game.set_time_scale(8)
            game.update(0.1)
        return [e for e in log if e]
    finally:
        events.set_sink(None)


@pytest.mark.parametrize("seed", range(6))
def test_scripted_ambush_scores_a_hit(seed):
    log = play(seed)
    kinds = [e["event"] for e in log]
    assert "intel" in kinds
    assert "contact" in kinds  # the group was sighted
    assert "fire" in kinds, "the skipper never got a firing solution"
    assert "hit" in kinds, f"fired but missed: {[e for e in log if e['event'] != 'state'][-6:]}"
    # Nobody saw us before the torpedo hit.
    first_alert = next((e for e in log if e["event"] == "alert"), None)
    assert first_alert is None or first_alert["reason"] == "torpedo"


def test_escorted_hunt_is_harder_but_a_hit_is_still_normal():
    """Acceptance: "more challenging game play but still achievable".  The same scripted
    skipper, who ignores the destroyers, still lands a hit on most seeds."""
    hits = 0
    for seed in range(8):
        log = play(seed, escorts=2)
        hits += any(e["event"] == "hit" for e in log)
    assert 4 <= hits  # unescorted it is 8 of 8; the escort costs some, not most


def test_a_surfaced_approach_is_spotted_and_the_group_runs():
    log: list[dict] = []
    events.set_sink(lambda line: log.append(events.parse(line)))
    try:
        game = Game(world=hunting_scenario(1, escorts=0), seed=1, state_interval=float("inf"))
        sub = game.world.player
        target = game.world.ships[1]
        while game.world.time < 3 * 3600:
            sub.set_throttle(1.0)
            steer_toward(sub, target.x, target.y)
            game.set_time_scale(8)
            game.update(0.1)
            if any(e and e["event"] == "alert" for e in log):
                break
        alert = next(e for e in log if e and e["event"] == "alert")
        assert alert["reason"] == "sighted"
        d = distance(sub.x, sub.y, target.x, target.y)
        assert d <= 6_600  # sighted at the 6 km lookout range (+ the 3 s spot timer at x8)
        game.set_time_scale(1)
        for _ in range(3000):  # 5 min: they run at full speed, the submerged boat cannot follow
            game.update(0.1)
        assert all(s.speed > 0.9 * s.params.max_speed for s in game.world.active_ships)
    finally:
        events.set_sink(None)
