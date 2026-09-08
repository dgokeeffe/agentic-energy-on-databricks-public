# Shared NEMWEB foundation

This directory is the read-only workshop framework for the governed NEMWEB
foundation. Facilitators prepare and verify it before the workshop. Participants
consume its governed outputs through [`QUICKSTART.md`](../QUICKSTART.md) and
their chosen track; they do not deploy, operate, or modify the foundation.

> **Facilitators only:** Links from this component to
> [`nemweb_foundation/`](../nemweb_foundation/README.md) identify the reviewed
> implementation and its authoritative operational scripts. Do not route
> participants into that directory.

Each attendee completes one self-contained track. The shared foundation serves
every track; no track creates a second data store.

## Fixed contracts

| Contract | Required interpretation |
|---|---|
| Regional dispatch | DISPATCHIS `PRICE` and `REGIONSUM`, five-minute interval-ending data |
| Market time | Fixed AEST (UTC+10), with no daylight saving |
| Processing time | Publication, landing, ingestion, and lineage timestamps are UTC instants |
| Corrections | Bronze retains archive versions; Silver selects the latest valid correction |
| Intervention | Gold retains both rows and exposes `is_effective_run`; consumers do not sum both runs |
| Unit output | Current SCADA is `actual_generation_mw`, not availability |
| Unit availability | Authoritative target and availability come from the daily T+1 unit-solution product |
| Snapshot | Deterministic prepared data with `live_evidence: false` |
| Landing roots | Snapshot and live data use separate `snapshot/` and `live/` siblings |

The complete source-to-table mapping and provenance remain in the
[migration manifest](../nemweb_foundation/README.md). The canonical
operating procedure remains in the
[NEMWEB runbook](deployment-gates.md).

## Facilitator sequence

Use a fresh AI-assistant conversation for each numbered prompt. Complete and
record the decision for one stage before opening the next.

1. [`01-deploy-foundation.md`](prompts/01-deploy-foundation.md) — validate the
   selected target, obtain explicit authorisation, and deploy with schedules
   paused.
2. [`02-run-snapshot.md`](prompts/02-run-snapshot.md) — run and reconcile the
   deterministic snapshot without making a live claim.
3. [`03-check-publication-gates.md`](prompts/03-check-publication-gates.md) —
   verify pipeline, SQL, metric, Genie, and dashboard results before live use.
4. [`04-prove-live-schedule.md`](prompts/04-prove-live-schedule.md) — after a
   separate approval, enable live mode temporarily, capture three scheduled
   cycles, pause again, and restore snapshot defaults.

The prompts do not grant permission. Deployment, job execution, live source
access, and schedule changes each require current human authorisation. Every
workspace-aware command must select `--profile daveok`. Stop if the profile,
workspace, identity, target resources, or permissions differ from the approved
setup.

## Framework skills

| Need | Skill |
|---|---|
| Select the next safe stage and preserve the data contract | [`00-nemweb-navigator`](skills/00-nemweb-navigator/SKILL.md) |
| Validate or operate deterministic snapshot mode | [`01-snapshot-mode`](skills/01-snapshot-mode/SKILL.md) |
| Prepare or operate the separately approved live landing | [`02-live-landing`](skills/02-live-landing/SKILL.md) |
| Capture exact-update and three-cycle proof | [`03-evidence-gates`](skills/03-evidence-gates/SKILL.md) |

These skill directories contain no copied operational scripts. Facilitators use
the scripts in `nemweb_foundation/scripts/` from the working directories shown
in the canonical runbook.

## Stop conditions

Stop and use the prepared workshop substitute when any required preflight item
is unverified, the selected profile is unexpected, a resource or permission
cannot be confirmed, snapshot data is about to be labelled live, an exact
pipeline update cannot be identified, a quality metric is missing, or the live
source is ahead of Bronze. Never weaken a check, invent source rows, use a full
refresh as routine recovery, or unpause a schedule to debug it.
