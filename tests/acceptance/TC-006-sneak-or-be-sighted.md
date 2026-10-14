---
id: TC-006
title: Merchants run from a sighted boat; a slow periscope-depth boat stays unseen
issue: 12
added_in: 15
---
## Preconditions

Visual contact with the group, boat surfaced, more than 7 km away (`RNG` above 7.0).

## Steps

1. Note the red circle around the boat: the distance at which merchant lookouts see it (about
   6 km surfaced at 40 m/px it is 150 px across).
2. Stay surfaced and steer straight at the group at full throttle until the nearest ship is
   inside the red circle (`RNG` below 6.0 km).
3. Press `R` for a new hunt and repeat the approach, but press `Space` (periscope depth) when
   `RNG` is about 7 km and press `S` until `THR +0.20` (about 3 kn or less).
4. Let the group pass about 1.5 km away.

## Expected

- Step 2: within a few seconds the message `<ships> running: we were sighted` appears, the
  panel shows `RUNNING` in orange, the ships turn away from the boat, speed up to about 11 kn
  and zigzag; the nearest ship fans out from the others. A submerged boat (7.6 kn) cannot
  catch them.
- Step 3: at periscope depth the red circle shrinks to about 1 km; it grows again if `SPD`
  goes above 3 kn.
- Step 4: no `running` message, the ships keep course and 8 kn, `AOB` sweeps through 90 as
  they pass.

## Automated

`tests/test_world.py` (spot timer, periscope range vs speed, flee behaviour) and
`tests/test_hunt.py::test_a_surfaced_approach_is_spotted_and_the_group_runs`.
