"""Sanity checks on the parameter sheet so a typo cannot silently break the balance."""

import pytest

from jenesboat_v2.sim import params as P


def test_submarine_is_faster_surfaced_than_submerged():
    assert P.TYPE_VIIC.vessel.max_speed > P.TYPE_VIIC.submerged_speed
    assert 0 < P.TYPE_VIIC.periscope_depth < P.TYPE_VIIC.deep_depth < P.TYPE_VIIC.max_depth
    assert P.TYPE_VIIC.fire_max_depth >= P.TYPE_VIIC.periscope_depth


def test_a_submerged_boat_cannot_catch_a_fleeing_merchant():
    for ship in (P.FREIGHTER, P.TANKER):
        assert ship.vessel.max_speed > P.TYPE_VIIC.submerged_speed
        assert ship.vessel.max_speed < P.TYPE_VIIC.vessel.max_speed
        assert ship.cruise_speed <= ship.vessel.max_speed


def test_torpedo_outruns_everything_within_its_run():
    for torp in (P.G7E, P.G7A):
        assert torp.speed > P.FREIGHTER.vessel.max_speed
        assert torp.arm_distance < torp.max_run
        assert torp.tubes > 0 and torp.reload_time > 0


def test_sub_sees_merchants_before_they_see_it():
    assert P.TYPE_VIIC.lookout_range > P.DETECTION.surfaced_range
    assert P.TYPE_VIIC.periscope_range > P.DETECTION.periscope_range
    assert P.DETECTION.periscope_max_depth < P.TYPE_VIIC.deep_depth
    assert P.TYPE_VIIC.hydrophone_range >= P.TYPE_VIIC.lookout_range


def test_ship_types_are_indexed_by_name():
    assert set(P.SHIP_TYPES) == {"freighter", "tanker", "destroyer"}
    assert P.SHIP_TYPES["tanker"].hits_to_sink == 2


@pytest.mark.parametrize("name", list(P.DIFFICULTIES), ids=list(P.DIFFICULTIES))
def test_escort_balance_relations_hold_at_every_level(name):
    rules = P.DIFFICULTIES[name].rules
    sonar, dc, ai, det = rules.sonar, rules.depth_charge, rules.escort_ai, rules.detection
    # A destroyer out-hunts a merchant, but sprinting deafens its own sonar.
    assert P.DESTROYER.vessel.max_speed > P.FREIGHTER.vessel.max_speed
    assert ai.attack_speed > sonar.own_noise_speed >= ai.approach_speed
    # Sonar outreaches a periscope lookout even against a creeping boat, but an end-on boat
    # under the layer can be held only a few hundred metres out.
    assert sonar.range * sonar.quiet_factor > det.periscope_range * P.DESTROYER.lookout
    quietest = sonar.range * sonar.quiet_factor * sonar.aspect_floor * sonar.layer_factor
    assert sonar.min_range < quietest < 1_000.0
    assert 0 < sonar.aspect_floor < 1 and 0 < sonar.layer_factor < 1
    assert 0 < sonar.arc <= 180 and sonar.min_range <= sonar.blind_zone_cap
    assert 0 < sonar.sure_fraction < 1 and sonar.area_base < sonar.area_span
    assert sonar.cloud_duration > sonar.ping_interval * 4
    # Charges: lethal inside damage, a boat cannot be lost to a single distant burst; the
    # depth bands tile the water from the shallowest setting to the boat's maximum depth.
    assert dc.lethal_radius < dc.damage_radius and 0 < dc.damage < 1
    assert dc.magazine >= dc.pattern_size * 2
    assert dc.bands[0][0] >= 15.0 and dc.bands[-1][1] == rules.submarine.max_depth
    assert all(a[1] == b[0] for a, b in zip(dc.bands, dc.bands[1:], strict=False))
    assert 0 < dc.confirm_damage < dc.damage
    assert dc.pattern_cooldown >= dc.run_max_time
    assert ai.lose_track_time > sonar.ping_interval * 10
    assert ai.datum_attack_age > 60.0 and ai.blind_attacks >= 1 and ai.max_track_speed > 0
    assert ai.hunt_leash > ai.screen_distance and ai.max_hunt_time > ai.lose_track_time
    # The boat: deep is a resource that shrinks with damage; radar sees surfaced boats only.
    assert rules.submarine.overdepth_rate > 0
    assert rules.radar.range == 0 or rules.radar.range > det.surfaced_range * P.DESTROYER.lookout
    assert 0 < rules.sea.layer_min < rules.sea.layer_max < rules.submarine.max_depth
    assert ai.max_hunters >= 1 and ai.hunters_per_escort >= 1
    # The torpedo and the boat stay the same weapon and hull, whatever the reload time.
    assert rules.torpedo.speed == P.G7E.speed and rules.torpedo.reload_time > 0
    assert rules.submarine.vessel.max_speed > rules.submarine.submerged_speed
    assert rules.scenario.escorts >= 1
