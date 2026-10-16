---
id: TC-014
title: Several contacts are tracked at once and T chooses the target
issue: 14
added_in: 15
---
## Preconditions

The whole group in sight (three hull boxes on the map).

## Steps

1. Look at the map and the contact panel.
2. Press `T` three times, pausing between presses.
3. Lose the selected ship (let it sail out of range, or go deep and fast) and watch the panel.

## Expected

- Every contact has its own dashed projected course; the target's is bright and the target
  wears a thin white ring. The panel shows the target (`TGT <id>`), then one line per other
  contact (`<id>  BRG  RNG  seen/sonar`) and `T: next target`.
- Each `T` moves the ring, the bright course line, the panel header (now `TGT <id> (T)`) and
  the fire-control markers to the next contact, nearest first, and wraps around.
- A chosen target stays selected while it is held, even when another ship comes closer. When
  it is lost the nearest contact becomes the target again.

## Automated

`tests/test_game_and_events.py::test_target_selection_cycles_and_persists`.
