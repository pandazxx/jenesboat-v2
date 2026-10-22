# Parameter sheet

Every tunable of the simulation lives in `src/jenesboat_v2/sim/params.py`. This page explains
the values. Units in the sim are metres, seconds and m/s; headings and bearings are degrees
clockwise from north. The HUD converts to knots and kilometres. `tests/test_params.py` checks
the relations that the game balance depends on (e.g. "a submerged boat cannot catch a
fleeing merchant"), at every difficulty level.

The values below are the base sheet, which is also the `patrol` level. A hunt runs on a
`Rules` bundle of these blocks (`world.rules`); a difficulty level swaps whole blocks for
copies with a few numbers changed, see "Difficulty levels" at the end and `docs/DIFFICULTY.md`.

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

**Attack angle** (`TORPEDO_HIT`, M3 / #22). The *track angle* is how far off the target's axis
the torpedo meets it: 90° is a beam shot, 0° bow-on or stern-on. Early-war contact pistols
failed at grazing angles, so a torpedo arriving at less than `glance_angle` = 30° off the axis
is a glancing blow: it detonates with probability `glance_chance` (0.5 on the base sheet; 1.0 at
`cadet`, 0.25 at `veteran`), otherwise it glances off (`glance` event, no damage, the torpedo
is spent). Either way the ship and its group are alerted as by a hit. The fire-control panel
shows the track angle (`trk 85`) and says `GLANCE` instead of `FIRE` for such a shot. A
shot down the throat of a charging destroyer is therefore a coin toss at best, and the
destroyer is dodging it (below).

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

The scenario sends two destroyers (`SCENARIO.escorts`; one at `cadet`, three at `veteran`)
with the three merchants; they start on their formation stations, 1.2 km ahead of the group
and 1.5 km off either flank (a third and fourth escort take stations 3 km off the flanks).
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

**Tracking.** Every sonar fix or sighting goes into a 45 s window; a least-squares line through
it gives the escorts the boat's position now (the +-40 m noise of single fixes averages out)
and its course and speed (needs three fixes over at least 10 s, capped at 7.6 kn). A torpedo hit
gives a rough position and no course. The prediction is carried at most 90 s past the last fix.

**Depth charges** (`DEPTH_CHARGE`). Projectors throw a charge up to 150 m from the ship, so a
destroyer does not have to cross the boat's path: a run starts as soon as the predicted
position of the boat (10 s ahead, about how long the first charge takes to sink) is within
150 m, and hunters steer for the predicted position rather than the last fix. A run is 6
charges 1 s apart. Each is aimed where the boat will be when that charge has sunk to its depth
(the predicted path), up to 15 m to either side of it, and set deeper than the one before, in
layers from 25 m above to 25 m below the estimated depth (never shallower than 15 m).
A charge whose aim point is beyond 150 m is not thrown. Charges sink at 3 m/s. A burst within
12 m of the boat breaks it; out to 45 m it does up to 40 % hull damage, falling off linearly,
in 3D (depth counts). Damage accumulates and is never repaired; the boat is lost at 100 %.
45 s between runs; 40 charges per ship. Rough odds against a boat that holds a steady course or
sits still for about 3 minutes after being found: half are lost when deep, all at periscope
depth. Circling does not help (the prediction stays on the circle's area); what helps is
leaving the area quietly and changing course, so the track is lost.

**Torpedo evasion** (`TORPEDO_EVASION`, the `comb` strategy of the `escort_evade` slot, M3 /
#22; `cadet` keeps `none`). An escort hears a running torpedo's screws within `hear_range` =
1,200 m (a G7a's wake is also seen at its 1,500 m wake range times the ship's lookout factor
by day). If the torpedo's closest approach, with both holding course and speed, is inside
`threat_width` = 150 m and comes before the torpedo runs out, the ship reacts after
`reaction_time` = 5 s: it turns hard to the course that *combs the track*, parallel to the
torpedo's course but `comb_angle` = 30° off it toward the side of the track the ship is
already on (running with the torpedo or toward it, whichever is the smaller turn), at full
speed, until the torpedo has gone by or run out, then carries on with what it was doing.
A destroyer charging the boat at 20 kn and hearing a G7e at 1.2 km has about 45 s: enough
to open 100 m or more, and a 10 m beam needs only 7. Fired from inside about 500 m, or at a
ship that does not hear it in time, a torpedo still hits.

**Escort AI** (`ESCORT_AI`, code in `sim/escort.py`):

| state | behaviour |
| --- | --- |
| evading | (any state, `escort_evade = comb`) a torpedo that will pass too close is heard: comb its track at full speed until it has gone by, then resume |
| formation | hold the station relative to the merchants' centre and route, at the convoy's speed |
| alarm | a sonar fix, a lookout sighting or a torpedo hit sets the group's *datum* (where the boat is). The convoy is told (merchants within 8 km run) |
| split | the escorts nearest the datum hunt (`hunters_per_escort` = 1 hunter per 3 escorts, 1 to 2); the rest screen. A lost hunter is replaced from the screens |
| hunt | steer for the predicted position of the boat, 20 kn, slow to 14 kn inside 1.5 km, throw a pattern from up to 150 m away. Without a fix younger than 60 s run the `escort_search` strategy: `box` sweeps a square around the datum that widens by 1 m/s (400 m to 2.5 km) |
| screen | stand 2 km from the convoy centre toward the datum, 700 m apart, facing the threat |
| stand down | no fix or sighting for 300 s: everyone returns to formation |
| merchants | an alerted merchant that is nearer the threat than the nearest non-hunting escort slips in behind it (the point 700 m behind it, never steering more than 90° from directly away from the boat); one already behind the escort keeps running away. With no escort it just runs away (M1 rule) |

A torpedo hit gives only a rough datum (2 km back along the torpedo's track) and never replaces
a fix younger than 30 s.

**Scoring.** Only merchants count for the hunt (`SUNK ... GRT`, the end banner, mission end).
Sinking a destroyer (1 torpedo, 1,800 GRT) adds to the separate escort bonus shown as
`(+N escort)`. Destroyers never "escape". The hunt also ends when the boat is lost
(`boat_lost`).


## Difficulty levels (`Rules`, `Strategies`, `Level`, `LEVELS`)

A level (`docs/DIFFICULTY.md`) names the strategy for each AI slot and replaces whole
parameter blocks. `patrol` is the base sheet above and the default; the player's boat is the
same at every level except for the torpedo reload time, so the difficulty is in the enemy.

| block . value | `cadet` | `patrol` | `veteran` | why |
| --- | --- | --- | --- | --- |
| `scenario.escorts` | 1 | 2 | 3 | the number of sonar sets and depth charge racks in the water, and how tight the screen is |
| `sonar.range` | 2,400 m | 3,000 m | 3,600 m | how far from the convoy's edge a submerged boat is safe; the fleet-noise and own-speed factors apply on top |
| `escort_ai.lose_track_time` | 180 s | 300 s | 480 s | how long escorts keep sweeping after the last fix before they go back to the convoy: the "wait it out deep" tactic gets cheaper or dearer |
| `depth_charge.damage` | 0.3 | 0.4 | 0.5 | hull damage at the edge of the damage radius: 4, 3 or 2 near bursts to lose the boat |
| `depth_charge.lethal_radius` | 12 m | 12 m | 15 m | veteran patterns are deadly a little further out |
| `torpedo.reload_time` | 90 s | 120 s | 150 s | the only change to the boat: how soon a second salvo is ready |
| `torpedo_hit.glance_chance` | 1.0 | 0.5 | 0.25 | whether a bow-on or stern-on shot (under 30° off the axis) detonates: every hit counts at cadet |
| `escort_evade` strategy | `none` | `comb` | `comb` | cadet destroyers never notice a torpedo; the others comb its track (#22) |
| other strategies | `box`, `zigzag` | same | same | one search and one flee behaviour so far |

`tests/test_params.py::test_escort_balance_relations_hold_at_every_level` runs the balance
relations against each level's rules, and `tests/test_difficulty.py` pins the ordering of the
numbers in the table.
