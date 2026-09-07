---
name: plan-change
description: Propose exact files, deterministic tests, eval criteria, and stops for one issue or authorised maintenance task.
---

# Plan the change

List the exact implementation files and tests, preserved contracts, commands,
fixture assumptions, and rollback point. Keep Analytics for lakehouse reads,
Lakebase for native application state, chronological splits for time-series ML,
and modern Lakeflow APIs where applicable. Include an agentic-eval rubric and
independent review, with separate behavioural and structural questions. Preserve
the existing reviewer floor in
[agentic-verification](../agentic-verification/SKILL.md); task kind does not reduce it.

Use the preparation choice from `understand-requirement` to explain the proof:
procedure-fit checks for repetitive tasks; a regression case for a small repair;
interface and failure-path checks for a new component or multi-step change;
cited supporting/contrary evidence and uninvestigated paths for an investigation;
and reference-behaviour comparisons for a translation or migration. Record why
these checks fit the task, along with unrun checks and limits, in the
[pair record](../../../docs/participant/workshop-pair-record.md) or maintenance plan.
No task kind grants permissions or waives a required gate.

The optional [read-only calibration](../../../workshop/agent-practice/README.md)
fits only if the selected issue and approved plan authorise it and the facilitator
has approved placement after rehearsal. It must not replace a required check or
change the run-of-show clock. Lesson instructions stay in the pair record for
read-only replay. A shared-skill or test change outside the original approved plan
needs a later approved task, not a post-review repository mutation.

Do not add provisioning, deployment, grants, live ingestion, schedule changes,
or production promotion to a participant plan. Repository maintenance uses the
same preparation and proof discipline, with only its explicitly authorised scope.
A person who did not draft the plan must approve it before implementation.
Send changed requirements back to `understand-requirement`; otherwise continue
to `implement-test` after approval.
