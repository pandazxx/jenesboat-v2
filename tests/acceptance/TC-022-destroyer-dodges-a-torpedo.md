---
id: TC-022
title: A charging destroyer hears a torpedo and combs its track
issue: 22
added_in: 28
---
## Preconditions

A fresh hunt at the default level (`patrol`) or `?difficulty=veteran`; a periscope-depth
approach until a destroyer has the boat (`ESCORT: destroyer-N pinged us` / `sighted us`) and
turns toward it. The same shot at `?difficulty=cadet` for comparison.

## Steps

1. Stay at periscope depth, stop, and turn so the heading points straight at the destroyer
   coming at you (the contact panel shows `AOB 0` or near it). Select it with `T`.
2. When it is 1.5 to 2 km away, fire (`F`) along the heading.
3. Watch the destroyer and the message log until the torpedo is gone, then do the same at
   `cadet`.

## Expected

- At `patrol`/`veteran`: within a few seconds of the torpedo coming inside about 1.2 km the log
  says `destroyer-N heard torpedo M and turns to comb its track`; the destroyer heels hard to
  one side at full speed and the torpedo runs past it (`torpedo M missed`). Once it has
  passed, the destroyer swings back onto the boat and resumes the attack.
- At `cadet` the destroyer holds its course and the torpedo hits (or glances, see TC-023).
- A torpedo fired from inside about 500 m, before it has time to turn, still hits.

## Automated

`tests/test_evasion.py::test_a_combing_destroyer_hears_the_torpedo_and_dodges_it`,
`::test_without_the_strategy_the_down_the_throat_shot_is_a_sure_hit`,
`::test_the_helm_answers_only_after_the_reaction_time`,
`::test_after_the_torpedo_has_passed_the_destroyer_goes_back_to_its_business`.
