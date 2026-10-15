---
id: TC-010
title: The map shows the boat moving: km-labelled world grid, own track, position readout
issue: 14
added_in: 15
---
## Preconditions

Fresh hunt, default zoom (20 m/px), time x1.

## Steps

1. Press `W` four times (`AHEAD FLANK`) and wait until `SPD` reads about 17 kn.
2. Watch the grid labels, the `POS` and `LOG` fields under the HUD and the area behind the
   boat for a minute.
3. Press `=` three times (5 m/px, then 2 m/px) and watch again.
4. Press `4` (x8) and watch at the default zoom.

## Expected

- The grid is fixed to the world: each vertical line carries its east coordinate in km at the
  bottom, each horizontal line its north coordinate at the left, and lines with their labels
  scroll past the boat (slowly at x1 and 20 m/px: 17 kn is under half a pixel per second).
- `POS 20.00E 20.00N` (km, 10 m resolution) changes about every second at 17 kn and `LOG`
  (nautical miles run, the ship's log) counts up 0.01 nm every 2 s.
- A dotted trail of the boat's past positions grows behind it (one dot per 50 m).
- At 5 m/px and closer a fainter 200 m grid appears between the km lines and motion is obvious.
- At x8 the km lines visibly scroll even at 20 m/px.

## Automated

`tests/test_world.py::test_boat_leaves_a_track` and
`tests/test_render.py::test_close_zoom_draws_the_minor_grid_and_the_own_track`.
