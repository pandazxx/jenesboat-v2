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
  without a window.
- `.copier-answers.yml` is managed by Copier; do not edit it.
