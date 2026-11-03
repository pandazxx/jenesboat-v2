---
id: TC-035
title: The convoy turns away only after the escorts' signal has gone round
issue: 39
added_in: 38
---
## Preconditions

A hunt at `patrol`; a firing position 2 to 3 km on the beam of an unalerted convoy.

## Steps

1. Fire a well-aimed torpedo at a merchant (the panel says `FIRE`); lower the scope.
2. Watch the merchants until the torpedo arrives.
3. In another hunt, get pinged or sighted by a destroyer before firing; note the time of
   `ESCORT: destroyer-N pinged us` and when the merchants turn.

## Expected

- The merchants hold course and speed while the torpedo runs, even though an escort heard it
  (`destroyer-N has our torpedo's track`): the shot hits.
- After a ping or a sighting, the merchants keep going for about 90 s at `patrol` (120 s at
  `cadet`, 60 s at `veteran`), then the log says `the convoy is told by destroyer-N: ... turn
  away` and they run.
- A hit or a dud still makes the merchants within 6 km run at once, as before.

## Automated

`tests/test_hunt_rework.py::test_merchants_turn_away_only_after_the_signal_delay`,
`::test_an_aimed_shot_at_an_unalerted_convoy_hits`.
