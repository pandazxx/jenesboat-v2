---
id: TC-001
title: Throttle and rudder move the submarine
issue: 7
added_in: 8
---
## Preconditions

Open the build URL in a desktop browser; wait until the HUD shows `HDG 000.0`.

## Steps

1. Hold `W` for about 3 seconds, release.
2. Hold `D` for about 2 seconds, release.

## Expected

- While `W` is held, `THR` climbs toward `+1.00` and `SPD` rises; the yellow sub moves up the
  screen (north) leaving its start position.
- While `D` is held, `HDG` increases (clockwise) and the heading line on the sub rotates right.
- Releasing `D` returns `RUD` to `+0.0` but `HDG` keeps its new value.

## Automated

`scripts/agent_web_test.py --keys W:3,D:2` (CI job "Agent smoke test") asserts the sub moved;
`tests/test_game_and_events.py::test_controls_ramp_throttle_and_steer` covers the logic.
