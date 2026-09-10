# Track A — governed answer

Track A turns the default operator question into an explainable answer that can
also refuse an unsafe question.

This track is self-contained. It does not depend on Track B, Track C, or a
partner. Work at your own pace, in stage order. You may pair with someone on the
same track if you prefer; nothing requires it.

Copy [`../workshop/track-record-template.md`](../workshop/track-record-template.md)
and keep it beside you.

> Can an operator trust the latest regional price trend, given NEMWEB
> corrections, freshness, and timezone handling?

Start with the supplied question, then explore sensible follow-up questions
when they help explain the result. Keep the governed data contract rather than
creating a second data store. A metric view, Genie Agent, Genie One feature,
MCP endpoint, dashboard, or App may be live, prepared, or unavailable; label
which one you used and continue with the prepared path when the live surface is
not released.

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
- a short closing note: what this would need to be trusted in production.

Record each result in your track record. Label evidence as **live**,
**snapshot**, or **prepared**. Snapshot and prepared material are never
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

## Numbered stages

Use a fresh AI-assistant conversation for every prompt. Finish the current stage
by recording what you learned, what remains uncertain, and whether you want to
continue, revise the question, or ask for help.

| Stage | Prompt | Output |
|---|---|---|
| 1. Research and brief | [`01-research-and-brief.md`](prompts/01-research-and-brief.md) | cited contract, approved brief, Gold-window evidence |
| 2. Metric view | [`02-check-metric-view.md`](prompts/02-check-metric-view.md) | checked measures, dimensions, and filter |
| 3. Genie Agent | [`03-scope-genie-agent.md`](prompts/03-scope-genie-agent.md) | agent purpose, assets, instructions, and limits |
| 4. Genie One, refusal, and MCP | [`04-test-genie-one-and-mcp.md`](prompts/04-test-genie-one-and-mcp.md) | supported answer, refusal, and MCP decision |
| 5. Governed answer surface | [`05-build-answer-surface.md`](prompts/05-build-answer-surface.md) | one surface showing owner, source, and freshness |
| 6. Benchmarks and close | [`06-benchmark-and-close.md`](prompts/06-benchmark-and-close.md) | expected results, rerun decision, closing note |

## Explore safely

At every stage, record the evidence label, what you learned, and the next
choice: continue, revise, ask for help, or stop. Prepared and snapshot paths are
valid ways to rehearse the workflow; they must simply remain labelled as such.

Keep these as hard boundaries:

- never describe prepared or snapshot evidence as live;
- keep source, grain, time semantics, correction policy, units, and freshness
  visible when presenting an answer;
- do not infer availability, curtailment, causation, bids, or forecasts from
  this historical dataset;
- do not expose credentials or private workspace details;
- do not deploy, run jobs, change permissions, or alter live schedules without
  explicit facilitator authorisation; and
- do not change an expected result merely to make a rerun pass.

When a live capability is unavailable, use the prepared path, label the gap, and
continue exploring rather than treating the stage as blocked.
