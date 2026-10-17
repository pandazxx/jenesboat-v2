---
id: TC-015
title: Destroyers ping with sonar and depth-charge a boat they have found
issue: 17
added_in: 18
---
## Preconditions

Fresh hunt (`R`). Two destroyers (red-orange boxes when seen) travel with the three merchants.
Zoomed out (`-`), x4 time (`3`) while closing.

## Steps

1. Approach the group submerged at periscope depth, stay within 1-2 km of a destroyer but
   outside the middle of the convoy; stop (`STOP`).
2. Wait. Watch the message log.
3. Circle the boat in a tight circle at AHEAD SLOW for a few minutes (the hunter must still
   attack even though it never crosses your path).
4. Go deep (`C`) and creep away (AHEAD SLOW) while the hunter is still running in.

## Expected

- When a destroyer pings the boat the log shows `ESCORT: destroyer-N pinged us` (or `sighted
  us` if seen on the surface) and `escort splits: destroyer-A hunting, destroyer-B screening`.
- The hunter turns toward you, slows to about 14 kn near the boat and the log shows
  `destroyer-A is making a depth charge run`; a pattern of up to 6 orange dots (charges) falls around where you are heading (the hunter
  predicts your course and need not cross your path, so circling does not make you safe), set at
  different depths, and a burst within
  about 40 m prints `DEPTH CHARGE close!` and `hull damage N%` (also in HUD line 1b).
- Creeping away quietly and deep reduces how often it is found; the damage is never repaired;
  enough damage ends the hunt with `HUNT OVER (the boat was sunk)`.
- A boat inside the convoy is much harder to find than one outside it (the fleet's own noise
  masks the sonar).

## Automated

`tests/test_escort.py::test_sonar_contact_splits_the_escort_into_hunter_and_screen`,
`test_hunter_runs_in_and_drops_a_pattern_on_a_boat_that_stays_put`,
`test_a_burst_inside_the_lethal_radius_sinks_the_boat`,
`test_sonar_reaches_further_than_lookouts_in_a_clear_sea_but_the_fleet_drowns_it`.
