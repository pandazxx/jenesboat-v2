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

- The game spans the full width of the window. A window wider than 16:9 is filled completely
  (more map left and right, the HUD text the same size as in a 16:9 window); a window taller
  than 16:9 shows a band of ocean colour above and below the 16:9 game. It is never pinned to
  a corner, never cut off and nothing looks stretched (grid squares stay square).
- Resizing keeps it centred and rescaled; the HUD text scales with the box and stays readable.
- Keys still work after clicking anywhere on the game.
- No on-screen buttons appear on a desktop with a mouse (see TC-019 for touch screens).

- On a high-DPI (Retina) screen the game still fills the whole box: it is not drawn small in
  the bottom-left quarter.

## Automated

The CI job "Agent smoke test" screenshot (artifact `agent-smoke-<build>`) shows the placement
at 1024x640 with a device pixel ratio of 2.
