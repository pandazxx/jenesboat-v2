---
id: TC-028
title: A hunter that has lost you attacks the dead-reckoned position, then an assumed flight, then searches and gives up
issue: 37
added_in: 38
---
## Preconditions

A hunt at `patrol`. Found by sonar at 60 m; the hunter has you (`echo on us` in the contact
panel when it is the target).

## Steps

1. Turn your stern to the hunter, ring AHEAD SLOW and go to 90 m (below the layer if the depth
   line shows `LAYER` shallower than that). Watch the log and the contact panel.
2. Keep creeping on a course 60° off the hunter's heading. Wait.
3. In another hunt, run straight away from the hunter at flank instead.

## Expected

- The hunter loses the echo (log says why); it still attacks where it reckons you are (one run,
  then `destroyer-N lost us and assumes we ran off on <course>`), then one or two runs `on a
  guess` along that course, then `destroyer-N is searching` with the contact panel showing
  `SEARCHING  no echo`; after about five minutes of search `escort lost the track, back to
  formation`.
- Creeping off the assumed course, the guessed patterns fall away from you; running straight
  away at flank, they fall on you.
- A hunt also ends `escort will not leave the convoy any further` (the leash), `has hunted
  long enough` (30 min at `patrol`) or `is out of depth charges`.

## Automated

`tests/test_hunt_rework.py::test_a_stale_fix_gets_one_datum_attack_then_a_blind_lead_along_the_approach_course`,
`::test_after_the_blind_attacks_the_hunter_searches_and_the_track_is_lost`,
`::test_the_hunt_ends_on_the_leash_and_on_the_clock`, `::test_empty_racks_end_the_hunt`.
