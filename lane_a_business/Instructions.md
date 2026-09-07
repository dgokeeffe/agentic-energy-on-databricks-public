# Track A — governed answer

Track A turns the default operator question into an explainable answer that can
also refuse an unsafe question. You are the Track A owner in one cross-track
pair. Keep working with the same Track B owner: use their timezone and freshness
evidence, and give them your approved brief and evidence threshold.

> Can an operator trust the latest regional price trend, given NEMWEB
> corrections, freshness, and timezone handling?

Do not invent a different question, report family, or data store unless the
facilitator approves the change. Do not assume a metric view, Genie Agent, Genie
One feature, MCP endpoint, dashboard, or App exists. Use a workspace surface
only after the facilitator confirms the relevant item in
[`../PRE-REQUISITES.md`](../PRE-REQUISITES.md) and releases it. Otherwise follow
the published [prepared fallback](../docs/facilitator/workshop-fallback.md).

## What you must produce

- a cited NEMWEB research note and approved question brief;
- a saved Gold window with source, capture time, row count, and freshness;
- a checked metric view with named measures and dimensions;
- one supported answer carrying source and freshness;
- one refusal of an out-of-scope bid recommendation;
- the access limit for an approved MCP, or a recorded "no MCP" decision;
- one dashboard, App, or prepared Markdown surface showing owner, source, and
  freshness;
- benchmark expectations written before rerun; and
- a completed [pilot canvas](../docs/participant/pilot-canvas.md).

Record each result in the
[pair record](../docs/participant/workshop-pair-record.md). Label evidence as **live**,
**snapshot**, or **prepared fallback**. Snapshot and prepared material are never
live proof.

## Fixed analysis contract

| Item | Required meaning |
|---|---|
| Gold subject | `gold_nem_region_dispatch_5min` through `nem_region_dispatch_metrics` |
| Window | Last 24 hours of `is_effective_run = true`, or a labelled prepared window |
| Market time | Five-minute interval-ending AEST, UTC+10, no daylight saving |
| Processing time | Source publication, ingestion, and Gold publication are UTC instants |
| Price | Dispatch price in AUD/MWh, not settlement price or a forecast |
| Demand | Regional total demand in MW |
| Corrections | Bronze retains versions; Silver selects the latest valid correction |
| Intervention | Default analysis selects exactly one effective run per region and interval |
| Freshness | Report newest source publication and newest Gold publication separately |

Negative prices can be valid. Do not infer causation from a trend, recommend a
bid, forecast unpublished intervals, or hide missing and uncertain context.

## Numbered stages and clock

Use a fresh AI-assistant conversation for every prompt. Finish the current stage
and record the human decision before starting the next.

| Stage | Workshop time | Prompt | Output |
|---|---|---|---|
| 1. Research and brief | Cards 1–5, 10:03–12:00 | [`01-research-and-brief.md`](prompts/01-research-and-brief.md) | cited contract, approved brief, Gold-window evidence |
| 2. Metric view | Card 6, 13:25–13:50 | [`02-check-metric-view.md`](prompts/02-check-metric-view.md) | checked measures, dimensions, and filter |
| 3. Genie Agent | Card 7, from 13:50 | [`03-scope-genie-agent.md`](prompts/03-scope-genie-agent.md) | agent purpose, assets, instructions, and limits |
| 4. Genie One, refusal, and MCP | Cards 7–8, by 14:27 | [`04-test-genie-one-and-mcp.md`](prompts/04-test-genie-one-and-mcp.md) | supported answer, refusal, and MCP decision |
| 5. Governed answer surface | Card 9, 15:00–15:22 | [`05-build-answer-surface.md`](prompts/05-build-answer-surface.md) | one surface showing owner, source, and freshness |
| 6. Benchmarks and close | Card 10 and close, 15:22–16:00 | [`06-benchmark-and-close.md`](prompts/06-benchmark-and-close.md) | expected results, rerun decision, pilot canvas |

At 12:00 update the status board. At 14:27 exchange evidence simultaneously
with the Track B owner and record what your checks can now stop. The facilitator
selects closing reports; the pair does not add a separate presentation task.

## Decisions and stop conditions

At every stage, a person chooses **accept**, **send back**, **reject**, or
**stop**. Stop when:

- the decision owner is absent or the question changes without approval;
- the source, grain, time semantics, correction policy, or freshness evidence
  cannot be cited;
- snapshot or prepared evidence is about to be described as live;
- the analysis needs another table, a second product, or unapproved data;
- a workspace capability or identity has not passed preflight;
- the supported answer omits source, time range, units, or freshness;
- the product gives bid or forecast advice instead of refusing;
- another tool is added before the refusal works;
- the answer surface hides owner, source, or freshness; or
- the benchmark question or expected result changes to make a rerun pass.

Do not deploy, merge, run a job, change permissions, expose credentials, or
weaken a check. Use only the switching triggers in the fallback pack.
