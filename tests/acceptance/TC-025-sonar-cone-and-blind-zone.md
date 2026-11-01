---
id: TC-025
title: A destroyer hears only inside its sonar cone and outside the blind zone under its keel
issue: 37
added_in: 38
---
## Preconditions

A fresh hunt at `patrol`, zoomed in (`=`) once a destroyer is in sight. Legend on.

## Steps

1. Note the faint red cone drawn from each destroyer's bow (the arc its sonar covers).
2. Submerged at 30 m, place the boat abeam of a destroyer, outside the cone, within 1 km, and
   wait a minute.
3. Then let it come at you until it is right overhead; watch the log.

## Expected

- The cone is drawn for every destroyer you hold by sight or hydrophone, out to the sonar's
  range, 70° either side of the bow at `patrol` (45° at `cadet`, 90° at `veteran`).
- Abeam, outside the cone, you are not pinged; as the destroyer turns and its cone sweeps over
  you the ping comes.
- When it is within about 90 m (3 x your depth, at least 150 m, at most 300 m) the log says
  `destroyer-N lost the echo: boat under the keel`; after it has passed, `boat in the baffles`
  or `boat outside the sonar cone` until it has turned round.

## Automated

`tests/test_escort.py::test_the_sonar_hears_only_inside_its_cone_and_outside_the_blind_zone`.
