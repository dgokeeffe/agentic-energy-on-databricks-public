# Participant workshop playbook

Start in [`QUICKSTART.md`](../../QUICKSTART.md). The facilitator's
[`workshop-run-of-show.md`](../facilitator/workshop-run-of-show.md) is the only
clock source. Work as one cross-functional pair with a business outcome
responsibility and an engineering quality responsibility.

## One shared GitHub-issue lifecycle

### One — select

Use [issue-navigator](../../.agents/skills/issue-navigator/SKILL.md) to select one
open issue labelled `workshop-ready`. Record the issue number, operator outcome,
acceptance points, and any required preview or prepared fallback. Do not create
a local ticket database.

### Two — understand

Use [understand-requirement](../../.agents/skills/understand-requirement/SKILL.md).
Inspect the complete issue, `nemweb_foundation/`, and the relevant app, ML, or
Lakebase starter. Confirm source, five-minute or other grain, units, fixed-AEST
market timestamps, UTC processing timestamps, correction order, intervention
handling, freshness, identity, and prepared-versus-live status. Turn prose into
measurable results. Record the task kind, preparation choice, and verification
rationale in the [pair record](workshop-pair-record.md). Start from a tested
procedure for repetitive work, a regression case for a repair, design discussion
for a new component, evidence and hypotheses for an investigation, or reference
behaviour for a translation. These choices never grant permissions or skip gates.

### Three — plan and approve

Use [plan-change](../../.agents/skills/plan-change/SKILL.md). Name exact files,
tests, commands, preserved contracts, eval rubric, review method, and stops. A
person who did not draft the plan must accept it before a write-capable
assistant starts. Send changed requirements back rather than silently widening
the plan.

### Four — implement and test

Create a branch and use [implement-test](../../.agents/skills/implement-test/SKILL.md).
Add or expose the deterministic test first when red/green proof is required.
Make the smallest approved change. Run focused tests, the relevant complete
suite, repository safety checks, and `git diff --check`. Capture exact commands,
exit codes, output, changed files, failures, fixes, and remaining uncertainty.

### Five — evaluate

Use [agentic-eval](../../.agents/skills/agentic-eval/SKILL.md). Evaluate the
trajectory, source and API choices, failed attempts, recovery, operating limits,
and operator outcome against the approved rubric. Keep this separate from unit
tests. Distinguish explanations ruled out with cited evidence from paths not
investigated. Record useful refinement, defect correction, restart, or block with
a reason when relevant; useful refinement is not automatically a failure.

The optional [two-case read-only calibration](../../workshop/agent-practice/README.md)
is pending facilitator placement and rehearsal. Use it only when the selected
issue and approved plan authorise it, without changing the run-of-show clock or
replacing any required check. Otherwise defer it or use a labelled prepared
facilitator demonstration outside the required work. Keep a proposed lesson in
the pair record and replay the original plus variant read-only. Separate actual
agent output from facilitator-prepared output and mark unrun steps `not-run`.
"No extra instruction needed" and "do not generalise" are legitimate outcomes;
there is no mandatory new skill or improvement metric per participant.

### Six — review

A person or independent assistant other than the author uses
[adversarial-review](../../.agents/skills/adversarial-review/SKILL.md). It returns
`REQUEST_CHANGES` with a reproducible finding or `PASS` with cited proof.
Reproduce, repair, and rerun every accepted finding. Record separate behavioural
and structural results: tests alone do not establish design fit. Structural review
covers the actual approved change, with location, consequence, and uncertainty;
"no material issue found" or "not applicable" with a reason is valid. Preserve the
existing reviewer floor in
[agentic-verification](../../.agents/skills/agentic-verification/SKILL.md), including
when using constrained fresh sessions or human fallback rather than native agents.

### Seven — prepare the pull request

Use [prepare-pull-request](../../.agents/skills/prepare-pull-request/SKILL.md).
Include `Closes #N`, changed files, tests, eval, review, prepared/live status,
and remaining uncertainty. A person accepts, sends back, rejects, or stops.
Participants and assistants do not merge or deploy. Lesson changes remain in the
pair record for read-only replay; a shared-skill or test change outside the original
approved plan needs a later approved task. Do not mutate the repository after final
review; accepted repairs must return through implementation and the affected gates.

## Fixed contracts

- NEM market timestamps are interval-ending fixed AEST (UTC+10, no daylight
  saving); processing timestamps are timezone-aware UTC.
- Preserve source corrections and intervention rows; governed defaults use the
  effective run.
- `actual_generation_mw` is SCADA output, not five-minute availability.
- AEMO interconnector flow keeps source sign. The app's constraint and flow
  summaries are market-wide, repeated per region, and have no regional
  allocation or inferred direction.
- Analytics reads lakehouse-owned data. Lakebase owns writable application
  state. Never write to a synced table.
- Training and evaluation splits are chronological. No feature may use
  information newer than its prediction time.
- Snapshot and prepared fixtures are non-live evidence.

## Participant limits

Participants may inspect `nemweb_foundation/` and run local checks. They do not
create or change Unity Catalog, Lakebase, synced tables, CDF feeds, Apps,
permissions, or schedules; deploy bundles; run jobs; enable live NEMWEB; change
`@prod`; add Model Serving; push without approval; or merge. Every
workspace-aware facilitator command uses the explicit `daveok` profile.

If a platform capability is unavailable, follow the
[prepared fallback](../facilitator/workshop-fallback.md), record `not-run` or
`blocked`, and continue only with independent local work.
