---
id: TC-012
title: P pauses the game and resumes it
issue: 14
added_in: 15
---
## Preconditions

A hunt under way at `AHEAD FLANK`, time x8.

## Steps

1. Press `P`.
2. Press `-`, `L`, hold `D` for a second, press `S` twice.
3. Press `P` again.

## Expected

- After step 1 the HUD reads `TIME PAUSED`, a `PAUSED - P to resume` banner sits mid screen,
  the `t=` clock, `POS`, `LOG` and every ship stop, and no messages arrive.
- During step 2 the map still zooms, the legend toggles, the rudder angle and the telegraph
  order change on the HUD, but the boat does not move or turn.
- After step 3 the clock runs again at the same x8, and the orders given while paused take
  effect (the boat turns and slows).
- `R` while paused starts a new hunt that is running.

## Automated

`tests/test_game_and_events.py::test_pause_freezes_the_world_but_not_the_view` and
`tests/test_cli.py::test_headless_pause_order_stops_the_clock`.
