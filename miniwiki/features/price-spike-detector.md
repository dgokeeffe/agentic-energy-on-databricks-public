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

Questions to settle before implementation:

- Is the absolute rule `price_per_mwh > threshold`, and what threshold is the
  workshop default?
- Is there a relative rule such as `price > k × trailing median`, and which rule
  wins when both fire?
- Is the boundary strict (`>`) or inclusive (`>=`)?
- How are negative prices, missing prices, short rolling-window history, daylight
  saving transitions, and duplicate intervals handled?
- Who owns the metric definition and what freshness is expected?

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

Required evidence:

- metadata validation rejects malformed rules before side effects;
- threshold changes alter the metadata hash without a code change;
- boundary, negative, null, duplicate, rolling-window, and timezone cases pass
  offline;
- Gold fields, daily metrics, and manifest counts reconcile;
- existing non-spike Gold fields remain stable.

## Human review

- **Decision:** pending definition review.
- **Reviewer:** pending.
- **Evidence reviewed:** [`research/nemweb-contract.md`](../research/nemweb-contract.md)
  and the deterministic fixture contract.

## Session note

- **Result:** the feature is captured as a bounded horizon item; no pipeline code
  has been changed for it yet.
- **Open risks:** definition drift, null/negative price semantics, local-day
  timezone attribution, and live non-determinism.
- **Next item:** agree the rule and write a worked fixture example, then update
  [`now.md`](../now.md).
