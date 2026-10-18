---
id: TC-019
title: Every order can be given with the on-screen buttons on a touch screen
issue: 19
added_in: 20
---
## Preconditions

TC-018 passed: the game runs on a phone held sideways. The ship cluster (bottom left) has
`AHEAD` over `ASTERN` in a column and `PORT` / `MID` / `STBD` in a row along the bottom.

## Steps

1. Tap `AHEAD` four times, then `ASTERN` once.
2. Hold `STBD` for about two seconds, let go, wait, then tap `MID`. Hold `PORT` and, while
   holding it, tap `AHEAD` with the other hand.
3. Tap `DIVE`, wait for periscope depth, tap `DEEP`, then `DIVE` again.
4. Tap `x1` six times, reading the HUD after each tap. Tap `-` and `+`.
5. Tap `PAUSE`, then the same button again.
6. Once a ship is in sight tap `TGT` and `FIRE`.
7. Tap `NEW`; tap `NO`. Tap `NEW` again; tap `YES`.

## Expected

- Step 1: the telegraph on the HUD steps `STOP -> AHEAD SLOW -> HALF -> FULL -> FLANK`, then
  back to `AHEAD FULL`; the boat moves. Every tap registers once (no double steps).
- Step 2: the rudder reading grows to `35 STBD` while the button is held, stays there when
  released, the boat keeps turning, and `MID` returns it to `AMIDSHIPS`. Holding `PORT` and
  tapping `AHEAD` at the same time does both (two fingers).
- Step 3: `DEPTH` goes to periscope depth (12 m), then 60 m, then back to periscope depth.
- Step 4: the button and the HUD read `x2`, `x4`, `x8`, `x16`, `x32`, `x1` in turn; the map
  zooms out and in.
- Step 5: the HUD shows `TIME PAUSED` and the banner `PAUSED - RUN to resume`, the button
  reads `RUN`; tapping it resumes.
- Step 6: the target ring moves to the next contact, a torpedo runs.
- Step 7: the prompt `Abandon this hunt and start a new one? YES / NO` appears with only the
  `YES` / `NO` buttons; `NO` returns to the hunt, `YES` starts a new one (new seed in the
  build tag).
- Throughout: a held button is highlighted, the page never scrolls, zooms or selects text,
  and the keyboard help line is not shown.

## Automated

CI `--mobile --taps "W,W,W,W,D:2,SPACE"`: `touch_inputs` lists `W` x4 and `SPACE`, the boat
moved and the rudder is to starboard in `last_state`. Protocol:
`tests/test_touch.py`, key merging: `tests/test_app.py::test_read_controls_merges_keyboard_and_touch_and_logs_both`.
