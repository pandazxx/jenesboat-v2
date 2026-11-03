---
id: TC-027
title: Depth charges are set in bands and move band after a pattern that did nothing
issue: 37
added_in: 38
---
## Preconditions

A hunt at `patrol`. Get sighted at periscope depth (`destroyer-N sighted us`), then go deep.

## Steps

1. Read the log line when the hunter starts its run.
2. Stay at 60 m through the first pattern; read the next run's line.
3. After a pattern that hurt you, read the following run's line.

## Expected

- `destroyer-N is making a depth charge run, charges set 15-40 m`: after a sighting the first
  pattern is shallow (after a sonar-only alarm it is `40-80 m`).
- A pattern that did under 10 % damage moves the next one to the following band (`40-80 m`,
  then `80-150 m`, then back to `15-40 m`); the bursts above or below you do little.
- A pattern that did 10 % or more keeps its band: change depth before the next run.
- The HUD's `HULL` line shows `SAFE <m>` once you are damaged.

## Automated

`tests/test_hunt_rework.py::test_a_fresh_fix_is_attacked_and_the_run_is_laid_as_the_ship_reaches_the_aim_points`,
`::test_the_depth_band_moves_on_after_a_pattern_that_did_nothing_and_stays_after_a_hit`.
