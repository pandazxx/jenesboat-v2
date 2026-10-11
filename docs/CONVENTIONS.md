# Development conventions

## Branches and pull requests

- `master` is always releasable. Nobody commits to it directly; every change arrives through a
  pull request.
- Work on topic branches named `topic/<short-slug>` (agents append a short id, e.g.
  `topic/m0-3672910`). Delete the branch after merge.
- Open the PR against `master` early. The PR title is the squash/merge commit subject.
- Required checks before merge: **Lint and test**, **Build web bundle**. The browser smoke test
  (**Agent smoke test**) must pass unless the PR explains why it cannot.
- Reference the issue the PR works on (`Closes #N` / `Part of #N`). Milestone work is tracked as
  a GitHub milestone with one tracking issue (e.g. `Milestone 0`, #2) and one sub-issue per
  deliverable.

## Commits

- Imperative subject line, <= 72 characters, no trailing period: `Add depth model to submarine`.
- Body explains *why* when it is not obvious. Wrap at 100 columns.
- Run `just lint` and `just test` before every commit.

## Versions, tags and releases

- Versions follow [SemVer](https://semver.org): `MAJOR.MINOR.PATCH`. While the game is pre-1.0,
  `MINOR` bumps may break save data or controls.
- The single source of truth is `version` in `pyproject.toml`. Bump it in a PR before tagging.
- Tags are `v<MAJOR>.<MINOR>.<PATCH>` on a `master` commit, annotated, e.g. `v0.1.0`.
  Pre-releases use `v<MAJOR>.<MINOR>.<PATCH>-rc.<N>` (`v0.2.0-rc.1`).
  `just tag v0.1.0` creates the tag after checking it matches `pyproject.toml`;
  `git push origin v0.1.0` publishes it.
- A GitHub Release is created from the tag with the same name as the tag (`v0.1.0`) and
  auto-generated notes; mark `-rc.N` tags as pre-releases. Milestones (`Milestone 0`, ...)
  are planning containers and are not tags.

## Build naming on the web

Every CI build is deployed to GitHub Pages: <https://pandazxx.github.io/jenesboat-v2/>.

| trigger                       | build name            | example                     |
| ----------------------------- | --------------------- | --------------------------- |
| push to `master`              | 7-char short SHA      | `builds/77d6a1f/`           |
| pull request commit           | 7-char short SHA (head commit) | `builds/03e4c44/`  |
| tag `v*`                      | the tag name          | `builds/v0.1.0/`            |

The site root is an index of all builds, newest first; `builds.json` is the same list as JSON.
The build id is also shown in the game HUD and in the `ready` event, so a tester can confirm
which build is running.

## Code layout rules

- Game logic lives in `src/jenesboat_v2/sim/` and `game.py` and must import nothing from
  raylib; it is unit-tested with pytest and runs headless (`just sim`).
- Only `render.py` and `app.py` touch `pyray`.
- Code must run on CPython 3.12 as well as 3.13: the browser runtime (pygbag) is 3.12, so avoid
  3.13-only syntax and stdlib additions.
