"""Fundamental parameters: every tunable of the simulation in one place.

Units are SI throughout the sim: metres, seconds, m/s, degrees clockwise from north.  Knots
and kilometres appear only in the HUD and in the docs.  ``docs/PARAMETERS.md`` explains each
value and where it comes from; change numbers here, not in the modules that use them.
"""

from __future__ import annotations

from dataclasses import dataclass

KNOT = 0.514444  # metres per second
HOUR = 3600.0

# Engine telegraph: the propeller orders the player steps through, as throttle fractions.
TELEGRAPH: tuple[tuple[str, float], ...] = (
    ("ASTERN FULL", -1.0),
    ("ASTERN HALF", -0.5),
    ("STOP", 0.0),
    ("AHEAD SLOW", 0.25),
    ("AHEAD HALF", 0.5),
    ("AHEAD FULL", 0.75),
    ("AHEAD FLANK", 1.0),
)
TELEGRAPH_STOP = 2  # index of STOP
RUDDER_MAX_ANGLE = 35.0  # degrees at full rudder (display only; the sim uses -1..1)
RUDDER_RATE = 0.5  # rudder units per second while A/D is held (hard over in 2 s)


@dataclass(frozen=True)
class VesselParams:
    """Classic ship maneuvering: propeller sets speed with inertia, rudder turns on a radius."""

    max_speed: float  # m/s, full ahead
    acceleration: float = 0.3  # m/s^2 toward the ordered speed
    turn_radius: float = 300.0  # m, radius of the circle steamed at full rudder
    max_turn_rate: float = 4.0  # deg/s, cap so fast ships do not spin
    reverse_fraction: float = 0.5  # max astern speed as a fraction of max_speed
    length: float = 60.0  # metres (hull box and hit test)
    beam: float = 8.0  # metres (hull box and hit test)


@dataclass(frozen=True)
class TorpedoParams:
    name: str
    speed: float  # m/s
    max_run: float  # m, the torpedo sinks after this run
    arm_distance: float  # m, no detonation closer than this to the tube
    tubes: int  # bow tubes, each holds one torpedo
    reserves: int  # torpedoes stowed for reloading
    reload_time: float  # s, to reload one tube
    wake_visible_range: float  # m, how far lookouts see its track (0 = wakeless)


@dataclass(frozen=True)
class DeckGunParams:
    """Defined for the parameter sheet; firing the gun is a Milestone 2 feature."""

    name: str
    calibre_mm: float
    max_range: float  # m
    rate: float  # s between rounds
    rounds: int
    hits_per_freighter: int  # rounds needed to sink a freighter


@dataclass(frozen=True)
class SubmarineParams:
    vessel: VesselParams  # surfaced kinematics
    submerged_speed: float  # m/s, electric motors
    periscope_depth: float  # m
    deep_depth: float  # m, the "go deep" order
    max_depth: float  # m
    dive_rate: float  # m/s vertical
    fire_max_depth: float  # m, tubes can be fired at or above this depth
    battery_full_speed_hours: float  # endurance at full submerged speed
    battery_creep_hours: float  # endurance with motors nearly stopped
    recharge_hours: float  # surfaced, diesels charging
    battery_empty_speed_fraction: float  # of submerged speed once the battery is flat
    lookout_range: float  # m, surfaced, daylight, big merchant with smoke
    periscope_range: float  # m, at periscope depth
    periscope_band: float  # m, periscope usable while depth <= periscope_depth + band
    hydrophone_range: float  # m, bearing-only contacts
    hydrophone_min_depth: float  # m, hydrophones useless on the surface
    hydrophone_max_speed: float  # m/s, own noise masks contacts above this


@dataclass(frozen=True)
class ShipType:
    name: str
    kind: str  # "merchant" or "military"
    vessel: VesselParams
    cruise_speed: float  # m/s, economical speed on the route
    tonnage: int  # GRT, the score for sinking it
    hits_to_sink: int  # torpedo hits
    visibility: float  # multiplier on how far the sub sees it (size, smoke)
    lookout: float  # multiplier on how far it sees the sub


@dataclass(frozen=True)
class DetectionParams:
    """How a ship's lookouts see the submarine (daylight; multiply by ``light`` at night)."""

    surfaced_range: float  # m, a surfaced boat
    periscope_range: float  # m, a periscope at quiet speed
    periscope_quiet_speed: float  # m/s, above this the feather and wake grow
    periscope_speed_penalty: float  # m of extra detection range per m/s above quiet speed
    periscope_max_depth: float  # m, deeper than this the boat is invisible
    spot_time: float  # s the boat must stay in range before the ship reacts


@dataclass(frozen=True)
class MerchantAIParams:
    alert_duration: float  # s of running after the last sighting
    zigzag_angle: float  # deg either side of the escape course
    zigzag_period: float  # s per leg
    spread_angle: float  # deg between neighbours so a group fans out
    escape_range: float  # m from the boat at which an alerted merchant counts as escaped
    panic_range: float  # m, a torpedo hit alerts merchants within this distance


# --- vessels -------------------------------------------------------------------------------

TYPE_VIIC_SURFACED = VesselParams(
    max_speed=17.7 * KNOT,
    acceleration=0.2,
    turn_radius=140.0,
    max_turn_rate=4.0,
    reverse_fraction=0.4,
    length=67.0,
    beam=6.2,
)

TYPE_VIIC = SubmarineParams(
    vessel=TYPE_VIIC_SURFACED,
    submerged_speed=7.6 * KNOT,
    periscope_depth=12.0,
    deep_depth=60.0,
    max_depth=150.0,
    dive_rate=1.0,
    fire_max_depth=20.0,
    battery_full_speed_hours=1.5,
    battery_creep_hours=20.0,
    recharge_hours=3.0,
    battery_empty_speed_fraction=0.15,
    lookout_range=12_000.0,
    periscope_range=7_000.0,
    periscope_band=2.0,
    hydrophone_range=15_000.0,
    hydrophone_min_depth=11.0,
    hydrophone_max_speed=4.0 * KNOT,
)

FREIGHTER = ShipType(
    name="freighter",
    kind="merchant",
    vessel=VesselParams(
        max_speed=11.0 * KNOT,
        acceleration=0.08,
        turn_radius=350.0,
        max_turn_rate=2.0,
        length=120.0,
        beam=16.0,
    ),
    cruise_speed=8.0 * KNOT,
    tonnage=4_500,
    hits_to_sink=1,
    visibility=1.0,
    lookout=1.0,
)

TANKER = ShipType(
    name="tanker",
    kind="merchant",
    vessel=VesselParams(
        max_speed=10.0 * KNOT,
        acceleration=0.06,
        turn_radius=450.0,
        max_turn_rate=1.5,
        length=160.0,
        beam=21.0,
    ),
    cruise_speed=8.0 * KNOT,
    tonnage=9_000,
    hits_to_sink=2,
    visibility=1.15,
    lookout=1.0,
)

DESTROYER = ShipType(
    name="destroyer",
    kind="military",
    vessel=VesselParams(
        max_speed=32.0 * KNOT,
        acceleration=0.5,
        turn_radius=250.0,
        max_turn_rate=6.0,
        length=100.0,
        beam=10.0,
    ),
    cruise_speed=12.0 * KNOT,
    tonnage=1_800,
    hits_to_sink=1,
    visibility=0.8,
    lookout=1.5,
)

SHIP_TYPES: dict[str, ShipType] = {t.name: t for t in (FREIGHTER, TANKER, DESTROYER)}

# --- weapons -------------------------------------------------------------------------------

G7E = TorpedoParams(
    name="G7e",
    speed=30.0 * KNOT,
    max_run=5_000.0,
    arm_distance=300.0,
    tubes=4,
    reserves=8,
    reload_time=120.0,
    wake_visible_range=0.0,
)

G7A = TorpedoParams(
    name="G7a",
    speed=40.0 * KNOT,
    max_run=6_000.0,
    arm_distance=300.0,
    tubes=4,
    reserves=8,
    reload_time=120.0,
    wake_visible_range=1_500.0,
)

DECK_GUN_88 = DeckGunParams(
    name="8.8 cm SK C/35",
    calibre_mm=88.0,
    max_range=4_000.0,
    rate=6.0,
    rounds=200,
    hits_per_freighter=12,
)

# --- rules ---------------------------------------------------------------------------------

DETECTION = DetectionParams(
    surfaced_range=6_000.0,
    periscope_range=1_000.0,
    periscope_quiet_speed=3.0 * KNOT,
    periscope_speed_penalty=900.0,
    periscope_max_depth=14.0,
    spot_time=3.0,
)

MERCHANT_AI = MerchantAIParams(
    alert_duration=600.0,
    zigzag_angle=30.0,
    zigzag_period=90.0,
    spread_angle=20.0,
    escape_range=20_000.0,
    panic_range=6_000.0,
)
