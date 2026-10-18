# jenesboat-v2

This is a 2d submarine hunting simulation game. The background is set on WWII. The player controls the submarine searching and hunting enemy ships in the open ocean.
The submarine must leverage it's stealth, limited speed and fire power to deal maxiumn damage to enemy naval power and economic.
The major enemy ship types are merchant and military ships. They offen comes in fleets, with military ships escorting the merchant ships to their destination.

## Key factors

- Submarine depth: affects
  * submarine speed
  * periscope availability
  * visibility of both sides (different visibility for surface vessels and submarines)
  * submarine weapon availability
  * weapon damage to the submarine
- Day / night: affects the visual visiblity of both sides
- Submarine battery: how long can submarine stay submerged
- Propeller speed: affects visibility

## Controls

- All vessels (including both player and enemy ships) use classic ship maneuver, accelerate / decelerate by propeller, turn by rudder.
- Different types of vessels have different maneuver parameters (`docs/PARAMETERS.md`).
- Player uses WASD to control submarine's propeller and rudder. Another key to controll submerging / emerging.

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
| 1-4   | time compression x1 / x2 / x4 / x8                       |
| P     | pause / resume                                           |
| L     | show / hide the symbol legend (on at the start)          |
| R     | new hunt (new seed); asks first, Y/R confirms, N cancels |


## Weapons

- Deck gun: equiped by enemy military ships and submarine. Can only fire on surface.
- Depth charges: equiped by enemy military ships.
- Torpedo: equiped by submarine. Can be fired on submerged or emerged status. Once fired, keep it's speed and course.


## Art style

- Simplest 2d lines / boxes / circles / dots repersentation.


## Strategies

### Player (submarine)

- Locate the fleet as far as possibile
- Prefer ambush the fleet on the projected route
- Approach the fleet stealthly
- Look for openings in the formation unprotected merchant ships. Prioritize them as attack target
- If the formation is tight, try to lure the military ships out of the formation.
- Always avoid facing military vessels directly. Hit, run, hide and hit again is the golden rule

### Merchant ships

- When attacked, dodge the immediate attack, keep distance with enemy, spread out
- Keep close to military otherwise.

### Military ships

- When cruising, keep in the outter rim to protect the convoy.
- When under thread, dispatch portion of military force to try to elimitate the thread, while keeping the rest to protect the convoy.
- Return to formation as soon as the thread is elimiated or lost.

## Development

- Stack: Python 3.13 + [raylib-python-cffi](https://electronstudio.github.io/raylib-python-cffi/)
  (`pyray`); the browser build is CPython 3.12 on WebAssembly via
  [pygbag](https://pypi.org/project/pygbag/), deployed to GitHub Pages.
- `uv` manages the Python environment and packaging; Nix devshell provides the other tools;
  `just` holds the shortcuts (`just` lists them).
- GitHub Actions lint, test, build and publish every build:
  <https://pandazxx.github.io/jenesboat-v2/> (build index, one playable page per build).
- Conventions (branches, commits, tags, releases, build naming): `docs/CONVENTIONS.md`.
- How an LLM agent tests a build (headless sim, browser driver): `docs/AGENT_TESTING.md`.
- How user and agent collaborate (requirements, issues, acceptance tests, reviews):
  `docs/AGENT_WORKFLOW.md`.

```sh
just sync        # install dependencies
just test        # pytest (game logic is window-free)
just run         # play in a native window (--seed N for a given hunt)
just sim --trace # headless simulation, JSON events
just build-web   # pygbag bundle in dist/web
```

Milestones: M0 bootstrap (#2), M1 merchant hunting (#9): spot a merchant group far away,
predict its route, ambush it submerged and torpedo it before it sees you and runs. The hunt
ends when every merchant is sunk or more than 20 km away, or your torpedoes are gone. Every number
the balance depends on is in `docs/PARAMETERS.md`.
