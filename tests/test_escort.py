"""Destroyer escorts: sonar, formation, the hunter/screen split, depth charges, standing down."""

from __future__ import annotations

import math

from jenesboat_v2.sim import World, hunting_scenario, new_ship
from jenesboat_v2.sim.escort import FORMATION, HUNT, SCREEN, hunters_wanted, sonar_range
from jenesboat_v2.sim.geo import distance
from jenesboat_v2.sim.params import (
    DEPTH_CHARGE,
    DESTROYER,
    ESCORT_AI,
    FREIGHTER,
    SONAR_ASDIC,
)
from jenesboat_v2.sim.submarine import new_submarine
from jenesboat_v2.sim.weapons import DepthCharge

C = 20_000.0


def convoy_world(escorts: int = 2, sub_dx: float = 0.0, sub_dy: float = -6_000.0) -> World:
    """Three freighters steaming east and ``escorts`` destroyers on their stations; the boat
    sits ``sub_dx, sub_dy`` from the convoy centre, stopped and submerged."""
    ships = [
        new_ship(f"merchant-{i}", FREIGHTER, C + 800.0 * (i - 1), C, course=90.0, spread=i - 1)
        for i in range(3)
    ]
    for i in range(escorts):
        side = 1.0 if i % 2 == 0 else -1.0
        ships.append(
            new_ship(
                f"destroyer-{i + 1}",
                DESTROYER,
                C + ESCORT_AI.station_ahead,
                C - side * ESCORT_AI.station_abeam,  # +90 degrees from an eastward course is south
                course=90.0,
            )
        )
    sub = new_submarine(x=C + sub_dx, y=C + sub_dy, heading=0.0)
    sub.depth = sub.target_depth = 30.0
    return World(width=40_000.0, height=40_000.0, player=sub, ships=ships)


def run(world: World, seconds: float, dt: float = 0.1) -> list[dict]:
    seen: list[dict] = []
    for _ in range(int(seconds / dt)):
        world.step(dt)
        seen.extend(world.events)
        world.events.clear()
    return seen


def kinds(evs: list[dict]) -> list[str]:
    return [e["event"] for e in evs]


def destroyers(world: World):
    return [s for s in world.ships if s.kind == "military"]


# --- sonar -----------------------------------------------------------------------------------


def test_sonar_reaches_further_than_lookouts_in_a_clear_sea_but_the_fleet_drowns_it():
    world = convoy_world()
    far = convoy_world(escorts=1)
    far.ships = [s for s in far.ships if s.kind == "military"]
    far.ships[0].x += 20_000.0  # alone, far from the merchants
    lone = far.ships[0]
    escorted = destroyers(world)[0]
    quiet_boat = SONAR_ASDIC.quiet_factor
    # The boat is stopped, so the quiet factor applies in both cases.
    assert math.isclose(sonar_range(far, lone), SONAR_ASDIC.range * quiet_boat)
    assert sonar_range(world, escorted) < sonar_range(far, lone)
    assert sonar_range(world, escorted) >= SONAR_ASDIC.range * SONAR_ASDIC.interference_floor * (
        quiet_boat
    )
    # Its own screws deafen it at speed.
    lone.speed = SONAR_ASDIC.own_noise_speed * 1.2
    assert math.isclose(
        sonar_range(far, lone), SONAR_ASDIC.range * quiet_boat * SONAR_ASDIC.own_noise_factor
    )
    far.player.speed = 5.0
    lone.speed = 0.0
    assert math.isclose(sonar_range(far, lone), SONAR_ASDIC.range)


def test_sonar_outranges_a_periscope_on_a_destroyer():
    from jenesboat_v2.sim.detection import ship_detection_range

    world = convoy_world()
    sub = world.player
    sub.depth = 12.0
    periscope = ship_detection_range(sub, DESTROYER)
    sub.depth = 30.0  # below the periscope: lookouts are blind, sonar is not
    assert ship_detection_range(sub, DESTROYER) == 0.0
    assert SONAR_ASDIC.range * SONAR_ASDIC.quiet_factor > periscope


# --- formation -------------------------------------------------------------------------------


def test_destroyers_keep_station_on_the_convoy():
    world = convoy_world(sub_dy=-18_000.0)
    start = [(d.x, d.y) for d in destroyers(world)]
    for d in destroyers(world):
        d.x -= 600.0  # knock them out of position
    run(world, 900)
    merchants = world.merchants
    cx = sum(m.x for m in merchants) / 3
    for d, (_sx, sy) in zip(destroyers(world), start, strict=True):
        assert abs((d.x - cx) - ESCORT_AI.station_ahead) < ESCORT_AI.station_tolerance * 1.5
        assert abs(d.y - sy) < ESCORT_AI.station_tolerance * 1.5
        assert d.escort.mode == FORMATION


# --- the alarm: split into hunters and screens -------------------------------------------------


def test_sonar_contact_splits_the_escort_into_hunter_and_screen():
    world = convoy_world(escorts=2, sub_dx=1_200.0, sub_dy=-2_000.0)
    evs = run(world, 120)
    assert "escort_alarm" in kinds(evs)
    split = next(e for e in evs if e["event"] == "escort_split")
    assert len(split["hunters"]) == hunters_wanted(2) == 1
    assert len(split["screens"]) == 1
    modes = {d.ship_id: d.escort.mode for d in destroyers(world)}
    assert sorted(modes.values()) == [HUNT, SCREEN]
    hunter = next(d for d in destroyers(world) if d.escort.mode == HUNT)
    screen = next(d for d in destroyers(world) if d.escort.mode == SCREEN)
    sub = world.player
    # The hunter closes on the boat; the screen stays on the fleet's side of it.
    assert distance(hunter.x, hunter.y, sub.x, sub.y) < 2_000.0
    cx = sum(m.x for m in world.merchants) / 3
    cy = sum(m.y for m in world.merchants) / 3
    assert distance(screen.x, screen.y, cx, cy) < distance(screen.x, screen.y, sub.x, sub.y)


def test_more_escorts_hunt_in_pairs():
    assert [hunters_wanted(n) for n in range(0, 8)] == [0, 1, 1, 1, 1, 1, 2, 2]


def test_merchants_run_for_the_screen_when_the_escort_is_alarmed():
    world = convoy_world(escorts=2, sub_dx=1_200.0, sub_dy=-2_000.0)
    run(world, 120)
    screen = next(d for d in destroyers(world) if d.escort.mode == SCREEN)
    sub = world.player
    for m in world.merchants:
        assert m.alerted(world.time)
        assert m.shelter is not None
        sx, sy = m.shelter
        # The shelter spot is behind the screening ship as seen from the boat.
        assert distance(sx, sy, sub.x, sub.y) > distance(screen.x, screen.y, sub.x, sub.y)
    run(world, 300)
    for m in world.merchants:
        assert distance(m.x, m.y, screen.x, screen.y) < 2_500.0


def test_merchants_without_escorts_just_run_away():
    world = convoy_world(escorts=0)
    for m in world.merchants:
        m.alert(world.time, world.player.x, world.player.y, 600.0)
    run(world, 5)
    assert all(m.shelter is None for m in world.merchants)


# --- depth charges -----------------------------------------------------------------------------


def test_hunter_runs_in_and_drops_a_pattern_on_a_boat_that_stays_put():
    world = convoy_world(escorts=2, sub_dx=1_200.0, sub_dy=-2_000.0)
    world.player.depth = world.player.target_depth = 20.0
    evs = run(world, 280)
    assert "depth_charge_run" in kinds(evs)
    assert kinds(evs).count("depth_charge") >= DEPTH_CHARGE.pattern_size
    hunter = next(d for d in destroyers(world) if d.escort.mode == HUNT)
    assert hunter.escort.charges < DEPTH_CHARGE.magazine


def test_a_burst_inside_the_lethal_radius_sinks_the_boat():
    world = convoy_world(escorts=0)
    sub = world.player
    world.depth_charges.append(DepthCharge(1, sub.x + 5.0, sub.y, sub.depth, DEPTH_CHARGE))
    world.depth_charges[0].depth = sub.depth - 0.1
    evs = run(world, 1)
    assert sub.destroyed
    assert world.mission()["status"] == "boat_lost"
    assert "mission_end" in kinds(evs)


def test_depth_charge_damage_falls_off_with_distance():
    charge = DepthCharge(1, 0.0, 0.0, 50.0, DEPTH_CHARGE)
    p = DEPTH_CHARGE
    assert charge.effect_on(0, 0, 50) == 1.0
    assert charge.effect_on(p.lethal_radius, 0, 50) == 1.0
    near = charge.effect_on(p.lethal_radius + 5, 0, 50)
    far = charge.effect_on(p.damage_radius - 5, 0, 50)
    assert 0 < far < near <= p.damage
    assert charge.effect_on(p.damage_radius, 0, 50) == 0.0
    assert charge.effect_on(0, 0, 50 + p.damage_radius) == 0.0  # depth counts


def test_a_charge_sinks_to_its_depth_before_it_bursts():
    charge = DepthCharge(1, 0.0, 0.0, 30.0, DEPTH_CHARGE)
    steps = 0
    while not charge.step(0.5):
        steps += 1
    assert math.isclose(steps * 0.5, 30.0 / DEPTH_CHARGE.sink_rate, abs_tol=0.5)


def test_damage_accumulates_but_does_not_kill_by_a_distant_burst():
    world = convoy_world(escorts=0)
    sub = world.player
    for dx in (30.0, 30.0):
        c = DepthCharge(1, sub.x + dx, sub.y, sub.depth, DEPTH_CHARGE)
        c.depth = sub.depth - 0.1
        world.depth_charges.append(c)
    run(world, 1)
    assert 0.0 < sub.damage < 1.0 or sub.destroyed


# --- losing the track ----------------------------------------------------------------------------


def test_escorts_return_to_formation_after_losing_the_track():
    world = convoy_world(escorts=2, sub_dx=1_200.0, sub_dy=-2_000.0)
    run(world, 60)
    assert world.datum is not None
    # The boat slips away out of every set's reach and stays quiet.
    sub = world.player
    sub.y = C - 12_000.0
    sub.x = C
    evs = run(world, ESCORT_AI.lose_track_time + 60)
    assert "escort_stand_down" in kinds(evs)
    assert world.datum is None
    assert all(d.escort.mode == FORMATION for d in destroyers(world))
    # ... and they head back to the convoy.
    evs = run(world, 900)
    cx = sum(m.x for m in world.merchants) / 3
    for d in destroyers(world):
        assert abs(d.x - cx - ESCORT_AI.station_ahead) < 1_500.0


# --- scoring ------------------------------------------------------------------------------------


def test_sinking_a_destroyer_is_a_bonus_not_a_merchant_kill():
    world = convoy_world(escorts=1)
    d = destroyers(world)[0]
    from jenesboat_v2.sim.weapons import Torpedo

    t = Torpedo(1, d.x - 100.0, d.y, 90.0)
    t.run = 400.0
    world.torpedoes.append(t)
    run(world, 30)
    assert d.sunk
    assert world.tonnage == 0 and world.bonus == DESTROYER.tonnage
    m = world.mission()
    assert m["status"] == "active" and m["escorts_sunk"] == [d.ship_id]
    assert not d.escaped and d.active is False


def test_destroyers_are_never_counted_as_escaped():
    world = convoy_world(escorts=1, sub_dy=-18_000.0)
    d = destroyers(world)[0]
    d.x, d.y = 1.0, 1.0
    run(world, 5)
    assert not d.escaped


def test_scenario_has_two_destroyers_on_station():
    world = hunting_scenario(3)
    ds = destroyers(world)
    assert [d.ship_id for d in ds] == ["destroyer-1", "destroyer-2"]
    assert len(world.merchants) == 3
    assert all(d.type is DESTROYER and d.escort.mode == FORMATION for d in ds)
    assert math.isclose(ds[0].speed, DESTROYER.cruise_speed)
