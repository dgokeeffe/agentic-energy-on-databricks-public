---
name: read-evidence-and-plan
description: Read the UTC incident evidence and approve a Track B plan naming the single implementation file, contract test, evaluation rubric, and stop conditions before editing.
---

# Read evidence and approve the plan

Use this skill for the Track B part of cards 1–3. Copy
[`assets/task-plan.md`](assets/task-plan.md) to the pair's working evidence
location; do not overwrite the template.

## Fixed contracts

- The repository is green before the labelled patch is applied.
- Processing, publication, and lineage timestamps are UTC instants.
- NEM market `interval_end` remains interval-ending fixed AEST, UTC+10, with no
  daylight saving.
- The seeded defect is not a general cleanup; it threatens the Track A
  freshness claim by making cross-system time comparisons unreliable.
- The named deterministic test must remain present, enabled, and unchanged.

## Plan requirements

Name the defect, expected result, one implementation file selected by the
patch, named test, focused regression, agentic evaluation criteria, required
run evidence, and stops. The eval must cover:

| Criterion | Required evidence |
|---|---|
| Tool choice | The agent inspected the named implementation and test before editing. |
| Trajectory | The agent reproduced red, made one approved repair, and reran green. |
| Operating envelope | Only approved files changed; no merge or deployment occurred. |
| Rubric quality | The record includes the diff, commands, exit codes, failures, and residual risks. |

A person who did not draft or dispatch the plan records approval and time before
any write-capable run. Stop if another file, schema, dataset, repository,
credential, merge, deployment, or weaker check is proposed.
