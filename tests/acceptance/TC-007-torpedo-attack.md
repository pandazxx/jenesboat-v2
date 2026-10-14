---
id: TC-007
title: F fires a torpedo along the heading; hits sink merchants and score tonnage
issue: 13
added_in: 15
---
## Preconditions

Boat at periscope depth within 2 km of an unalerted merchant, panel showing a solution.

## Steps

1. Wait for the panel to show `FIRE` in green, press `F`.
2. Watch the white dot and its track line.
3. Press `F` once more with the bow pointing at empty sea.
4. Watch `TUBES` and the message line for two minutes.

## Expected

- Step 1: message `torpedo 1 away, course NNN`; `TUBES 3/4`; a white dot leaves the bow and runs
  straight at 30 kn leaving a thin track. The merchant does not react (the G7e is wakeless).
- When the dot reaches the hull: `HIT <ship>`, then `<ship> SUNK, 4,500 GRT` (freighter, one
  hit) or only `HIT` for a tanker, which needs a second torpedo. `SUNK N GRT` on the HUD
  increases. The wreck stays as a grey X and stops. The other ships start running
  (`running: torpedo`) away from the direction the torpedo came from.
- Step 3: the torpedo runs 5 km and the message `torpedo N missed` appears.
- Step 4: `TUBES n/4  RES 8 (reload NNNs)` counts down 120 s per tube and `RES` drops by one
  when a tube is reloaded. At `DEPTH` below 20 m `F` gives `cannot fire: too deep`.

## Automated

`tests/test_weapons.py`.
