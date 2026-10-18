---
id: TC-018
title: On a phone held sideways the game fills the screen and the HUD is readable
issue: 19
added_in: 20
---
## Preconditions

An iPhone 16 (or any phone) in Safari or Chrome, the build URL open, the phone held sideways
(landscape). Rotation lock off.

## Steps

1. Hold the phone upright (portrait) and look at the page.
2. Turn it sideways and wait for the HUD.
3. Read the HUD lines (`HDG`, `DEPTH`, `TUBES`), the contact panel on the right and the
   message log at the bottom. Tap `?` to show the legend, read it, tap `?` to hide it.
4. Press `AHEAD` four times and watch the boat and the grid.
5. Optional: add the page to the home screen and open it from there.

## Expected

- In portrait the page says to turn the phone sideways; nothing else is shown.
- In landscape the game covers the whole screen: no black bars on the sides, no scrolling, no
  browser zoom on double tap, no part of the HUD under the notch / Dynamic Island (the
  buttons keep clear of it; ocean may run under it).
- The HUD text is readable at arm's length (it is about 20 % bigger relative to the screen
  than on a desktop) and complete: nothing is cut off at the right edge. The message log
  sits between the two button clusters and long messages wrap. No legend is up at the start;
  `?` opens it centred and hides it again.
- The grid squares are square and the boat is a round dot (nothing is stretched); the map is
  wider than on a 16:9 desktop window (the `km` grid labels show more columns).
- Opened from the home screen the game is full screen without browser bars.

## Automated

CI runs `scripts/agent_web_test.py --mobile` (852x393 CSS px, 3x pixels); the summary's
`viewport` shows the logical size `976x450` and `web-mobile.png` in the `agent-smoke-<build>`
artifact shows the layout. `tests/test_app.py::test_logical_size` fixes the sizes.
