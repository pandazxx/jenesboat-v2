# Agent workflow convention

How the user (product owner / reviewer) and the coding agent (`claude`, `codex`, ...) work
together on jenesboat-v2. The short version:

> **Chat is for triggering and talking. GitHub is the record.**
> Every requirement, bug, test result and review decision ends up in an issue or a PR, even
> when it was first said in chat. The agent is responsible for writing it there.

Roles: the **user** owns *what* and *whether it is good enough*; the **agent** owns *how*, keeps
GitHub up to date, and never merges on its own.

## 1. Providing requirements

| size | how | becomes |
| --- | --- | --- |
| idea / one-liner | say it in chat or open an issue with the **Requirement** template | one issue, label `type:requirement` |
| feature | **Requirement** issue with acceptance criteria | one issue, one PR |
| milestone | a tracking issue (`Milestone N`) + a GitHub milestone | agent files one sub-issue per deliverable (see #2) |

A requirement is "good enough to start" when it has:

- **Goal**: one paragraph on the player experience or outcome.
- **Acceptance criteria**: a checklist the user can verify by playing a build or reading a
  screen, e.g. `- [ ] a submerged boat is slower than a surfaced one`.
- **Out of scope** (optional) and **references** (README sections, issues, images).

If the user gives a requirement in chat, the agent files the issue itself (same template),
links it back in chat, and *asks clarifying questions in the issue* (label
`status:needs-info`). The user answers in the issue thread. The agent begins work once the
questions that block design are answered; everything else it decides and records as
"Assumptions" in the issue.

Anything that changes behaviour (new rule, balance change, control change) is a requirement
issue first, even if small. Refactors and chores are `type:task` issues and need no criteria.

## 2. Submitting issues

Use the templates (`.github/ISSUE_TEMPLATE/`):

- **Requirement** — see above.
- **Bug report** — must include the **build id** (shown bottom-right in the HUD and in the
  build URL `builds/<id>/`), steps, expected vs actual, and a screenshot or the agent smoke
  summary if available. Bugs without a build id get `status:needs-info`.
- **Task** — chores, refactors, tooling.

Labels the agent maintains on every issue:

| label | meaning |
| --- | --- |
| `type:requirement` / `type:bug` / `type:task` | what it is |
| `priority:p0` / `p1` / `p2` | p0 = blocks play or CI, fix first; p2 = whenever |
| `status:needs-info` | agent is waiting for the user to answer in the issue |
| `status:ready` | understood, not started |
| `status:in-progress` | a topic branch exists; the issue body links the PR |
| `status:needs-test` | PR is up and the user's acceptance test is the next step |
| `status:blocked` | waiting on something outside the issue (explained in a comment) |

Agent behaviour on a new issue: reply within the issue with (a) its understanding in two
sentences, (b) questions if any, (c) the plan (files/modules it will touch, tests it will
add). One issue -> one branch `topic/<issue#>-<slug>` -> one PR with `Closes #<issue#>`.
Milestone sub-issues get their own small PRs rather than one giant PR.

## 3. Test cases and results

Three layers, each with its own record:

1. **Automated** — pytest, lint, the pygbag build and the browser smoke test run on every
   PR commit. The record is the CI checks on the PR; the smoke screenshot and JSON summary
   are the `agent-smoke-<build>` artifact. Red CI is the agent's problem, not the user's.
2. **Acceptance test cases** — written by the agent from the issue's acceptance criteria,
   one Markdown file per case in `tests/acceptance/TC-NNN-<slug>.md` (see
   `tests/acceptance/README.md`). They live in the PR, so the user reviews the test cases
   together with the code. `just test` checks every case has the required fields.
3. **Acceptance results** — the PR description has a **Test plan** section listing each
   case as a checkbox with the build URL:
   `- [ ] TC-003 submerged boat is slower — https://pandazxx.github.io/jenesboat-v2/builds/<id>/`.
   The user plays the build and either ticks the box or comments `TC-003 FAIL: <what happened>`
   (a screenshot helps). The agent fixes, pushes, and re-posts the test plan with the new build
   id; previously ticked cases stay ticked only if the change cannot affect them (agent says
   which). A PR is mergeable when CI is green and every case is ticked or explicitly waived by
   the user ("TC-004 waived: not needed for M0").

Results are therefore versioned per build: the PR shows which build was tested and the final
state is preserved in the merged PR. Bugs found during acceptance that are *outside* the PR's
scope become new **Bug report** issues (the agent files them, referencing the build id).

## 4. Code review and replies

The user reviews on GitHub (inline comments or a review). Prefix comments to signal weight:

| prefix | meaning | agent response |
| --- | --- | --- |
| `must:` | has to change before merge | fix, reply "Fixed in `<sha>`: <what changed>" |
| `nit:` | style/minor | fix unless it conflicts with something; reply briefly |
| `question:` | explain | answer in the thread; add a code comment or doc if the answer is non-obvious |
| `idea:` | out of scope here | agent files a `type:task`/`type:requirement` issue and links it in the reply |
| no prefix | treat as `must:` | |

Agent rules when replying to a review:

- Reply **in the same thread** for every comment; never leave one unanswered. The agent does
  not resolve threads; the user resolves them when satisfied.
- Fixes for a review round go in commits prefixed `review:` (e.g. `review: clamp dive rate`)
  so the user can diff just that round. No force-pushes during review.
- If the agent disagrees, it says so once with the reason and a suggested alternative, then
  does what the user decides. If the user repeats the request, it is done without further
  debate.
- After addressing a round, the agent posts one summary comment: a list of comments ->
  what changed (with short SHAs), plus the refreshed **Test plan** when behaviour changed, and
  re-requests review.
- The user merges. The agent never merges, force-pushes to `master`, or deletes branches
  the user has not approved.

Review comments made in chat ("the sub turns too fast") are copied by the agent into the PR
as a comment ("from chat: ...") before being acted on, so the record stays on GitHub.

## 5. Further conventions (recommended)

- **Status reporting**: when a task takes more than one session, the agent leaves a progress
  comment on the issue at the end of each session: done / next / blocked. Chat gets the same
  three lines plus links.
- **Decisions log**: design decisions that the README does not cover (e.g. "speed is m/s in
  the sim, knots only in the HUD") go in the issue where they were made and, if lasting, in
  `docs/CONVENTIONS.md` or the module docstring. Not in chat only.
- **Definition of done** for a PR: issue linked, `just lint`/`just test` green, CI green,
  acceptance cases written and ticked/waived, docs updated (README, CLAUDE.md, docs/) when
  behaviour or workflow changed, PR description current.
- **One build id everywhere**: bug reports, test results and chat all refer to the 7-char
  short SHA or tag shown in the HUD. The index at
  <https://pandazxx.github.io/jenesboat-v2/> maps ids to commits and PRs.
- **Releases**: tagging is a user decision; the agent proposes (`just tag vX.Y.Z` plus draft
  notes grouped by milestone issues) and the user tags.
- **Priorities when the agent is idle**: `priority:p0` bugs, then `status:ready` issues in the
  open milestone in issue-number order, then anything else `status:ready`.
