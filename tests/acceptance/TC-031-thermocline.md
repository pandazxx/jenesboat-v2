---
id: TC-031
title: The thermocline hides a boat below it and is shown once crossed
issue: 37
added_in: 38
---
## Preconditions

A fresh hunt at `patrol` (every `patrol` hunt has a layer between 40 and 90 m).

## Steps

1. Dive to 60 m (`C`); watch the depth line and the log.
2. If no layer message came, order deeper (the layer may be below 60 m): use `C` then
   `SPACE`/`C` steps... (any order below the layer); watch for the message.
3. Found by a destroyer, compare `ECHO` above and below the layer.

## Expected

- Crossing the layer: log `thermocline: the water changes at <m> m (we are below it)`, and the
  depth line shows `LAYER <m>` from then on.
- Below the layer `ECHO` halves at `patrol`; the hunter loses the echo sooner.
- At `veteran` some hunts have no layer at all.

## Automated

`tests/test_hunt_rework.py::test_the_thermocline_is_drawn_per_hunt_and_told_once_the_boat_crosses_it`,
`tests/test_escort.py::test_effective_reach_is_the_range_scaled_by_aspect_speed_layer_and_the_set`.
