---
id: TC-020
title: A hunt can be started at a chosen difficulty level and keeps it on restart
issue: 21
added_in: 27
---
## Preconditions

The build index (https://pandazxx.github.io/jenesboat-v2/).

## Steps

1. Click the build in the index: a start page with one button per difficulty opens
   (`builds/<id>/start.html`). Click `Veteran`.
2. Read the first message in the log and the tag at the bottom right of the HUD.
3. Press `R` (or `NEW`) and confirm; read the message and the tag again.
4. Go back to the start page and pick `Cadet`; read them again. Then open the game page
   directly (`builds/<id>/`, no query) and once with `?difficulty=veteran` on its URL.
5. (Optional, native) `just run -- --difficulty cadet` and `just sim --difficulty veteran
   --seconds 1`: the `ready` and `final` events show `"difficulty":"veteran"`.

## Expected

- The start page shows the build id and three buttons with a one-line description each,
  `Patrol` marked as the default; it works on a phone held sideways.
- After `Veteran` the objective message starts `Objective (Veteran):` and the HUD tag reads
  `build <id>  seed <n>  Veteran`; `?difficulty=veteran` on the game URL does the same.
- After `R` the new hunt is still `Veteran` (next seed).
- `Cadet` gives `Cadet`; the game page without a query gives `Patrol`. A misspelt name on
  the URL falls back to `Patrol` (a `warning` event in the console).

## Automated

`tests/test_difficulty.py::test_game_starts_at_the_chosen_level_and_restarts_keep_it`,
`tests/test_difficulty.py::test_headless_cli_takes_a_difficulty`,
`tests/test_difficulty.py::test_the_web_page_hands_the_url_level_to_the_game`; the CI phone
smoke step loads `?difficulty=veteran` with `--expect-difficulty veteran`.
