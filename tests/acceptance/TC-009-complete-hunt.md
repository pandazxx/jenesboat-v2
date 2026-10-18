---
id: TC-009
title: A complete hunt: spot, predict, ambush, sneak, attack, mission end
issue: 9
added_in: 15
---
## Preconditions

Fresh hunt (`R`), x8 time (`4`), zoomed out (`-` twice).

## Steps

1. Read the BdU report, run surfaced toward the reported position until the group is sighted.
2. Read `CRS` and the dashed projected route; run surfaced to a point 1-2 km beside the route,
   ahead of the group, before the ships come within about 7 km (`RNG`).
3. Stop (`S` to `STOP`), `Space` to periscope depth, point the bow across the route (`A`/`D`,
   then `Q`).
4. Press `1` (x1) when the nearest ship is within 3 km; wait for `FIRE` on the panel and press
   `F`. Fire at the others as solutions appear.
5. Play on until the banner appears.

## Expected

- The group is sighted at about 12 km, the merchants hold course and 8 kn while the boat is
  unseen, and at least one torpedo hits if fired on a green `FIRE` solution.
- After the first hit the survivors run and zigzag away; a submerged boat cannot catch them,
  a surfaced one is sighted at 6 km and they keep running.
- The first message of the hunt states the objective; HUD line 3 keeps the score as
  `HUNT n/3 sunk, n away`.
- When every merchant is sunk or has got away (more than 20 km from the boat or off the map,
  whether or not it ever saw you), or the torpedoes are gone, the banner
  `HUNT OVER (<reason>): N sunk, N GRT, N got away - R for a new hunt` appears and `R` starts
  a new, different hunt (the seed at the bottom right changes). Pressing `R` mid-hunt first
  asks `Y / R: yes  N: no` and freezes the world until you answer.
- Challenge check (acceptance criterion): with the approach above a hit is normal; being seen
  during the approach means losing the group.

## Automated

`tests/test_hunt.py::test_scripted_ambush_scores_a_hit` plays this with a scripted skipper on
six seeds.
