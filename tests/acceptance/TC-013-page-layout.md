---
id: TC-013
title: The game canvas is centred in the browser window and scales with it
issue: 14
added_in: 15
---
## Preconditions

Open the build URL in a desktop browser (Chrome, Firefox or Safari), any window size.

## Steps

1. Wait for the HUD to appear.
2. Resize the browser window: narrow and wide, short and tall. Try full screen (F11).

## Expected

- The game fills the largest 16:9 box that fits the window and is centred both ways, with the
  dark ocean colour around it; it is never pinned to a corner and never cut off.
- Resizing keeps it centred and rescaled; the HUD text scales with the box and stays readable.
- Keys still work after clicking anywhere on the game.

## Automated

The CI job "Agent smoke test" screenshot (artifact `agent-smoke-<build>`) shows the placement
at 1024x640.
