---
id: TC-001
title: Throttle and rudder move the submarine
issue: 7
added_in: 8
---
## Preconditions

Open the build URL in a desktop browser; wait until the HUD shows `HDG 000.0`.

## Steps

1. Press `W` four times.
2. Hold `D` for about 1 second, release.
3. Press `Q`.

## Expected

- Each `W` press moves the telegraph one position (`AHEAD SLOW`, `AHEAD HALF`, `AHEAD FULL`,
  `AHEAD FLANK`), `SPD` rises toward 17.7 kn and the yellow sub moves up the screen (north);
  `S` steps back down through `STOP` to `ASTERN HALF` / `ASTERN FULL`.
- While `D` is held the HUD reads `RUDDER NN STBD` growing to 35 in two seconds, `HDG`
  increases (clockwise) and the heading line on the sub rotates right. Releasing `D` keeps the
  rudder where it was and the boat keeps turning.
- `Q` reads `RUDDER AMIDSHIPS` and the turn stops; `HDG` keeps its new value.

## Automated

`scripts/agent_web_test.py --keys W:0.3,W:0.3,W:0.3,W:0.3,D:2` (CI job "Agent smoke test")
asserts the sub moved; `tests/test_game_and_events.py::test_telegraph_steps_and_rudder_holds`
covers the logic. (Changed in M1, PR #15: telegraph and holding rudder.)
