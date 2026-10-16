"""Sanity checks on the parameter sheet so a typo cannot silently break the balance."""

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
