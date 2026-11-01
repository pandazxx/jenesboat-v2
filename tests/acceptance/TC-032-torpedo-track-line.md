---
id: TC-032
title: An observed torpedo gives the escorts its track, which they sweep
issue: 37
added_in: 38
---
## Preconditions

A hunt at `patrol`: an attack position within 3 km of the convoy, undetected.

## Steps

1. Fire a torpedo at a merchant from 2 to 3 km; lower the scope and turn 90° off the shot.
2. Watch the map and the log as the torpedo passes within 1.2 km of a destroyer.

## Expected

- `destroyer-N has our torpedo's track: the escorts will sweep it`; an orange line appears
  along the torpedo's track back from where it was heard, 5 km long (the torpedo's run).
- The hunter runs down that line toward you at 14 kn (`destroyer-N sweeps the torpedo track`),
  the screen stands toward the line and the merchants turn away from it.
- A boat that has left the line is not found by the sweep unless its sonar picks you up; at the
  far end the hunter searches around it.

## Automated

`tests/test_hunt_rework.py::test_an_observed_torpedo_gives_the_escorts_its_track_and_the_hunter_sweeps_it`.
