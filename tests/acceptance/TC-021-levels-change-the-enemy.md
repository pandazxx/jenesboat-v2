---
id: TC-021
title: The levels change the escort, not the boat
issue: 21
added_in: 27
---
## Preconditions

Three fresh hunts of the same seed, one per level: `?difficulty=cadet`, no query (`patrol`),
`?difficulty=veteran` (the seed is in the HUD tag; the web build picks it at random, so use
`just sim --seed 7 --difficulty <level> --seconds 1` to compare the same hunt, or just count).

## Steps

1. Surface, go to AHEAD FLANK toward the intel bearing at x8 until the group is in sight,
   then count the destroyers (red hulls) in each hunt.
2. At `veteran`, approach submerged to within 3 km of the group's edge at AHEAD SLOW and
   note when `ESCORT: destroyer-N pinged us` appears; do the same at `cadet`.
3. Fire one torpedo at anything and watch the `reload` countdown in the TUBES line.
4. At `veteran`, once hunted, go deep, stop, and wait for `escort lost the track, back to
   formation`; compare the wait with `cadet`.

## Expected

- `cadet` has 1 destroyer, `patrol` 2, `veteran` 3 (the third starts 3 km off a flank).
- The `veteran` escort pings the boat from further out than the `cadet` one (3.6 km vs 2.4 km
  base range, both reduced by the fleet's noise).
- Reload is 90 s at `cadet`, 120 s at `patrol`, 150 s at `veteran`; the boat's speed, depths
  and battery are the same at every level.
- The `veteran` escort keeps sweeping about 8 minutes after the last fix, the `cadet` one
  about 3.

## Automated

`tests/test_difficulty.py::test_the_scenario_follows_the_level`,
`tests/test_difficulty.py::test_the_level_changes_what_the_escort_hears_and_how_long_it_remembers`,
`tests/test_params.py::test_escort_balance_relations_hold_at_every_level`.
