---
id: TC-026
title: A merchant's screws or the water after a pattern hide the boat from the sonar
issue: 37
added_in: 38
---
## Preconditions

A hunt at `patrol`, found by a destroyer, at 60 m.

## Steps

1. Let the hunter make a run; watch the pattern burst and the grey disc that appears where the
   charges went off.
2. Creep so that the disc lies between you and the hunter as it comes round.
3. In another hunt, inside the convoy, keep a freighter between you and the pinging destroyer.

## Expected

- The grey disc (disturbed water) stays for about three minutes at `patrol` (longer at
  `cadet`, shorter at `veteran`), then fades.
- While the disc or a merchant is between you and a destroyer, that destroyer gets no echo:
  the log says `destroyer-N lost the echo: boat behind the cloud` / `behind merchant-2`, and
  the fix ring stops updating.
- A merchant casts a wider shadow when it runs (its noise grows with speed), and still a
  shadow when stopped or sunk.

## Automated

`tests/test_escort.py::test_a_friendly_ship_or_a_cloud_between_casts_a_noise_shadow`,
`tests/test_hunt_rework.py::test_a_pattern_leaves_a_cloud_that_hides_the_boat_and_then_clears`.
