# Parameter sheet

Every tunable of the simulation lives in `src/jenesboat_v2/sim/params.py`. This page explains
the values. Units in the sim are metres, seconds and m/s; headings and bearings are degrees
clockwise from north. The HUD converts to knots and kilometres. `tests/test_params.py` checks
the relations that the game balance depends on (e.g. "a submerged boat cannot catch a
fleeing merchant").

## Orders (`TELEGRAPH`, `RUDDER_MAX_ANGLE`, `RUDDER_RATE`)

The engine telegraph has seven positions: ASTERN FULL (-1.0), ASTERN HALF (-0.5), STOP, AHEAD
SLOW (0.25), AHEAD HALF (0.5), AHEAD FULL (0.75), AHEAD FLANK (1.0), as fractions of the
vessel's current speed limit (so AHEAD HALF is 8.9 kn surfaced and 3.8 kn submerged, just
under the hydrophone limit). The rudder moves at `RUDDER_RATE` = 0.5 per second while A/D is
held (hard over, 35°, in 2 s) and stays where it is released.

## Vessel motion (`VesselParams`)

All vessels use the same classic model: the propeller order sets a target speed that the ship
approaches at `acceleration`; the rudder turns the ship on a circle of `turn_radius`, so the
turn rate in deg/s is `rudder * speed / turn_radius` (capped at `max_turn_rate`). A stopped
ship does not turn and a ship going astern turns the other way.

| vessel | max speed | accel | turn radius | max turn | length x beam | notes |
| --- | --- | --- | --- | --- | --- | --- |
| Type VIIC surfaced | 17.7 kn | 0.20 m/s² | 140 m | 4.0 °/s | 67 x 6.2 m | diesels; tactical diameter ~300 m |
| Type VIIC submerged | 7.6 kn | same | same | same | same | electric motors, see below |
| freighter | 11 kn (cruise 8) | 0.08 | 350 m | 2.0 | 120 x 16 m | 4,500 GRT, 1 torpedo |
| tanker | 10 kn (cruise 8) | 0.06 | 450 m | 1.5 | 160 x 21 m | 9,000 GRT, 2 torpedoes |
| destroyer | 32 kn (cruise 12) | 0.50 | 250 m | 6.0 | 100 x 10 m | escort, M2: 1,800 GRT bonus, 1 torpedo |

Sources are the usual Type VIIC figures (17.7 / 7.6 kn) and typical WWII tramp steamers and
tankers (8 kn convoy speed, 10-11 kn flat out). Turn radii are a little tighter than reality so
the game stays playable without time compression above x8.

## Submarine (`SubmarineParams`, `TYPE_VIIC`)

| parameter | value | why |
| --- | --- | --- |
| periscope depth | 12 m | periscope usable while depth <= 12 + 2 m (`periscope_band`) |
| deep depth | 60 m | the `C` order; invisible to lookouts, blind except hydrophone |
| max depth | 150 m | game limit (test depth of the type was ~230 m) |
| dive rate | 1 m/s | ~12 s to periscope depth, ~1 min to deep |
| fire max depth | 20 m | tubes can be fired at or above this depth |
| battery | 1.5 h at full submerged speed, 20 h at creep, 3 h recharge surfaced | drain grows with the cube of the throttle (propeller power); empty battery = 15 % of submerged speed |
| lookouts | 12 km (surfaced, day) | big merchant with smoke on a clear day |
| periscope | 7 km | low eye height |
| hydrophone | 15 km, bearing only | needs depth >= 11 m and own speed <= 4 kn |

Speed limit by depth: full `max_speed` on the surface, `submerged_speed` once the hull is under
(linear blend over the first 12 m), scaled by the battery rule.

## Weapons

| weapon | speed | run | arming | tubes / reserves | reload | wake |
| --- | --- | --- | --- | --- | --- | --- |
| G7e (electric, **M1 default**) | 30 kn | 5,000 m | 300 m | 4 / 8 | 120 s | none |
| G7a (steam) | 40 kn | 6,000 m | 300 m | 4 / 8 | 120 s | seen at 1,500 m |

Torpedoes leave the bow on the boat's heading and run straight (no gyro angle in M1). A hit is
the torpedo point entering the target's hull box after the arming distance.

The 8.8 cm deck gun (`DECK_GUN_88`: 4 km, one round per 6 s, 200 rounds, ~12 hits per
freighter) is defined on the sheet for Milestone 2 and cannot be fired yet.

## Detection (`DetectionParams`, how ships see the boat)

| boat state | seen at (day, lookout 1.0) |
| --- | --- |
| surfaced | 6,000 m |
| periscope depth, <= 3 kn | 1,000 m |
| periscope depth, faster | 1,000 m + 900 m per m/s above 3 kn (about 2,900 m at 7 kn) |
| deeper than 14 m | never |

Multiply by the ship type's `lookout` (destroyer 1.5) and by the world's `light` (1.0 = day;
night is a later milestone). A ship reacts only after the boat has stayed in range for
`spot_time` = 3 s; the timer runs down again when the boat drops out of range.

## Merchant AI (`MerchantAIParams`)

| parameter | value | effect |
| --- | --- | --- |
| alert duration | 600 s | keeps running this long after the last sighting, then returns to the route |
| zigzag | ±30° every 90 s | while running |
| spread | 20° between neighbours | a group fans out instead of running in a line |
| escape range | 20 km | a merchant this far from the boat (or off the map) has got away, alerted or not: the hunt area |
| panic range | 6 km | a torpedo hit alerts every merchant within this distance |

## Destroyer escort (M2: `SonarParams`, `DepthChargeParams`, `EscortAIParams`)

The scenario sends two destroyers (`ESCORTS` in `scenario.py`) with the three merchants; they
start on their formation stations, 1.2 km ahead of the group and 1.5 km off either flank.
Lookouts use the ordinary detection table (`lookout` 1.5 makes a surfaced boat visible at
9 km, a periscope at 1.5 km).

**Active sonar** (`SONAR_ASDIC`). Each destroyer pings every 5 s. The echo range is 3,000 m
multiplied by:

| factor | value | why |
| --- | --- | --- |
| other ships within 2.5 km (the fleet itself) | -12 % each, never below 40 % | the convoy's screws and wakes mask the echo: this is the "interfered by the fleet" rule, so a boat lurking at the edge of the convoy is hard to find and one outside it is not |
| destroyer faster than 15 kn | x 0.4 | its own screws deafen the set; hunters slow to 14 kn inside 1.5 km |
| boat at or below 2.5 kn | x 0.7 | a creeping boat makes less noise |

The echo is lost inside 150 m (the attacker runs over the boat on its last fix). A fix has a
+-40 m error per axis. The boat's depth is not measured.

**Depth charges** (`DEPTH_CHARGE`). Sink at 3 m/s to a setting guessed from the boat's depth
+-25 m (never shallower than 15 m). A burst within 12 m of the boat breaks it; out to 40 m it
does up to 50 % hull damage, falling off linearly, in 3D (depth counts). Damage accumulates and
is never repaired; the boat is lost at 100 %. A run drops 5 charges 1 s apart when the datum
is within 90 m; 45 s between runs; 24 charges per ship.

**Escort AI** (`ESCORT_AI`, code in `sim/escort.py`):

| state | behaviour |
| --- | --- |
| formation | hold the station relative to the merchants' centre and route, at the convoy's speed |
| alarm | a sonar fix, a lookout sighting or a torpedo hit sets the group's *datum* (where the boat is). The convoy is told (merchants within 8 km run) |
| split | the escorts nearest the datum hunt (`hunters_per_escort` = 1 hunter per 3 escorts, 1 to 2); the rest screen. A lost hunter is replaced from the screens |
| hunt | run in at 20 kn, slow to 14 kn inside 1.5 km, drop a pattern on the datum. Without a fix younger than 60 s sweep a square around the datum that widens by 1 m/s (400 m to 2.5 km) |
| screen | stand 2 km from the convoy centre toward the datum, 700 m apart, facing the threat |
| stand down | no fix or sighting for 300 s: everyone returns to formation |
| merchants | an alerted merchant runs for the point 700 m behind the nearest non-hunting escort (as seen from the threat) and stays on its far side; with no escort it just runs away (M1 rule) |

A torpedo hit gives only a rough datum (2 km back along the torpedo's track) and never replaces
a fix younger than 30 s.

**Scoring.** Only merchants count for the hunt (`SUNK ... GRT`, the end banner, mission end).
Sinking a destroyer (1 torpedo, 1,800 GRT) adds to the separate escort bonus shown as
`(+N escort)`. Destroyers never "escape". The hunt also ends when the boat is lost
(`boat_lost`).

