---
id: TC-034
title: The whole run's events can be downloaded as a battle log
issue: 37
added_in: 38
---
## Preconditions

The web build on a phone or a desktop browser with the touch overlay (any touch screen, or
a browser with touch emulation); play a few minutes of a hunt.

## Steps

1. Tap `LOG` in the attack cluster.
2. Open the downloaded file.

## Expected

- A file `jenesboat-battle-log-<timestamp>.jsonl` downloads at once.
- It holds one JSON object per line: the `ready` event first, then every event of the run
  (`intel`, `contact`, `input`, `state` once a second, `escort_alarm`, `depth_charge_run`,
  `echo_lost`, `blind_lead`, `escort_stand_down` with its reason, ...), without the
  `JENESBOAT ` prefix, so it can be read by any JSON lines tool.
- Natively, `uv run jenesboat-v2 --log battle.jsonl` (also with `--headless`) appends the same
  lines, with the prefix, to the file.

## Automated

`tests/test_hunt_rework.py::test_the_battle_log_can_be_written_to_a_file`; the page's `jb_log`
hook is checked by `tests/test_touch.py::test_page_uses_the_same_buttons_in_the_same_order`.
