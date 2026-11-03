---
id: TC-033
title: At veteran a surfaced boat is found by radar far beyond the lookouts
issue: 37
added_in: 38
---
## Preconditions

A fresh hunt with `?difficulty=veteran`; the convoy about 14 km away at the start.

## Steps

1. Run in on the surface toward the convoy.
2. Note the range when the alarm comes; dive.
3. Repeat at `patrol`.

## Expected

- At `veteran`, as soon as a destroyer is within 20 km the log says `ESCORT: destroyer-N has us
  on radar` and the merchants run (`radar has us`); the escorts' fix is exact (no ring) and the
  first pattern will be set shallow.
- Submerged (even at periscope depth) radar sees nothing.
- At `patrol` and `cadet` there is no radar: a surfaced boat is sighted at about 9 km.

## Automated

`tests/test_hunt_rework.py::test_radar_finds_a_surfaced_boat_at_veteran_and_is_handled_like_a_sighting`.
