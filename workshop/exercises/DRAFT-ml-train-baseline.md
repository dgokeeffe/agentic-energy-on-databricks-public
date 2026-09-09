# Train and register a price-spike baseline

**Track B or ML · advanced · Genie Code / agent-assisted · Visible today: NEEDS RICHER DATA**

Labels: `workshop`, `workshop-ticket`, `difficulty: advanced`, `area: ml`, `area: mlops`, `blocked: needs data`

> **Blocked, and the repository already says so.** `nemweb_ml/README.md`:
> *"too small to establish historical completeness, class balance, calibration, or
> predictive value. Passing its tests does not prove that a model is useful."*
>
> Measured: `tests/fixtures/history.json` has **6 rows**;
> `validate_training_eligibility` yields **train=3, validation=1, test=2**. The label is
> `label_price_spike_next_30m`, and the governed snapshot contains **0 negative prices and
> 0 corrections across 2 intervals of 1 region** — so there is almost certainly no spike
> variety to learn from either.
>
> A model can be fit. It would mean nothing. Do not schedule this until a facilitator has
> landed real history. See [`DRAFT-ml-refuse-to-train.md`](DRAFT-ml-refuse-to-train.md)
> for the version that is completable today.

## Operator outcome

An analyst can see a calibrated, honestly-evaluated probability that a region's price
spikes in the next 30 minutes, with the model's limits stated alongside the number.

## Why it is worth doing once unblocked

This is the exercise most people expect from an ML track, and it is the right shape:
`notebooks/train.py` stops at a deliberate `NotImplementedError` asking for "an
interpretable baseline on the approved chronological splits". The contracts around it are
already built and tested — leakage, chronological ordering, immutable model version,
feature and scoring times, source freshness, missing-feature status.

So the scaffolding is genuinely good. Only the data is missing.

## What "unblocked" requires

Real history with enough spike events to learn and evaluate on. One authorised live lander
run gives ~2 hours across 5 regions, which is **still not enough** for a 30-minute-ahead
spike label — you need days to weeks. That means MMSDM archive backfill, not just a live
cycle, which is why this is the most data-hungry exercise in the set.

State the minimum you need before starting, and get it agreed.

## Where to start

- `nemweb_ml/notebooks/train.py` — the stub.
- `nemweb_ml/src/nemweb_ml/features.py`, `split.py`, `contracts.py`, `train.py`.
- `nemweb_ml/tests/test_leakage.py` — the leakage contract, already enforced.
- `nemweb_ml/sql/gold_nem_predictions.sql` — the prediction surface.

## Required change

- An **interpretable** baseline. Logistic regression or a shallow tree, not a gradient
  boosting ensemble; the point is that a reviewer can read why it predicted what it did.
- Evaluation on the held-out chronological test period only, reporting a metric
  appropriate to a rare-event label. Accuracy on an imbalanced spike label is
  meaningless — say so and use something better.
- **Calibration**, reported honestly. A probability that is not calibrated is not a
  probability.
- Registration as `@challenger` only, never `@prod`.
- Prediction rows carrying immutable model version, feature time, scoring time, source
  freshness, and missing-feature status, per the existing contract.
- The app's existing prediction-stale handling must keep working: stale or missing input
  cannot produce an apparently current score.

## 30-minute checkpoint

Features and splits confirmed against the leakage contract, and the class balance measured
and reported. **If the label has too few positives, stop and report that** — it is a valid
and useful outcome, not a failure.

## Deterministic tests

- no feature is newer than its prediction time, and every label is in the future;
- splits are strictly chronological with no overlap;
- the reported metric suits an imbalanced label, and the class balance is stated;
- calibration is measured, not assumed;
- `@prod` is never touched;
- a stale or missing feature cannot yield an apparently current score;
- the existing eligibility gate is respected, not bypassed.

## Agentic eval

Did the agent report accuracy on an imbalanced label? Did it check class balance before
choosing a metric? Did it reach for an uninterpretable model despite the requirement? Ask
what its calibration plot shows and what it would tell an operator who asked "should I
trust this at 0.7?" Ask whether it verified the data was sufficient before training, or
trained first and rationalised after.

## Evidence required

Approved plan, the minimum-data agreement, changed files, class balance, the chosen metric
with justification, calibration evidence, test output, the registered model version and
alias, and an explicit statement of what the model cannot be used for.

## Limits

No `@prod` alias change. No Model Serving endpoint. No registration without passing the
eligibility gate. No accuracy claim on an imbalanced label. No presenting a snapshot-fitted
model as evidence of predictive value. Training consumes compute and needs facilitator
authorisation.
