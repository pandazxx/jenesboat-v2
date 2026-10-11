# Testing a build as an agent

Every build of jenesboat-v2 can be exercised by an LLM agent (`claude`, `codex`, ...) without a
human watching a screen. Three layers, cheapest first.

## 1. Unit tests (no window)

```sh
just sync && just lint && just test
```

## 2. Headless simulation (no window, no browser)

The CLI runs the real game logic without raylib and prints one JSON event per line, each
prefixed with `JENESBOAT ` so it can be grepped out of any log:

```sh
just sim --seconds 30 --trace \
  --script '[{"t":0,"throttle":1},{"t":5,"rudder":1},{"t":8,"dive":true}]'
```

Order keys: `throttle` and `rudder` (-1..1), `dive` (toggle surface/periscope depth),
`target_depth` (metres). Events: `ready`, `order`, `state` (every second with `--trace`),
`final`. A `state`/`final` payload looks like:

```json
{"event":"state","t":30.0,
 "player":{"x":2000.0,"y":600.0,"heading":35.0,"speed_kn":12.1,"throttle":1.0,"rudder":1.0,
           "depth":12.0,"target_depth":12.0,"surfaced":false},
 "ships":[{"id":"merchant-1","kind":"merchant","x":...,"heading":90.0,"speed_kn":8.0}, ...],
 "world":{"width":4000.0,"height":2250.0}}
```

## 3. The web build in a headless browser

Each build is deployed at `https://pandazxx.github.io/jenesboat-v2/builds/<name>/` (see the
[build index](https://pandazxx.github.io/jenesboat-v2/) or `builds.json`). The game prints the
same `JENESBOAT` events to the browser console, so a Playwright script can drive it:

```sh
just agent-setup                 # once: downloads headless Chromium
just agent-web-test https://pandazxx.github.io/jenesboat-v2/builds/<name>/ \
  --keys "W:3,D:2" --screenshot dist/agent/web.png
```

The script waits for the `ready` event (the first load fetches the Python runtime from the
pygbag CDN and can take a minute), focuses the canvas, holds the given keys for the given
seconds, then prints and writes (`dist/agent/web.json`) a summary:

```json
{"ok": true, "ready": {"event":"ready","build":"abc1234", ...},
 "states": 6, "first_state": {...}, "last_state": {...},
 "player_moved_m": 41.3, "speed_kn": 4.9, "screenshot": "dist/agent/web.png"}
```

Exit code 0 means: ready, state events flowing and the submarine moved when keys were held.
On failure the summary contains the console tail and page errors. Look at the screenshot to
judge rendering (ocean grid, grey merchant boxes, orange escort, yellow submarine dot, HUD).

To test a local build instead of a deployed one:

```sh
just build-web mybuild && just serve-web &   # http://localhost:8000
just agent-web-test http://localhost:8000/
```

CI runs exactly this against every build (**Agent smoke test** job) and uploads the screenshot
and summary as the `agent-smoke-<name>` artifact.

## Controls reference

| key   | action                        |
| ----- | ----------------------------- |
| W / S | throttle up / down (held)     |
| A / D | rudder port / starboard (held)|
| Space | toggle dive / surface         |

## Container image

`.prj_assistant/image/Dockerfile` installs the shared libraries headless Chromium needs, so the
agent container can run layer 3 after `just agent-setup`.
