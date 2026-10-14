---
id: TC-005
title: The target's projected route and the torpedo aiming helper show where to fire
issue: 14
added_in: 15
---
## Preconditions

A visual contact on the panel (`TGT ...`), boat surfaced or at periscope depth, `TUBES` not
empty.

## Steps

1. Press `=` until the target and the boat both fit on screen (10 or 5 m/px).
2. Turn the boat (`A`/`D`, needs some speed) so that the faint yellow line from the bow crosses
   the dashed line running ahead of the target.
3. Stop turning and watch the markers at the crossing.

## Expected

- A dashed grey line runs ahead of the target along its course: its projected route.
- A faint yellow line runs 5 km from the bow along the boat's heading: where a torpedo would go.
- Where they cross, a small circle marks the crossing and a dot marks where the target will be
  when a torpedo fired now gets there. The panel's last line reads
  `run N.N km  NN s  lead +NNN m  wait` while the dot is short of the circle, `late` when it
  is past, and turns green with `FIRE` when the dot is on the circle (within half a ship length).
- If the lines do not cross within 5 km ahead, the panel reads
  `no solution: tracks do not cross in range` and no markers are drawn.

## Automated

`tests/test_weapons.py::test_solution_leads_a_crossing_target` and
`test_zero_error_solution_actually_hits`.
