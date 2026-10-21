"""Fundamental parameters: every tunable of the simulation in one place.

Units are SI throughout the sim: metres, seconds, m/s, degrees clockwise from north.  Knots
and kilometres appear only in the HUD and in the docs.  ``docs/PARAMETERS.md`` explains each
value and where it comes from; change numbers here, not in the modules that use them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

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


@dataclass(frozen=True)
class SonarParams:
    """A destroyer's active sonar (ASDIC): long reach, but blind to the boat's depth and easily
    drowned by noise.  Range is ``range`` times the factors below."""

    range: float  # m, quiet sea, boat at full submerged noise
    min_range: float  # m, inside this the echo is lost (the attacker is over the boat)
    own_noise_speed: float  # m/s, faster than this the ship's own screws deafen the set
    own_noise_factor: float  # range multiplier while faster than that
    interference_radius: float  # m, other ships this close add their noise to the sea
    interference_per_ship: float  # range lost per neighbouring ship (fraction of range)
    interference_floor: float  # range never drops below this fraction
    quiet_speed: float  # m/s, a boat creeping at or below this is harder to hear
    quiet_factor: float  # range multiplier for a creeping boat
    ping_interval: float  # s between pings; the fix is as old as the last ping
    position_error: float  # m, error of the fix (each axis) before it is used as a datum


@dataclass(frozen=True)
class DepthChargeParams:
    sink_rate: float  # m/s, how fast a charge sinks to its set depth
    lethal_radius: float  # m, a burst this close breaks the boat
    damage_radius: float  # m, a burst this close hurts the boat
    damage: float  # hull damage (0..1; the boat is lost at 1) at the edge of damage_radius
    depth_error: float  # m, the pattern is layered over the boat's depth +- this
    min_depth: float  # m, shallowest setting
    pattern_size: int  # charges per attack run, layered in depth and thrown to both sides
    drop_interval: float  # s between charges in a pattern
    throw_range: float  # m, projectors throw a charge up to this far from the ship
    scatter: float  # m, each charge lands up to this far either side of the predicted path
    pattern_cooldown: float  # s before the same ship starts another run
    magazine: int  # charges carried per destroyer


@dataclass(frozen=True)
class EscortAIParams:
    hunters_per_escort: int  # one hunter per this many escorts (at least one), max_hunters cap
    max_hunters: int
    track_window: float  # s of sonar fixes used to estimate the boat's course and speed
    track_min_baseline: float  # s, fixes closer in time than this give no course estimate
    max_track_speed: float  # m/s, a faster estimate is noise (the boat's best submerged speed)
    lead_limit: float  # s, the prediction is never carried further than this past the last fix
    lose_track_time: float  # s without a fix or sighting before the escort stands down
    station_ahead: float  # m, formation station ahead of the convoy centre
    station_abeam: float  # m, formation station abeam of the convoy centre (alternating sides)
    screen_distance: float  # m from the convoy centre toward the threat
    screen_abeam: float  # m between screening ships
    station_tolerance: float  # m, within this the ship holds course at convoy speed
    attack_speed: float  # m/s, hunting speed (sonar is degraded above own_noise_speed)
    approach_range: float  # m from the datum where a hunter slows so its sonar can hear
    approach_speed: float  # m/s, the closing speed inside approach_range
    search_speed: float  # m/s, speed while searching the datum area
    search_start: float  # m, first search circle radius around the datum
    search_growth: float  # m/s, how fast the circle widens as the track gets older
    search_max: float  # m
    shelter_distance: float  # m behind the screening ship that merchants run to
    shelter_radius: float  # m, merchants this near the shelter point stop closing in


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

SONAR_ASDIC = SonarParams(
    range=3_000.0,
    min_range=150.0,
    own_noise_speed=15.0 * KNOT,
    own_noise_factor=0.4,
    interference_radius=2_500.0,
    interference_per_ship=0.12,
    interference_floor=0.4,
    quiet_speed=2.5 * KNOT,
    quiet_factor=0.7,
    ping_interval=5.0,
    position_error=40.0,
)

DEPTH_CHARGE = DepthChargeParams(
    sink_rate=3.0,
    lethal_radius=12.0,
    damage_radius=45.0,
    damage=0.4,
    depth_error=25.0,
    min_depth=15.0,
    pattern_size=6,
    drop_interval=1.0,
    throw_range=150.0,
    scatter=15.0,
    pattern_cooldown=45.0,
    magazine=40,
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

ESCORT_AI = EscortAIParams(
    hunters_per_escort=3,
    max_hunters=2,
    track_window=45.0,
    track_min_baseline=10.0,
    max_track_speed=7.6 * KNOT,
    lead_limit=90.0,
    lose_track_time=300.0,
    station_ahead=1_200.0,
    station_abeam=1_500.0,
    screen_distance=2_000.0,
    screen_abeam=700.0,
    station_tolerance=250.0,
    attack_speed=20.0 * KNOT,
    approach_range=1_500.0,
    approach_speed=14.0 * KNOT,
    search_speed=12.0 * KNOT,
    search_start=400.0,
    search_growth=1.0,
    search_max=2_500.0,
    shelter_distance=700.0,
    shelter_radius=400.0,
)


# --- difficulty levels ---------------------------------------------------------------------
# A difficulty (cadet, patrol, veteran) is plain data: the parameter blocks above, bundled,
# with whole blocks swapped for ``replace`` copies, plus the name of the strategy filling
# each AI slot.  The plug-in mechanism (registering strategies, looking them up, checking a
# difficulty) is ``sim/difficulty.py``; the design is explained in ``docs/DIFFICULTY.md``.


@dataclass(frozen=True)
class ScenarioParams:
    """What the hunting scenario puts on the map besides the three merchants."""

    escorts: int  # destroyers with the group


SCENARIO = ScenarioParams(escorts=2)


@dataclass(frozen=True)
class Rules:
    """The complete parameter set one hunt runs on.  The world carries one and every module
    reads its numbers from ``world.rules``; the defaults are the sheet above."""

    submarine: SubmarineParams = TYPE_VIIC
    torpedo: TorpedoParams = G7E
    detection: DetectionParams = DETECTION
    merchant_ai: MerchantAIParams = MERCHANT_AI
    sonar: SonarParams = SONAR_ASDIC
    depth_charge: DepthChargeParams = DEPTH_CHARGE
    escort_ai: EscortAIParams = ESCORT_AI
    scenario: ScenarioParams = SCENARIO


@dataclass(frozen=True)
class Strategies:
    """Which behaviour fills each AI decision point (a *slot*).  Each value names a strategy
    registered in ``sim/difficulty.py``; the defaults are the M1/M2 behaviours."""

    escort_search: str = "box"  # how a hunter sweeps for a boat whose track has gone stale
    escort_evade: str = "none"  # what an escort does about a torpedo running at it
    merchant_flee: str = "zigzag"  # how an alerted merchant runs


@dataclass(frozen=True)
class Difficulty:
    """A difficulty level (not a game level: there is one hunt, played harder or easier)."""

    name: str  # the id used on the command line, the URL and in events
    title: str  # what the HUD shows
    description: str  # one line for --help and the docs
    rules: Rules
    strategies: Strategies


CADET = Difficulty(
    name="cadet",
    title="Cadet",
    description="one destroyer with a short sonar and a short memory, lighter charges, "
    "quick reloads",
    rules=Rules(
        torpedo=replace(G7E, reload_time=90.0),
        sonar=replace(SONAR_ASDIC, range=2_400.0),
        depth_charge=replace(DEPTH_CHARGE, damage=0.3),
        escort_ai=replace(ESCORT_AI, lose_track_time=180.0),
        scenario=ScenarioParams(escorts=1),
    ),
    strategies=Strategies(),
)

PATROL = Difficulty(
    name="patrol",
    title="Patrol",
    description="two destroyers, the Milestone 2 balance (the default)",
    rules=Rules(),
    strategies=Strategies(),
)

VETERAN = Difficulty(
    name="veteran",
    title="Veteran",
    description="three destroyers with longer sonar reach and memory, heavier charges, "
    "slow reloads",
    rules=Rules(
        torpedo=replace(G7E, reload_time=150.0),
        sonar=replace(SONAR_ASDIC, range=3_600.0),
        depth_charge=replace(DEPTH_CHARGE, damage=0.5, lethal_radius=15.0),
        escort_ai=replace(ESCORT_AI, lose_track_time=480.0),
        scenario=ScenarioParams(escorts=3),
    ),
    strategies=Strategies(),
)

DIFFICULTIES: dict[str, Difficulty] = {d.name: d for d in (CADET, PATROL, VETERAN)}
DEFAULT_DIFFICULTY = PATROL.name
