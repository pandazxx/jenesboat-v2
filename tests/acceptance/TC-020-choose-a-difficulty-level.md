---
id: TC-020
title: A hunt can be started at a chosen difficulty level and keeps it on restart
issue: 21
added_in: 27
---
## Preconditions

A web build URL from the build index.

## Steps

1. Open the build with `?difficulty=veteran` appended to its URL (for example
   `https://pandazxx.github.io/jenesboat-v2/builds/<id>/?difficulty=veteran`).
2. Read the first message in the log and the tag at the bottom right of the HUD.
3. Press `R` (or `NEW`) and confirm; read the message and the tag again.
4. Open the build without the query, or with `?difficulty=cadet`, and read them again.
5. (Optional, native) `just run -- --difficulty cadet` and `just sim --difficulty veteran
   --seconds 1`: the `ready` and `final` events show `"difficulty":"veteran"`.

## Expected

- With `?difficulty=veteran` the objective message starts `Objective (Veteran):` and the HUD
  tag reads `build <id>  seed <n>  Veteran`.
- After `R` the new hunt is still `Veteran` (next seed).
- Without the query the level is `Patrol`; with `?difficulty=cadet` it is `Cadet`. A
  misspelt level falls back to `Patrol` (a `warning` event in the console).

## Automated

`tests/test_difficulty.py::test_game_starts_at_the_chosen_level_and_restarts_keep_it`,
`tests/test_difficulty.py::test_headless_cli_takes_a_difficulty`,
`tests/test_difficulty.py::test_the_web_page_hands_the_url_level_to_the_game`; the CI phone
smoke step loads `?difficulty=veteran` with `--expect-difficulty veteran`.
