# Show when the network, not the generators, set the price

**Track B · advanced · no Lakebase · Visible today: NEEDS RICHER DATA**

Labels: `workshop`, `workshop-ticket`, `difficulty: advanced`, `area: pipeline`, `area: dashboard`, `blocked: needs data`

> **Blocked.** The snapshot holds **2 intervals of 1 region** with **0 negative
> prices** and **0 corrections**. Congestion is a story about prices diverging between
> regions while a flow sits at its limit, and one region cannot diverge from itself. A
> facilitator must land a wider dispatch window first. The design below is reviewable
> today; the demonstration is not.

## Operator outcome

An analyst can see the intervals where regional prices separated because the network
could not move power, distinguishing a transmission constraint from a generation
shortage.

## Fits Stage 4 once unblocked: 90 minutes

This is the exercise that most rewards market intuition. When an interconnector is at
its limit and prices on either side diverge, the expensive region is expensive because
of the *wire*, not because of the *plant* — and that is a genuinely different
operational conclusion.

Both inputs are already governed and populated in principle:
`gold_nem_interconnector_flows_5min` and `gold_nem_binding_constraints_5min`. There is
also an unused 30-minute aggregate, `gold_nem_interconnector_flow_30min`, with zero
consumers.

## The trap, which is the actual lesson

The repository is emphatic that **no governed interconnector-to-region mapping
exists**. The Track C app says so on screen:

> No regional allocation or directional interpretation is inferred because no governed
> interconnector-to-region mapping is available.

And AEMO's source sign is retained unchanged, so a positive or negative `mw_flow`
cannot be read as "into" or "out of" a region without that mapping.

So the honest exercise is **not** "show flow direction". It is: identify intervals
where a constraint binds and prices differ, report both facts, and **refuse to name
which way the power went**. A participant who produces a directional arrow has failed
the exercise while appearing to succeed — which is the same shape as the defects this
session found.

## Where to start

- `nemweb_foundation/agentic_energy/nemweb/pipeline/gold_interconnectors.py`
- `nemweb_foundation/agentic_energy/nemweb/pipeline/gold_constraints.py` — note
  `is_binding` is the documented derivation `MARGINALVALUE <> 0`.
- `gold_nem_region_dispatch_5min` — regional prices.
- `nemweb_foundation/dashboards/nemweb_overview.lvdash.json` — where the result belongs.
- `nemweb_foundation/DATA-CONTRACT.md` — the no-mapping rule, verbatim.

## Required change

A governed congestion view plus its dashboard surface.

- Identify intervals where at least one interconnector constraint binds, using the
  existing `is_binding` derivation rather than a new threshold.
- For those intervals, report the regional price spread across represented regions.
- Report the interconnector's flow at AEMO source sign, labelled as such.
- Filter `is_effective_run` so both intervention runs are not double counted.
- **State on the surface** that no direction is inferred and why.

## 30-minute checkpoint

The binding-interval identification and the price spread working, filtered to effective
runs. The dashboard tile is the second half.

## Deterministic tests

- only effective runs are counted, and an interval with both intervention runs yields
  one row;
- `is_binding` matches the documented `MARGINALVALUE <> 0` derivation, including the
  zero boundary;
- AEMO source sign is preserved unchanged;
- no output field, label, or tile title asserts a flow direction;
- market-wide counts are never summed across regions;
- a single-region window produces a defined result — say what a spread means with one
  region, because that is what today's snapshot contains;
- fixed AEST market time and UTC processing time stay distinct.

## Agentic eval

Did the agent infer a direction anywhere, including in prose or a chart axis label? Did
it invent a binding threshold instead of using `is_binding`? Did it filter
`is_effective_run`? Ask it what its output cannot tell an operator — a good answer names
the missing region mapping without prompting.

## Evidence required

Approved plan, changed files, SQL reconciliation against governed Gold, test output,
the count of binding intervals found, and a dashboard screenshot. If the snapshot yields
no binding interval, say so rather than presenting an empty tile as a result.

## Limits

No interconnector-to-region mapping invented, no directional interpretation, no summing
market-wide values across regions, no new threshold where a governed derivation exists.
No deployment or schedule change.
