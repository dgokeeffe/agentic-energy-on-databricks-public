# NEMWEB price spike detector

## Intent

- **Decision owner:** paired business and engineering reviewers (name the person
  in the session note before approval).
- **Question:** which NEM regions and days concentrate the most dispatch-price
  risk?
- **Expected value:** make a handful of commercially important five-minute
  intervals visible without requiring a user to inspect raw prices.
- **Evidence threshold:** the definition must be reproducible from metadata,
  deterministic fixtures, a reconciled manifest, and a governed Gold surface.

## Discussion and boundary

The existing canonical market grain is `(region, interval_utc)` with demand and
price. A spike must be auditable: each flagged interval carries the rule and
threshold that fired, and daily metrics use the declared source timezone.

Questions to settle before implementation — **all now settled**, see
[Agreed rule](#agreed-rule-2026-09-10):

- Is the absolute rule `price_per_mwh > threshold`, and what threshold is the
  workshop default? — yes, `300.0` AUD/MWh.
- Is there a relative rule such as `price > k × trailing median`, and which rule
  wins when both fire? — no relative rule; deferred, so no precedence is needed.
- Is the boundary strict (`>`) or inclusive (`>=`)? — strict.
- How are negative prices, missing prices, short rolling-window history, daylight
  saving transitions, and duplicate intervals handled? — negative prices are
  valid and never spikes; a missing price is labelled `UNKNOWN_PRICE`; rolling
  history does not arise without a relative rule; market time stays fixed AEST so
  no daylight-saving conversion applies; duplicates resolve through the existing
  governed correction order before the rule is applied.
- Who owns the metric definition and what freshness is expected? — the metric
  view is owned with the rest of the governed foundation; freshness is labelled
  per row against a recorded 900-second limit rather than enforced as a filter.

## Agreed rule (2026-09-10)

| Item | Decision |
|---|---|
| Rule | Absolute only: `rrp_aud_per_mwh > threshold`. No relative rule. |
| Threshold | `300.0` AUD/MWh, carried in `resources/metadata/spike_rule.json` |
| Boundary | **Strict** `>`; exactly `300.00` is not a spike |
| Staleness limit | `900` seconds, matching `nemweb_ml/batch_score.py` |
| Fingerprint | `79b2541d5e5a7fa0fdbe244e2d6df89430ba9174d5ee2c493b7c4021fcfd7978` |

**Threshold rationale, and its limit.** 300 AUD/MWh is a *workshop-configured*
reporting level, not an AEMO-published spike definition. It was the pre-2022
administered price cap and remains a conventional high-price reporting level,
while the Market Price Cap is far higher. This was **not verified against current
AEMO documentation** — the implementing session had no network access to AEMO
sources — so the level is recorded as a reviewable default that a facilitator
should confirm before the number is quoted to participants as market fact. The
threshold is metadata, so correcting it needs no code change, and every flagged
row carries the threshold it was evaluated against so a past result stays
explainable afterwards.

**Why no relative rule.** A trailing-median rule was considered and deliberately
deferred: it needs rolling-window and short-history semantics that roughly double
the test surface, and the absolute rule already delivers the operator outcome in
the issue. Adding it later is a new definition review, not an amendment.

**In scope:** metadata-carried thresholds, per-interval Gold flags, per-region
and local-day metrics, manifest evidence, deterministic tests, and a governed
metric-view/Genie surface.

**Not in scope:** forecast-error analytics, FCAS detection, alert delivery,
unit-level attribution, interconnector/constraint context, or writeback to
AEMO/NEMWEB.

## Approved agent brief

Do not begin implementation until the human reviewer records the agreed rule in
this page. Once approved, the agent may change only the relevant metadata,
generic pipeline logic, fixtures/tests, and documented governed surface. It must
not add a source-specific job, bypass quarantine, or enable live acquisition.

Required evidence, and where each is now met:

| Required evidence | Met by |
|---|---|
| metadata validation rejects malformed rules before side effects | `load_spike_rule()` raises `ContractError`; 9 parametrised rejection cases |
| threshold changes alter the metadata hash without a code change | `rule_fingerprint()`; `test_threshold_change_alters_the_fingerprint_without_a_code_change` |
| boundary, negative, null, duplicate, timezone cases pass offline | `tests/nemweb/test_price_spike_detector.py`, 33 tests, no warehouse needed |
| Gold fields and metrics reconcile | `test_metric_reconciliation.py` reconciles all five measures against a hand-computed fixture |
| existing non-spike Gold fields remain stable | new materialized view only; no existing Gold module changed |

Rolling-window evidence does not apply, because no relative rule was approved.

## Implementation (2026-09-10)

Branch `feat/governed-dispatch-price-spike-detector`, **not committed**.

- `agentic_energy/resources/metadata/spike_rule.json` — the reviewed rule
- `agentic_energy/nemweb/spike.py` — Spark-free rule, fingerprint, and
  correction-then-effective-run-then-classify ordering
- `agentic_energy/nemweb/pipeline/gold_price_spikes.py` —
  `gold_nem_dispatch_price_spike_5min`
- `sql/nemweb_metric_views.sql` — `nem_dispatch_price_spike_metrics`
- `sql/nemweb_semantics.sql` — candidate-key gate plus two gates asserting the
  strict boundary and that a missing price is never flagged
- `sql/genie_benchmarks/07_regional_price_spikes.sql` — alert-ready query
- `dashboards/nemweb_overview.lvdash.json` — `ds_spikes`, a spike counter and a
  spike table under the KPI row

**The order of operations is the substance.** Corrections resolve first, then the
effective intervention run is selected, and only then is the threshold applied.
Applied in any other order, a superseded value or a non-effective run can create
a spike that never happened.

**Freshness labels, never filters.** A stale spike is reported and marked `STALE`.
Filtering stale rows out would make a real spike look like an absence of spikes.
Non-spiking intervals are retained for the same reason, so "no spikes" stays
distinguishable from "no data".

## Human review

- **Decision:** rule approved 2026-09-10; implementation **awaiting independent
  review**.
- **Reviewer:** pending — a person who did not draft the change must review the
  diff, and should confirm the 300 AUD/MWh rationale against current AEMO
  documentation before it is quoted to participants as market fact.
- **Evidence reviewed:** [`research/nemweb-contract.md`](../research/nemweb-contract.md)
  and the deterministic fixture contract.

## Session note

- **Result:** the measure is implemented and proved offline. 353 tests pass and
  the static asset gate reports 7 benchmarks and 7 dashboard statements.
- **Verified by mutation, not just by green tests.** Relaxing the Gold view's
  boundary from `>` to `>=` initially passed the whole suite — the offline tests
  covered the Python rule while the published answer came from the Spark module.
  Four static contract tests now bind the Gold view to the reviewed rule, and each
  of four mutations (boundary, threshold, skipped correction resolution, dropped
  effective-run filter) was re-run and confirmed to fail.
- **Not run.** No SQL was executed. The Gold view, the metric view, the benchmark
  and the dashboard datasets are contract-tested but have never run against a
  warehouse, and the dashboard has never been rendered. Those need workspace
  authorisation.
- **Open risks:** the threshold rationale is unverified against AEMO sources; the
  snapshot fixture contains no interval above 300 AUD/MWh, so a live or thickened
  window is needed to see a non-zero spike count end to end; the spike metric was
  deliberately not added to the Genie space asset set.
- **Next item:** independent review of the diff, then a pull request linked to
  [issue #3](https://github.com/dgokeeffe/agentic-energy-on-databricks-public/issues/3).
