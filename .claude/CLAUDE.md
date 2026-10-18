# jenesboat-v2

2D WWII submarine hunting game (see `README.md` for game design: depth, day/night, battery,
propeller speed, weapons, and ship AI strategies). Art style: simple lines/boxes/circles/dots.

## Stack
- Python >=3.13, managed with `uv`; tasks via `just`.
- Rendering: raylib (pyray), target is WASM deployed to static hosting (GitHub Pages / S3).
- Package: `src/jenesboat_v2/`; tests: `tests/` (pytest). Lint/format: ruff (line length 100).
- Dev env is Nix flake + direnv on user machines; in the agent container use `uv` directly.

## Workflow
- `just sync` install deps, `just test` run tests, `just lint` check, `just fmt` autofix.
- Run `just lint` and `just test` before every commit.
- Work on a topic branch, push, and open a PR against `master`; never commit to `master`.
- Keep game logic (physics, ship AI, visibility) separate from rendering so it is unit-testable
  without a window: `sim/`, `game.py` and `touch.py` never import pyray; only `render.py`/`app.py` do.
- The web page (`web/noctx.tmpl`) owns the canvas size and the touch buttons; the game draws in
  logical px (`app.logical_size`) and polls the buttons through `touch.py` (one bit per key,
  the page's `JB_KEYS` must match `touch.KEYS`).
- Every tunable number lives in `sim/params.py` and is explained in `docs/PARAMETERS.md`;
  balance changes edit those, not the modules that use them.
- The browser runtime (pygbag) is CPython 3.12: keep the package 3.12-compatible.
- `just build-web <id>` builds `dist/web`; `just sim` runs the headless simulation;
  `just agent-web-test <url>` drives a build in headless Chromium (see `docs/AGENT_TESTING.md`).
- Conventions for branches, commits, tags, releases and web build naming: `docs/CONVENTIONS.md`.
- Collaboration rules (file issues for chat requirements, labels, acceptance cases in
  `tests/acceptance/`, test plan checklist in the PR, how to reply to reviews): `docs/AGENT_WORKFLOW.md`.
- CI (`.github/workflows/ci.yml`) publishes every build to the `gh-pages` branch under
  `builds/<short-sha|tag>/` and regenerates the index with `scripts/gen_build_index.py`.
- `.copier-answers.yml` is managed by Copier; do not edit it.
