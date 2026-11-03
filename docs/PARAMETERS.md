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
| periscope | 7 km | low eye height; only with the scope raised |
| hydrophone | 15 km, bearing only | needs depth >= 11 m and own speed <= 4 kn |
| periscope raised / lowered | `V`, 5 s to raise (`scope_raise_time`) | lowered: nothing shows above the water (lookouts cannot see the boat at periscope depth) and the boat is blind, hydrophone only; going deep lowers it, coming back up does not raise it (#37) |
| safe depth | `max_depth x (1 - damage)`; below it the hull loses `overdepth_rate` = 0.1 % per second for every 20 m of excess (cadet 0.05 %, veteran 0.15 %) | deep is a resource that shrinks with damage: a sound boat may sit at 150 m, a boat that has taken 40 % is safe to 90 m and groans below it (#37) |

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
| periscope depth, scope lowered | never |
| deeper than 14 m | never |

Multiply by the ship type's `lookout` (destroyer 1.5) and by the world's `light` (1.0 = day;
night is a later milestone). An escort with **radar** (`RadarParams`, `veteran` only, 20 km)
finds a *surfaced* boat at once and exactly, and the group treats it as a sighting. A ship reacts only after the boat has stayed in range for
`spot_time` = 3 s; the timer runs down again when the boat drops out of range.

## Merchant AI (`MerchantAIParams`)

| parameter | value | effect |
| --- | --- | --- |
| alert duration | 600 s | keeps running this long after the last sighting, then returns to the route |
| zigzag | ±30° every 90 s | while running |
| spread | 20° between neighbours | a group fans out instead of running in a line |
| escape range | 20 km | a merchant this far from the boat (or off the map) has got away, alerted or not: the hunt area |
| panic range | 6 km | a torpedo hit alerts every merchant within this distance |
| warning delay | 90 s (cadet 120, veteran 60) | an escort's report of the boat (a fix, a sighting, radar) reaches the merchants, and they turn away, this long later: the commodore's emergency turn takes time to signal and to answer. A torpedo an escort hears does *not* warn the merchants at all (#39) |

## Destroyer escort (`SonarParams`, `SeaParams`, `DepthChargeParams`, `EscortAIParams`)

The scenario sends two destroyers (`SCENARIO.escorts`; one at `cadet`, three at `veteran`)
with the three merchants; they start on their formation stations, 1.2 km ahead of the group
and 1.5 km off either flank (a third and fourth escort take stations 3 km off the flanks).
Lookouts use the ordinary detection table (`lookout` 1.5 makes a surfaced boat visible at
9 km, a raised periscope at 1.5 km). The rules below are the hunt rework of #37 (design
record: `docs/ESCAPE_BALANCE.md`, `docs/ESCAPE_STORIES.md`).

**Active sonar** (`SONAR_ASDIC`). Each destroyer pings every 5 s. One ping has one *effective
reach*, the range at which this ship can hold this boat right now:

```
R_eff = range x f_aspect x f_speed x f_layer x f_set        (0 behind a noise shadow)
```

| factor | value | why |
| --- | --- | --- |
| `range` | 3,000 m (cadet 2,400, veteran 3,600) | a beam-on, moving boat above the layer, settled set |
| `f_aspect` | `aspect_floor + (1 - aspect_floor) x abs(sin aspect)`, floor 0.4 (cadet 0.3, veteran 0.5) | a hull broadside returns far more sound than a bow; end-on to the pinger is the classic evasion |
| `f_speed` | x 0.7 at or below 2.5 kn (`quiet_speed`, `quiet_factor`) | a creeping boat makes less noise |
| `f_layer` | x 0.5 below the thermocline (cadet 0.4, veteran 0.6) | sound bends away at the temperature layer |
| `f_set` | sprinting (over 15 kn) x 0.25; `settle_time` 20 s of nothing after slowing; rudder more than half over x 0.5 | the set hears nothing through its own screws and wake |
| noise shadows | 0 behind a friendly ship (afloat, stopped or sunk: `noise_base` 150 m + `noise_per_knot` 30 m/kn of its speed, as a sector beyond it) or behind the **cloud** a pattern leaves (`cloud_radius` 150 m for `cloud_duration` 180 s; cadet 240, veteran 120) | the convoy's screws and the boiling water after the bursts mask the sea behind them: the boat can shelter in both |

The echo comes back only inside the **cone** the set can be trained over, `arc` = 70 deg either
side of the bow (cadet 45, veteran 90; the rest is the baffles), and outside the **blind
zone** under the keel, `depth_blind_ratio` 3 x the boat's depth (cadet 4, veteran 2.5),
never less than `min_range` 150 m nor more than `blind_zone_cap` 300 m. Inside
`sure_fraction` 0.4 of `R_eff` (veteran 0.5) the echo is sure; beyond it the chance falls
to zero at `R_eff`. A fix is a random point in a ring of radius `area_base` 25 m +
`area_span` 150 m x (d / `R_eff`): a faint echo is a poor fix (175 m at the edge of the
reach, 75 m a third of the way in). The boat's depth is never measured. The HUD draws each
destroyer's cone, the escorts' fix on the boat with its ring, and `ECHO <m>`, the settled
reach of the nearest destroyer against the boat now.

**The sea** (`SEA`). Each hunt draws a thermocline between `layer_min` 40 m and `layer_max`
90 m (`layer_chance` 1.0; 0.7 at `veteran`, so some veteran hunts have none). The boat learns
where it is by crossing it (`LAYER <m>` on the depth line of the HUD).

**Tracking.** Every sonar fix, sighting or radar fix goes into a 45 s window; a least-squares
line through it gives the escorts the boat's position now and its course and speed (needs
three fixes over at least 10 s, capped at 7.6 kn). Bigger rings mean a worse track. A sighting
or radar fix is exact and says the boat is shallow. An **observed torpedo** (heard within
1,200 m, or its wake seen) gives the escorts its *track line*: the boat is somewhere along it
within the torpedo's run (5,000 m), the hunter sweeps the line outward from the target at
14 kn, and the line becomes a stale point to search around at its end. A torpedo does not
overrule a fix younger than 30 s.

**Depth charges** (`DEPTH_CHARGE`). Projectors throw a charge up to 150 m from the ship. A run
starts as soon as the predicted position of the boat (10 s ahead) is within 150 m; it is 6
charges 1 s apart, each aimed where the boat will be when that charge has sunk to its depth
(the predicted path), up to 15 m to either side (`scatter`); a pattern on an assumed flight straddles the path instead, in steps out to `blind_scatter` 60 m either side, because the guess is worth less than a fix. The pattern is set in one **depth band**:
15 to 40, 40 to 80 or 80 to 150 m (`bands`), the six charges spread over it. A sighting or
a torpedo starts the escorts in the shallow band, a sonar-only alarm in the medium one; a
pattern that does at least `confirm_damage` 10 % confirms its band, one that does less moves
the next pattern to the following band (deep after medium, shallow after deep). Each charge is
**released when the ship reaches its aim point**; if the aim points stay ahead and out of
reach for `run_max_time` 90 s the run is abandoned (the run-over release, which ends the stern
chase stalemate of #35). Charges sink at 3 m/s. A burst within 12 m of the boat breaks it; out
to 45 m it does up to 40 % hull damage, falling off linearly, in 3D (depth counts). Damage
accumulates and is never repaired; the boat is lost at 100 %. The rack reloads in
`pattern_cooldown` 120 s (cadet 150, veteran 90); 40 charges per ship.

**Torpedo evasion** (`TORPEDO_EVASION`, the `comb` strategy of the `escort_evade` slot, M3 /
#22; `cadet` keeps `none`). An escort hears a running torpedo's screws within `hear_range` =
1,200 m (a G7a's wake is also seen at its 1,500 m wake range times the ship's lookout factor
by day). If the torpedo's closest approach, with both holding course and speed, is inside
`threat_width` = 150 m and comes before the torpedo runs out, the ship reacts after
`reaction_time` = 5 s: it turns hard to the course that *combs the track*, parallel to the
torpedo's course but `comb_angle` = 30° off it toward the side of the track the ship is
already on, at full speed, until the torpedo has gone by or run out, then carries on with what
it was doing. Fired from inside about 500 m, or at a ship that does not hear it in time, a
torpedo still hits.

**Escort AI** (`ESCORT_AI`, code in `sim/escort.py`). The hunt is a cycle:

| state | behaviour |
| --- | --- |
| evading | (any state, `escort_evade = comb`) a torpedo that will pass too close is heard: comb its track at full speed until it has gone by, then resume |
| formation | hold the station relative to the merchants' centre and route, at the convoy's speed (intent `formation`, or `returning` while getting back to it) |
| alarm | a sonar fix, a sighting, a radar fix or an observed torpedo sets the group's *datum*. A fix, sighting or radar report also warns the convoy (merchants within 8 km turn away `warning_delay` later, `convoy_warned` in the log); an observed torpedo warns the escorts only (#39) |
| split | the escorts nearest the datum hunt (`hunters_per_escort` = 1 hunter per 3 escorts, 1 to 2); the rest screen. A lost hunter is replaced from the screens |
| hunting | steer for the predicted position of the boat, 20 kn, slow to 14 kn inside 1.5 km, throw a pattern from up to 150 m away while the fix is under 60 s old (`attacking` during a run) |
| datum attack | a fix older than 60 s but younger than `datum_attack_age` 180 s (cadet 120, veteran 240) is still attacked once, at the dead-reckoned position |
| blind lead | when that finds nothing, the hunter assumes the boat has run straight away from the ship that found it, from the last fix, at the type's best submerged speed (`max_track_speed`, 7.6 kn) ever since, and attacks that assumed track `blind_attacks` times (2; cadet 1, veteran 3), on a fresh rack each time. A boat that runs straight is where the assumption says; a boat that turned or slowed is not |
| sweeping | with a torpedo line as the datum: down the track from the target outward at 14 kn, pinging both sides |
| searching | the `escort_search` strategy: `sweep` runs legs *through* the datum from alternating directions so the cone covers the whole area, which widens by 1 m/s (400 m to 2.5 km); `box` (the M2 square) is kept for tests |
| screen | stand 2 km from the convoy centre toward the datum, 700 m apart, facing the threat |
| stand down | the hunt ends (`escort_stand_down` with a reason, in the log): `lost`, no echo for `lose_track_time` (300 s; cadet 180, veteran 480) counted from when the hunter started searching; `leash`, a hunter more than `hunt_leash` 10 km (cadet 6, veteran 15) from where the convoy centre was when the alarm was raised; `time`, `max_hunt_time` 30 min after the alarm (cadet 15, veteran 60); `charges`, every hunter's rack empty. Everyone returns to formation |
| merchants | an alerted merchant that is nearer the threat than the nearest non-hunting escort slips in behind it; one already behind the escort keeps running away. With no escort it just runs away (M1 rule) |

The log says when a hunter loses the echo and why (`under the keel`, `outside the cone`,
`behind merchant-2`, `behind the cloud`, `faint echo missed`, `out of reach`), what band each
pattern is set to, when the hunter assumes a flight, and why the escorts broke off.

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
| `scenario.escorts` | 1 | 2 | 3 | the number of sonar sets and depth charge racks in the water, and how tight the screen is; cones cover each other's blind arcs |
| `sonar.range` | 2,400 m | 3,000 m | 3,600 m | how far from the convoy's edge a submerged boat is safe; the aspect, speed, layer and set factors apply on top |
| `sonar.arc` | 45 deg | 70 deg | 90 deg | how much of the sea a set listens to: the narrower, the more water the boat can hide in abeam |
| `sonar.depth_blind_ratio` | 4 | 3 | 2.5 | how far out a deep boat is lost under the keel (capped at 300 m) |
| `sonar.aspect_floor` | 0.3 | 0.4 | 0.5 | what an end-on boat is worth: the veteran's "turn the stern to it" buys more at `cadet` |
| `sonar.layer_factor` | 0.4 | 0.5 | 0.6 | how much the thermocline hides |
| `sonar.sure_fraction` | 0.4 | 0.4 | 0.5 | how far out an echo is sure |
| `sonar.cloud_duration` | 240 s | 180 s | 120 s | how long a pattern's cloud hides the boat |
| `sea.layer_chance` | 1.0 | 1.0 | 0.7 | some veteran hunts have no layer |
| `radar.range` | none | none | 20 km | a surfaced boat is found far beyond the lookouts at `veteran` |
| `depth_charge.pattern_cooldown` | 150 s | 120 s | 90 s | the rack reload between runs |
| `depth_charge.damage` | 0.3 | 0.4 | 0.5 | hull damage at the edge of the damage radius: 4, 3 or 2 near bursts to lose the boat |
| `depth_charge.lethal_radius` | 12 m | 12 m | 15 m | veteran patterns are deadly a little further out |
| `escort_ai.datum_attack_age` | 120 s | 180 s | 240 s | how stale a fix the hunter still attacks |
| `escort_ai.blind_attacks` | 1 | 2 | 3 | how many attacks on the assumed straight flight |
| `escort_ai.lose_track_time` | 180 s | 300 s | 480 s | how long the search goes on without an echo |
| `escort_ai.hunt_leash` | 6 km | 10 km | 15 km | how far from the convoy a hunter will follow |
| `escort_ai.max_hunt_time` | 15 min | 30 min | 60 min | how long the escorts hunt at most |
| `submarine.overdepth_rate` | 0.05 %/s | 0.1 %/s | 0.15 %/s | per 20 m below the safe depth |
| `merchant_ai.warning_delay` | 120 s | 90 s | 60 s | how long the convoy takes to answer an escort's report of the boat |
| `torpedo.reload_time` | 90 s | 120 s | 150 s | how soon a second salvo is ready |
| `torpedo_hit.glance_chance` | 1.0 | 0.5 | 0.25 | whether a bow-on or stern-on shot (under 30° off the axis) detonates: every hit counts at cadet |
| `escort_evade` strategy | `none` | `comb` | `comb` | cadet destroyers never notice a torpedo; the others comb its track (#22) |
| other strategies | `sweep`, `zigzag` | same | same | one search and one flee behaviour so far |

`tests/test_params.py::test_escort_balance_relations_hold_at_every_level` runs the balance
relations against each level's rules, and `tests/test_difficulty.py` pins the ordering of the
numbers in the table.
