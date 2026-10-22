---
id: TC-023
title: A torpedo arriving bow-on or stern-on is a glancing blow; the panel warns before firing
issue: 22
added_in: 28
---
## Preconditions

A fresh hunt; a merchant in sight and selected (`T`) at periscope depth.

## Steps

1. Manoeuvre so the selected ship is coming nearly straight at the boat or going nearly
   straight away (the panel's `AOB` near 0 or 180) and read the solution line.
2. Turn so the ship will cross the heading from the side (`AOB` around 90) and read it again.
3. Fire a down-the-throat shot at a ship (a destroyer at `cadet`, where it does not dodge, is
   the easy case) and watch the log; repeat a few times across hunts.
4. Fire a beam shot at a merchant.

## Expected

- The solution line shows the track angle (`trk 12`) and reads `GLANCE` in orange instead of
  `FIRE` while the angle is under 30°; from the side it shows `trk 80`-`90` and `FIRE` in green.
- A bow-on or stern-on torpedo that reaches the hull sometimes logs
  `torpedo N glanced off <ship> (<angle> deg off its axis): no detonation`: the torpedo is
  spent, the ship is undamaged, and the group is alerted all the same (`running: torpedo`).
  At `patrol` about half detonate, at `veteran` a quarter, at `cadet` all of them.
- A beam shot always detonates (`HIT <ship>`).

## Automated

`tests/test_evasion.py::test_a_shot_from_dead_ahead_can_glance_off_and_still_raises_the_alarm`,
`::test_a_beam_shot_always_detonates`, `::test_glance_chance_one_means_every_hit_counts_and_chance_is_seeded`,
`::test_the_solution_carries_the_track_angle`, `::test_levels_select_the_strategy_and_the_glance_chance`.
