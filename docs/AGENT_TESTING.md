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
just sim --seconds 30 --trace --seed 7 \
  --script '[{"t":0,"throttle":1},{"t":5,"rudder":1},{"t":8,"dive":true},{"t":20,"fire":true}]'
```

`--seed` picks the hunt (same seed, same world); `--seconds` is game time before time
compression. Order keys: `throttle` (-1..1) or `telegraph` (`"ahead half"`, `"stop"`, ...),
`rudder` (-1..1, +1 = 35° starboard, stays until the next order), `dive` (Space: one band
shallower, or periscope depth from the surface), `deep` (C), `target_depth` (metres), `fire`
(F), `time_scale` (1, 2, 4, 8, 16 or 32), `target` (a ship id, or `null` for automatic), `next_target`,
`pause` (toggle; the headless clock keeps running but the world
does not, so a paused stretch shortens the simulated time).

Events (one JSON object per line, `t` in game seconds): `ready`, `intel` (the radio report:
approximate bearing/range/course of the group), `order`, `contact` / `contact_lost`
(`method` is `visual` or `hydrophone`), `alert` (merchants start running; `reason` is `sighted`
or `torpedo`), `fire`, `fire_refused`, `hit`, `sunk` (with `tonnage`), `torpedo_lost`,
`escaped`, `mission_end`, `pause`, `restart`, `state` (every second with `--trace`), `final`.
A `state`/`final` payload looks like:

```json
{"event":"state","t":30.0,"seed":7,"time_scale":1,"zoom":20.0,
 "player":{"x":20000.0,"y":20000.0,"heading":35.0,"speed_kn":12.1,"throttle":1.0,"telegraph":"AHEAD FLANK","rudder":1.0,
           "depth":12.0,"target_depth":12.0,"surfaced":false,"band":"periscope",
           "battery":0.998,"tubes":{"loaded":3,"reserves":8,"reload":12.0},"can_fire":true},
 "ships":[{"id":"freighter-1","kind":"merchant","type":"freighter","x":...,"heading":212.0,
           "speed_kn":8.0,"hits":0,"sunk":false,"escaped":false,"alerted":false}, ...],
 "contacts":[{"id":"freighter-1","method":"hydrophone","bearing":38.0}, ...],
 "torpedoes":[{"id":1,"x":...,"y":...,"heading":35.0,"run":450.0,"armed":true,"alive":true}],
 "target":"freighter-1","solution":{"run":1800.0,"time":117.0,"error":-12.0},
 "tonnage":0,"log_nm":1.25,
 "mission":{"status":"active","sunk":[],"escaped":[],"remaining":[...],
            "tonnage":0,"torpedoes_left":11},
 "cue":{"kind":"intel","ship":null,"x":...,"y":...,"course":212.0,"bearing":38.0,"range":15600.0},
 "world":{"width":40000.0,"height":40000.0,"light":1.0}}
```

`contacts` is what the boat knows: visual contacts are exact and carry the ship `type`;
hydrophone contacts are the operator's estimate of position, course and speed with an empty
`type` and never yield a firing solution. `ships` is ground truth for checking. `solution` is the
fire-control helper for the nearest visual contact: `error` near 0 means a torpedo fired now
along the heading meets the target. `mission.status` is `active`, `complete` (every merchant sunk or got away: more than 20 km
from the boat or off the map) or `out_of_torpedoes`; `mission.reason` says which.
`cue` is where to look when nothing is in sight: the intel
report, or the dead-reckoned position of the ship fixed last (`kind` = `last_seen`); `null`
while any ship is held visually or on the hydrophones. `tests/test_hunt.py` shows a scripted skipper that uses
exactly these to ambush the group; it is the template for an agent playing a build.

## 3. The web build in a headless browser

Each build is deployed at `https://pandazxx.github.io/jenesboat-v2/builds/<name>/` (see the
[build index](https://pandazxx.github.io/jenesboat-v2/) or `builds.json`). The game prints the
same `JENESBOAT` events to the browser console, so a Playwright script can drive it:

```sh
just agent-setup                 # once: downloads headless Chromium
just agent-web-test https://pandazxx.github.io/jenesboat-v2/builds/<name>/ \
  --keys "W:0.3,W:0.3,W:0.3,W:0.3,D:2" --dpr 2 --screenshot dist/agent/web.png
```

The script waits for the `ready` event (the first load fetches the Python runtime from the
pygbag CDN and can take a minute), focuses the canvas, holds the given keys for the given
seconds (each `W` press is one telegraph position, so four presses order AHEAD FLANK), then
prints and writes (`dist/agent/web.json`) a summary:

```json
{"ok": true, "ready": {"event":"ready","build":"abc1234", ...},
 "states": 6, "first_state": {...}, "last_state": {...},
 "player_moved_m": 41.3, "speed_kn": 4.9, "screenshot": "dist/agent/web.png"}
```

`--dpr 2` emulates a high-DPI (Retina) screen, where the browser's GL buffer is twice the
window size; CI uses it so the screenshot proves the game fills the canvas there too.
Exit code 0 means: ready, state events flowing and the submarine moved when keys were held.
On failure the summary contains the console tail and page errors. Look at the screenshot to
judge rendering (ocean grid in km, yellow submarine dot with its red visibility circle, HUD;
grey merchant boxes only once they are in sight).

`--mobile` emulates an iPhone 16 held sideways (852x393 CSS px, 3x pixels, touch screen):
the page shows the on-screen buttons and `--taps "W,W,W,W,D:2,SPACE"` touches them (a
button name from `web/noctx.tmpl`, `:seconds` to hold it). The summary then also has
`touch_overlay` (the buttons are shown), `viewport` (the game's logical size, e.g.
`976x450` for that phone) and `touch_inputs` (the presses the game logged with
`"source":"touch"`); `taps_ok` and the exit code require every logged tap to have arrived.
CI runs this as a second step and keeps `web-mobile.png` / `web-mobile.json` next to the
desktop pair in the same artifact.

```sh
just agent-web-test https://pandazxx.github.io/jenesboat-v2/builds/<name>/ \
  --mobile --keys "" --taps "W,W,W,W,D:2" --screenshot dist/agent/web-mobile.png
```

### Native window screenshots (layout checks)

The native build can draw one frame and quit, which is the quickest way to look at the HUD
at a given size without a browser (needs a display; in a container start `Xvfb :99` and set
`DISPLAY=:99`):

```sh
uv run jenesboat-v2 --seed 7 --size 976x450 --touch --screenshot dist/shots/phone.png
```

`--size WxH` is the window size (976x450 is what an iPhone 16 gets in logical px),
`--touch` lays the HUD out as on a touch screen (message log between the button zones, no
keyboard help line, legend centred) and `--screenshot FILE` saves the frame after 2 s of
game time. The `screenshot` event confirms the path and the logical size used.

To test a local build instead of a deployed one:

```sh
just build-web mybuild && just serve-web &   # http://127.0.0.1:9000
just agent-web-test http://127.0.0.1:9000/
```

Do not serve a build on `http://localhost:8xxx`: the pygbag runtime treats that origin as its
own dev server and rewrites the package CDN to `http://localhost:8000/cdn/`, so the `cffi` and
`raylib` wheels 404 and the game never reaches `ready`.

CI runs exactly this against every build (**Agent smoke test** job) and uploads the screenshot
and summary as the `agent-smoke-<name>` artifact.

## Controls reference

| key   | action                                                   |
| ----- | -------------------------------------------------------- |
| W / S | engine telegraph one position ahead / astern (ASTERN FULL, ASTERN HALF, STOP, AHEAD SLOW, AHEAD HALF, AHEAD FULL, AHEAD FLANK) |
| A / D | rudder to port / starboard while held (hard over in 2 s); it stays where released |
| Q     | rudder amidships                                         |
| Space | surfaced -> periscope depth -> surfaced; deep -> periscope depth |
| C     | go deep (60 m)                                           |
| F     | fire a torpedo along the heading                         |
| T     | next target (cycles through the contacts; otherwise the nearest is the target) |
| - / = | zoom out / in                                            |
| 1-6   | time compression x1 / x2 / x4 / x8 / x16 / x32           |
| P     | pause / resume                                           |
| L     | show / hide the symbol legend (off at the start)         |
| R     | new hunt (new seed); asks first, Y/R confirms, N cancels |

Playwright key names for `--keys`: letters as is, `Space`, `Minus`, `Equal`, `Digit4`.
Touch button names for `--taps`: `W S A D Q SPACE C F T MINUS EQUAL P L R Y N TIME`
(`TIME` cycles the time compression; `A` / `D` act while held, so give them seconds).

## Container image

`.prj_assistant/image/Dockerfile` installs the shared libraries headless Chromium needs, so the
agent container can run layer 3 after `just agent-setup`.
