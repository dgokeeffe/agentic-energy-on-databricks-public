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

Questions settled on 2026-09-10, in the order they were asked:

- **Rule shape: relative only.** A price is a spike when it reaches a multiple of
  the median of the preceding intervals for the same region. No absolute rule, so
  no precedence question arises. A fixed dollar threshold cannot be regionally
  fair: it never fires in a normally-cheap region and fires constantly in an
  expensive one.
- **Boundary: inclusive (`>=`).** A price exactly on the multiple is a spike.
- **Baseline: 288 preceding intervals (24 hours), excluding the judged interval.**
  Excluding it matters — a spike included in its own baseline shifts the median
  upward and masks itself.
- **Threshold: parameterised, no default.** `nemweb.spike_baseline_multiple` is a
  required pipeline setting. The threshold is a market judgement, not an
  engineering constant.
- **Insufficient history: `NULL`, not `false`.** "We cannot tell yet" is a
  different claim from "we checked and found nothing".
- **Negative and zero baselines: withheld.** NEM prices go negative, and
  `-500 >= 3 × -100` is arithmetically true and market nonsense; against a zero
  median every positive price is an infinite multiple.
- **Administered and suspended prices: labelled, not excluded.**
  `price_formation_basis` carries `ADMINISTERED` / `SUSPENDED` / `MARKET`.

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

- **Decision:** rule agreed 2026-09-10; implementation authorised and complete
  locally. Not deployed.
- **Reviewer:** the requester settled all seven definition questions above in
  session. **A named market reviewer has still not signed off the threshold
  value**, which is why the value is a required parameter rather than a committed
  number.
- **Evidence reviewed:** [`research/nemweb-contract.md`](../research/nemweb-contract.md)
  and the deterministic fixture contract.

## Implementation

The rule lives in two places, deliberately:

- `agentic_energy/nemweb/corrections.py` — `mark_price_spikes()`, pure Python,
  behaviourally tested in `tests/nemweb/test_price_spike_rule.py`.
- `pipeline/gold_additional_aggregates.py` — `gold_nem_dispatch_price_spike_5min`,
  the deployed PySpark window, pinned by static assertions in
  `test_gold_contracts.py`.

**Why both.** A trailing median is a window function and a Databricks metric view
`expr:` must be an aggregate, so the window cannot live in the metric view; and
`test_metric_reconciliation.py` asserts measure expressions verbatim, so the
threshold cannot be a SQL parameter there either. The metric view
`nem_dispatch_price_spike_metrics` therefore only aggregates the Gold columns.

The two-layer test split is deliberate for a second reason. `facility-dimension-as-of.md`
records a defect where a well-tested pure function was reimplemented in PySpark
with one input substituted, so the tests confirmed the assumption rather than the
deployed behaviour. The static test here asserts `rowsBetween(-288, -1)` and
rejects `-288, 0`, which is that exact failure shape for this rule.

## Session note

- **Result:** implemented locally and validated. Both test layers were
  **mutation-checked**: eight deliberate defects were introduced one at a time
  (self-inflating baseline, `NULL`→`false`, dropped negative-baseline guard,
  boundary flipped to strict, dropped effective-run filter, frame end `-1`→`0`,
  hard-coded threshold) and each was caught by the specific test written for it.
- **Known limitation, not a defect:** the snapshot fixture spans about two hours,
  and the baseline needs 24. `is_price_spike` is therefore `NULL` for every
  fixture row, so the rule is proven by unit tests and **not** demonstrated
  end-to-end on snapshot data. Do not shorten the window to make a demo light up;
  thicken the fixture or state the limitation.
- **Open risks:** the threshold value itself is unset and unreviewed; window
  performance at sustained five-minute cadence is unmeasured; no live cycle.
- **Unverified and blocking a deployment claim: `F.median()` over a `ROWS BETWEEN`
  frame has not been executed.** The Databricks `median` reference says it "can
  also be invoked as a window function using the `OVER` clause", but percentile
  functions are documented elsewhere as accepting only `RANGE` frames, and this
  repository has no precedent — every other window use is `row_number()`. PySpark
  is not installable in the authoring environment, so the plan was never analysed.
  **The first authorised dev run must confirm the view analyses at all.** If it
  raises on the `ROWS` frame, the fallback is `collect_list` over the same frame
  with `percentile_approx` applied to the resulting 288-element array; the pure
  function, the tests, and every governed surface stay unchanged, because only the
  median mechanism moves.
- **Next item:** a named reviewer sets `BUNDLE_VAR_spike_baseline_multiple`, then
  an authorised deployment exercises Gate 5 metric reconciliation.
