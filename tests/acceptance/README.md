# Acceptance test cases

One Markdown file per case, `TC-NNN-<slug>.md`, written by the agent from the issue's
acceptance criteria and reviewed in the same PR as the code. Results are recorded per build in
the PR's **Test plan** checklist (see `docs/AGENT_WORKFLOW.md`, section 3).

Required front matter: `id`, `title`, `issue`, `added_in` (PR number). Required sections:
`## Preconditions`, `## Steps`, `## Expected`. Optional: `## Automated` naming the pytest or
smoke check that covers the same behaviour. `just test` validates the format.

```markdown
---
id: TC-001
title: Throttle and rudder move the submarine
issue: 7
added_in: 8
---
## Preconditions
...
```
