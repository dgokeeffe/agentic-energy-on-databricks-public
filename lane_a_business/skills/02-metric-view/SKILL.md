---
name: lane-a-metric-view
description: Check the regional dispatch metric-view contract, its effective-run filter, dimensions, measures, units, and reconciliation to governed Gold.
---

# Metric view

Use this skill for the Track A part of card 6. A facilitator may release a
workspace metric view or a prepared definition after the relevant preflight.
Do not infer that either exists merely because this skill names it.

## Required contract

The regional metric view uses the governed five-minute regional Gold subject
and applies `is_effective_run = true` globally. It exposes:

- dimensions: `interval_end`, `region_id`, `intervention`,
  `source_publication_at`, and `gold_published_at`;
- average dispatch price in AUD/MWh;
- maximum dispatch price in AUD/MWh;
- average total demand in MW;
- estimated demand energy using five minutes divided by 60; and
- effective five-minute observation count.

Market intervals end in fixed AEST. Source and Gold publication fields support
freshness analysis and remain separate. Metric measures require the syntax
supported by the released workspace; follow the facilitator's verified example.

## Check

1. Record whether the definition is live or prepared and who supplied it.
2. Name the source, global filter, measures, dimensions, units, and time grain.
3. Compare at least one metric result with the saved Gold-window method.
4. Keep valid negative prices and explain missing values.
5. Record the result, discrepancy, uncertainty, and human decision.

Stop if effective-run behaviour is absent, dispatch and settlement prices are
confused, units or freshness fields are missing, reconciliation fails without
explanation, or another data product is required.
