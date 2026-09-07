# Agent-to-PR workflow

This repository uses Git, pull requests, and committed Markdown for work that
must continue between sessions. It does not require a local issue database or a
tracker-specific command, which keeps the workshop usable in Omni Sandbox.

## Responsibilities

| Participant | Responsibility |
|---|---|
| Parent agent | Reads the current objective, protects the approved files and behaviour, sequences implementation and review, and reports the final evidence. |
| Writer | Makes one coherent change, runs the named checks, and reports changed files and remaining uncertainty. |
| Reviewers | Inspect the current files and diff independently; they do not edit during a review pass. |
| Human reviewer | Decides whether the change is acceptable and whether it may merge or affect a workspace. |

## Sequence

```text
select one workshop-ready GitHub issue
  → inspect the issue and nemweb_foundation
  → understand measurable requirements
  → exact files, deterministic tests, eval, and review plan
  → approval by a person who did not draft the plan
  → branch and implementation
  → focused tests, full applicable checks, and git diff --check
  → agentic eval
  → independent adversarial review
  → reproduce and resolve concrete findings
  → pull request with Closes #N
  → human accept, send back, reject, or stop
```

Keep durable decisions, research, and handoff notes in [`../miniwiki/`](../miniwiki/index.md).
The pull request records the implementation evidence and review result.

## Pull request evidence

A pull request should state:

- the intended outcome and important behaviour that must not change;
- changed files and any migrations or external effects;
- exact validation commands and results;
- review findings and how each was handled;
- remaining uncertainty or prepared fallbacks; and
- whether deployment, live data, access, or schedule changes occurred.

Do not claim completion from an agent summary alone. Inspect the diff, run the
checks, and require explicit human approval before merge or workspace changes.
