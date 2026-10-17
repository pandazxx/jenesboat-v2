---
id: TC-016
title: The escort splits, merchants shelter behind the screen, the track is lost
issue: 17
added_in: 18
---
## Preconditions

Fresh hunt (`R`), the whole group in sight at periscope depth.

## Steps

1. Fire a torpedo at a merchant and watch the group after the hit.
2. Go deep and creep away from the area; keep watching at x8 for 5-6 minutes of game time.

## Expected

- After the hit the destroyers react: one hunts toward the torpedo's launch point (about 2 km
  behind the hit), the other places itself between you and the merchants.
- The surviving merchants keep running away from you, tucking in behind the screening
  destroyer; none of them ever turns toward you to reach it.
- A hunter that finds nothing sweeps a widening square around the last fix. After 5 minutes
  without a fix `escort lost the track, back to formation` appears and both destroyers go back
  to their stations beside the merchants.

## Automated

`tests/test_escort.py::test_merchants_run_for_the_screen_when_the_escort_is_alarmed`,
`test_escorts_return_to_formation_after_losing_the_track`,
`test_destroyers_keep_station_on_the_convoy`.
