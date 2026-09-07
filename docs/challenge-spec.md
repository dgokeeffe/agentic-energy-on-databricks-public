# Agentic Energy challenge specification

## Outcome

A cross-functional pair completes one `workshop-ready` GitHub issue against the
governed NEMWEB implementation. The pair must show both an operator result and
an engineering result that can be accepted or rejected from deterministic tests,
an agentic eval, and independent review.

## Delivery sequence

```text
select workshop-ready issue
→ inspect issue and nemweb_foundation
→ understand measurable requirements
→ propose exact files and tests
→ human approval
→ branch and implement
→ deterministic tests
→ agentic eval
→ adversarial review
→ pull request with Closes #N
→ human accept, send back, reject, or stop
```

The repository-owned skills under [`.agents/skills/`](../.agents/skills/) define
each stage. GitHub is the shared issue and pull-request system; the workshop does
not require Jira, Beads, a local issue database, or a tracker CLI.

## Governed NEM contracts

- Dispatch intervals end in fixed AEST (UTC+10, no daylight saving).
- Processing and publication timestamps are timezone-aware UTC.
- Corrections use source run order; both intervention rows remain, with
  `is_effective_run` used by governed defaults.
- `actual_generation_mw` is five-minute SCADA output, never unit availability.
- AEMO interconnector MW keeps source sign. Market-wide constraint and flow
  summaries repeated per regional app row have no regional allocation or
  directional interpretation.
- Snapshot and prepared data remain labelled non-live.

## Starter choices

- `nemweb_foundation/` contains the inspectable NEMWEB pipeline and tests.
- `nemweb_app/` uses AppKit Analytics for lakehouse reads and Lakebase for native
  investigation state. Mock and integration modes share domain contracts.
- `workshop/lakebase/` fixes single-writer ownership, Triggered sync, an
  idempotent migration, and an offline CDF reducer.
- `nemweb_ml/` fixes point-in-time schema, chronological splits, leakage gates,
  MLflow Unity Catalog registry configuration, and batch lineage fields.

## Acceptance

The approved plan names exact files, tests, eval, reviewer, and stops. A person
other than the plan author approves it. The implementation passes focused and
complete applicable tests, link and safety validation, and `git diff --check`.
The eval cites trajectory evidence. A reviewer other than the author returns a
reproducible `PASS` after repairs. The pull request uses `Closes #N`; a person
then decides whether to accept, send back, reject, or stop.

Participants may inspect all starters and run local checks. They do not deploy,
run jobs, create or change Lakebase or Unity Catalog resources, change grants,
enable live NEMWEB, change schedules, change `@prod`, add Model Serving, or
merge. Platform operations require separate facilitator approval and evidence.
