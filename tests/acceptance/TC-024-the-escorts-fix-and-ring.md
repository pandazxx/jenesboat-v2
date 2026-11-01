---
id: TC-024
title: The map shows the escorts' fix on the boat and how sure they are
issue: 37
added_in: 38
---
## Preconditions

A fresh hunt at `patrol`. Approach the convoy at periscope depth until a destroyer pings you
(`ESCORT: destroyer-N pinged us`). Legend on (`L` / `?`) to read the symbols.

## Steps

1. Watch the orange dot and ring that appear near your boat after the ping.
2. Hold course and speed for a minute; then turn your stern toward the destroyer and ring
   AHEAD SLOW.
3. Watch the ring on the next pings, and the `ECHO` line in the status column.

## Expected

- After the ping an orange dot (where the escorts think you are) with a ring around it (how
  sure they are) sits near the boat; the dot is not exactly on the boat.
- Each ping moves the dot and resets the ring; the ring is small (tens of metres) when the
  destroyer is close and beam-on to you, larger (over 100 m) when it is far or you are end-on
  and creeping; `ECHO` falls when you turn end-on, slow down or get under the layer.
- With no ping for a while the dot and ring fade; when the destroyer sees your periscope (or
  radar has you at `veteran`) the ring disappears: the fix is exact, one indicator only.

## Automated

`tests/test_escort.py::test_a_fix_is_a_point_in_a_ring_that_grows_with_the_faintness_of_the_echo`,
`tests/test_hunt_rework.py::test_the_snapshot_carries_what_the_hud_draws`.
