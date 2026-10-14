---
id: TC-002
title: Space dives to periscope depth and surfaces again; submerged speed is lower
issue: 7
added_in: 8
---
## Preconditions

Build open, sub at full throttle (`THR +1.00`) and `SPD` steady near 17 kn.

## Steps

1. Press `Space` once.
2. Wait about 15 seconds.
3. Press `Space` again and wait about 15 seconds.

## Expected

- After step 1 the HUD shows `DEPTH ... -> 12.0 m`, depth increases about 1 m per second, the
  sub becomes an outline circle and the label reads `SUBMERGED`.
- At 12 m, `SPD` settles near 7 kn.
- After step 3 the sub returns to 0 m, is drawn filled, reads `SURFACED` and `SPD` climbs back
  toward 17 kn.

## Automated

`tests/test_submarine.py` covers the depth and speed model.
