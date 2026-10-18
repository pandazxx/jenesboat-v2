---
id: TC-017
title: Merchants are the score, a destroyer is a bonus, and the hunt stays winnable
issue: 17
added_in: 18
---
## Preconditions

Fresh hunt (`R`).

## Steps

1. Read the objective message. Torpedo a destroyer (it is faster and turns tighter than a
   merchant; wait until it is close and crossing).
2. Sink the merchants one by one using what you learn about the escort's behaviour.

## Expected

- A sunk destroyer logs `destroyer-N SUNK: escort bonus 1,800 GRT`; the HUD shows
  `(+1,800 escort)` and `SUNK ... GRT` and `HUNT n/3` count only merchants.
- Sinking all destroyers does not end the hunt; the hunt ends only when the merchants are sunk or
  away, the torpedoes are gone or the boat is lost.
- Compared with M1 the group is harder to get at, but a patient submerged approach (slow, deep
  when hunted, out of the convoy's middle) still gets at least one merchant on most hunts.

## Automated

`tests/test_escort.py::test_sinking_a_destroyer_is_a_bonus_not_a_merchant_kill`,
`tests/test_hunt.py::test_escorted_hunt_is_harder_but_a_hit_is_still_normal`.
