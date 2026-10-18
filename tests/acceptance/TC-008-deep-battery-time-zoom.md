---
id: TC-008
title: Deep order, battery, time compression and zoom
issue: 11
added_in: 15
---
## Preconditions

Fresh hunt, boat surfaced, `BATT 100%`.

## Steps

1. Press `C`. Wait until `DEPTH 60.0 m`.
2. Press `W` four times (`AHEAD FLANK`) for one minute at x8 (press `4`).
3. Press `Space` once, then once more after reaching 12 m.
4. Press `1` to `6` in turn and watch the `t=` counter at the bottom right.
5. Press `-` and `=` several times.

## Expected

- Step 1: `DEPTH ... -> 60.0 m`, band `DEEP`; the red visibility circle disappears below 14 m;
  the panel only shows hydrophone contacts (if any are within 15 km); `F` says `too deep`.
- Step 2: `SPD` tops out near 7.6 kn and `BATT` falls visibly (full speed drains the battery in
  about 1.5 h of game time; at x8 a few percent per real minute). On the surface it climbs back.
- Step 3: the first `Space` from deep goes to `12.0 m` (`PERISCOPE`), the second to the surface.
- Step 4: `TIME x1`, `x2`, `x4`, `x8`, `x16`, `x32` (keys `1`-`6`) and the clock runs
  correspondingly faster; the boat still
  steers and dives normally.
- Step 5: five zoom levels from 2 to 40 m/px; the `1 km` scale bar changes length; the boat
  stays centred.

## Automated

`tests/test_submarine.py` (depth bands, battery) and
`tests/test_game_and_events.py` (time compression, zoom).
