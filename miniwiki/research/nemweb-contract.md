# NEMWEB source contract

## Why this page exists

This page is a place to accumulate source research without pretending that an
uncited answer is a requirement. Add citations, capture dates, and unresolved
questions as the workshop learns.

The default workshop question is:

> Can an operator trust the latest regional price trend, given NEMWEB
> corrections, freshness, and timezone handling?

Pairs execute from [`../../QUICKSTART.md`](../../QUICKSTART.md).
If Omnigent is down, start here and label the research prepared.

## Current working assumptions

- Dispatch prices and demand arrive at a five-minute interval grain.
- The canonical parser emits `region`, `interval_datetime`, `demand_mw`, and
  `price_per_mwh`.
- Source timezone must be declared and timestamps normalized before Silver
  consumers use them.
- A versioned snapshot is the reproducible baseline. Live NEMWEB watermarks and
  source-to-Gold latency provide the operating evidence for the five-minute path.

## Evidence to collect

For each research session record the source URL or document, capture date,
source version if available, grain, freshness/expected lag, timezone, natural
key, missing-value behavior, licensing/provenance, and what could make the
conclusion wrong.

## Questions still open

- Which NEMWEB report families are permitted for the workshop and under what
  reuse terms?
- Which publication timestamp should drive freshness: source event time,
  pipeline ingestion time, or both?
- What fields are guaranteed versus commonly present in DISPATCHIS?
- Which business-local timezone should daily metrics use for each region?

## Handoff

The implementation scope, ordered tasks and evidence threshold are recorded in
[`../features/full-nemweb-lakeflow.md`](../features/full-nemweb-lakeflow.md).
