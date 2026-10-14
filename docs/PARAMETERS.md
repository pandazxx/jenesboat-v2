# Parameter sheet

Every tunable of the simulation lives in `src/jenesboat_v2/sim/params.py`. This page explains
the values. Units in the sim are metres, seconds and m/s; headings and bearings are degrees
clockwise from north. The HUD converts to knots and kilometres. `tests/test_params.py` checks
the relations that the game balance depends on (e.g. "a submerged boat cannot catch a
fleeing merchant").

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
| destroyer | 32 kn (cruise 12) | 0.50 | 250 m | 6.0 | 100 x 10 m | out of scope until M2 |

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
| escape range | 20 km | an alerted merchant this far from the boat has got away |
| panic range | 6 km | a torpedo hit alerts every merchant within this distance |
