---
name: evidence-gates
description: Capture exact NEMWEB run and pipeline-update proof, reconcile quality and freshness, and validate three consecutive scheduled cycles.
---

# Evidence gates

Use this skill for snapshot publication checks and facilitator-only live-cycle
proof.

## Read first

- [`../../Instructions.md`](../../Instructions.md)
- [NEMWEB runbook data and evidence sections](../../deployment-gates.md#4-data-and-analyst-gates)
- [Migration manifest evidence contract](../../../nemweb_foundation/README.md#operations-and-evidence-contract-slice-9-2026-09-02)

> **Facilitators only:** The authoritative capture and validation programs are
> `nemweb_foundation/scripts/capture_nemweb_evidence.py` and
> `nemweb_foundation/scripts/validate_nemweb_live.py`. Reference them from the
> working directory shown in the runbook. Do not copy them into this skill or
> expose the solution directory to participants.

## Per-cycle proof

For each cycle, record the orchestration run ID, child lander outcome, pipeline
ID, and exact pipeline update ID. Poll that update to `COMPLETED`, `FAILED`, or
`CANCELED`, and filter events to the same update. If identifiers are not exposed,
use task timestamps and proceed only when exactly one update matches. Never
select an unproven latest update.

Capture, for each of the five critical subjects:

- source filename, publication time, source interval, and checksum signature;
- landed, Bronze, Silver, and Gold counts and watermarks;
- Gold business-column fingerprint and natural-key duplicate count;
- exact-update expectation metrics and failures;
- source-to-Gold and landed-to-Gold processing lags; and
- binding-constraint evidence at or before Bronze when a new interval has no
  binding row.

The five subjects are regional price/demand, unit actual output, SCADA by
region/fuel, binding constraints, and interconnector flow.

## Three-cycle decision

Append cycle two and cycle three to the same evidence pack. The live validator
must see all five subjects in every cycle, one distinct update ID per cycle,
successful outcomes, non-empty Gold output, zero duplicates and failed
expectations, and starts approximately five minutes apart.

A no-new-source cycle requires an unchanged filename, publication timestamp,
source interval, and checksum signature, with the listing not ahead of Bronze.
A changed DISPATCHIS source with no new binding row is a
source-changed/no-Gold-change observation, not no new source.

Stop on an ambiguous update, missing expectation metrics, failed expectation,
duplicate key, negative processing lag, source listing ahead of Bronze, or
invalid cycle spacing. Preserve failures and nested pipeline exceptions. Store
only reviewed, non-sensitive output; exclude tokens, private workspace URLs,
tenant identifiers, and private operator details.
