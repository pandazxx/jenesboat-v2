---
id: TC-029
title: The periscope is raised and lowered by order; lowered, the boat is invisible but blind
issue: 37
added_in: 38
---
## Preconditions

A fresh hunt. Dive to periscope depth (`SPACE`) near the convoy.

## Steps

1. Read `SCOPE UP` in the status column; press `V` (touch `SCOPE`).
2. Read the status and the map; press `V` again and count the seconds.
3. Go deep (`C`), then come back to periscope depth (`SPACE`).

## Expected

- `V` lowers the scope at once: `SCOPE DOWN`, log `periscope down`; every visual contact is
  lost (hydrophone bearings stay); the red "how far lookouts can see you" ring disappears, and
  destroyers 1 km away do not sight you.
- `V` again: `SCOPE RISING` for about 5 s, then `SCOPE UP`, contacts return.
- Going deep lowers the scope; coming back up leaves it `DOWN` until you order it up.
- Surfaced the line reads `SURFACED`.

## Automated

`tests/test_hunt_rework.py::test_the_periscope_is_lowered_by_going_deep_and_raised_only_by_order`,
`::test_the_scope_control_and_the_new_messages`.
