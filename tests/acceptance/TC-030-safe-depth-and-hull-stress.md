---
id: TC-030
title: Below the safe depth the hull groans and takes damage; the safe depth shrinks with damage
issue: 37
added_in: 38
---
## Preconditions

A hunt where a pattern has hurt the boat (`hull damage N%`, say 30 % or more).

## Steps

1. Read `HULL 70%  SAFE 105 m` (or thereabouts) in the status column.
2. Order a depth below the safe depth (set a deep target with `C` and then deeper if needed;
   `C` is 60 m, so this needs damage over 60 % or a deeper order via the touch `DEEP`... use
   `C` after 60 % damage) and wait.
3. Come back above the safe depth.

## Expected

- `SAFE <m>` is 150 m times the hull left (150 m at no damage, 105 m at 30 %, 60 m at 60 %).
- Below it, every ten seconds the log says `HULL GROANING at <depth> m, safe depth <m> m:
  damage N%` and the damage climbs, faster the deeper you are below the safe depth; at 100 %
  the hunt ends `the boat was sunk`.
- Above the safe depth the damage stops climbing (it is never repaired).

## Automated

`tests/test_hunt_rework.py::test_below_the_safe_depth_the_hull_takes_damage_and_says_so`.
