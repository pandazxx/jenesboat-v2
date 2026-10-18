---
id: TC-011
title: A legend explains every map symbol and can be hidden with L
issue: 14
added_in: 15
---
## Preconditions

Fresh hunt (`R`); no legend is shown.

## Steps

1. Press `L` and read the panel in the lower right.
2. Press `L` again; press `L` once more.
3. Get a visual contact and a firing solution (see TC-005) and compare the orange markers with
   the legend.

## Expected

- A panel titled `LEGEND (L to hide)` lists every symbol with a swatch in its colour: your boat
  (surfaced/submerged), the red lookout circle, your track, ships in sight, hydrophone ghosts
  and bearings, the target's projected course, the torpedo track, the crossing ring, the
  target-at-impact dot, the miss-distance line (green = fire), running torpedoes, and the
  intel / last-seen marker.
- The legend is not up at the start; `L` shows it, hides it (the build tag and messages
  stay) and shows it again.
- The orange ring sits where the faint torpedo line crosses the dashed target course, the
  orange dot sits on the dashed course where the target will be when the torpedo arrives, and
  the line between them shrinks to nothing and turns green as the solution comes good.

## Automated

`tests/test_render.py::test_legend_is_off_by_default_and_l_toggles_it`.
