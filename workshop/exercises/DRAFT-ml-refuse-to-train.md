# Make the training job refuse to register a model that proves nothing

**Track B or ML · core · Genie Code / agent-assisted · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: ml`, `area: mlops`

## Operator outcome

A training run on insufficient data **fails loudly and says what is missing**, instead of
producing a registered model with a plausible metric that nobody can rely on.

## Fits Stage 4: 60–90 minutes, and it is the honest ML exercise here

Read the ML starter's own README first:

> The checked-in July 2026 fixture is deterministic prepared data derived from the
> workshop schema. It is **too small to establish historical completeness, class balance,
> calibration, or predictive value. Passing its tests does not prove that a model is
> useful.**

I measured it. `tests/fixtures/history.json` has **6 rows**, and
`validate_training_eligibility` splits them into **train=3, validation=1, test=2**.

So a model *can* be fit. Three training rows. Any accuracy figure it produces is
meaningless, and `notebooks/train.py` currently stops at a deliberate
`NotImplementedError` telling the participant to train "an interpretable baseline".

**That gap is the exercise.** Not "train a model on three rows" — that teaches the wrong
lesson and would be the ML equivalent of the fuel mapping I built from guessed strings
this session, where the test confirmed my assumption rather than the behaviour.

Instead: make the pipeline **refuse**. Add the eligibility gate the README says is
required but that nothing enforces, so an insufficient dataset cannot reach registration.
That is a genuinely useful MLOps habit and it is completable in the slot.

## Why this suits Genie Code with agent assistance

The work is small in volume but demands reading three contract modules and the README
carefully before writing anything. An agent is good at that; the risk is that it
enthusiastically trains a model and reports 100% accuracy on two test rows. Catching that
tendency is part of the exercise.

**If time runs short, implement the gate and skip the baseline entirely.** A refusal with
a clear message and its tests is the complete result.

## Where to start

- `nemweb_ml/README.md` — read the limits paragraph first; it is the requirement.
- `nemweb_ml/src/nemweb_ml/train.py` — 33 lines. `validate_training_eligibility`,
  `configure_mlflow`, `register_challenger`.
- `nemweb_ml/src/nemweb_ml/split.py` — `chronological_split`.
- `nemweb_ml/src/nemweb_ml/contracts.py` — `validate_training_rows`.
- `nemweb_ml/notebooks/train.py` — the `NotImplementedError` stub.
- `nemweb_ml/tests/test_split.py`, `test_leakage.py` — existing gates to extend.

## Required change

- An explicit eligibility gate with **named, justified minimums**: rows per split,
  distinct prediction times, distinct regions, and label class balance. State why each
  threshold is what it is; a number with no reasoning is not a gate.
- The gate raises with a message naming exactly which condition failed and by how much,
  not a generic "insufficient data".
- `register_challenger` cannot be reached when the gate fails. Prove it.
- The 6-row fixture must **fail** the gate. That is the correct outcome, and your test
  should assert the failure rather than work around it.
- A second, larger synthetic fixture that **passes** the gate, so both paths are tested.
  Label it clearly as synthetic and state that passing does not imply predictive value.

Do not lower a threshold to make the existing fixture pass.

## 30-minute checkpoint

The gate implemented with justified thresholds, and a test proving the 6-row fixture is
refused. The passing fixture and the registration-blocked test are the second half.

## Deterministic tests

- the 6-row fixture is refused, and the message names the failing condition and its
  actual versus required value;
- a sufficient synthetic fixture passes;
- `register_challenger` is unreachable on a failed gate — assert it is never called, do
  not merely assert the gate raised;
- the existing leakage and chronological-split tests still pass unmodified: features no
  newer than prediction time, labels in the future, strictly ordered splits;
- a single-class label set is refused even when row counts are sufficient;
- `@prod` is never touched, and no Model Serving endpoint is defined.

## Agentic eval

**The most likely failure is enthusiasm.** Did the agent train a model and report a
metric on two test rows? Ask what its reported accuracy means with `n=2`; a good answer
says "nothing". Did it justify every threshold, or pick round numbers? Did it lower a
threshold so the shipped fixture would pass?

## Evidence required

Approved plan with the thresholds and their justification, changed files, test output
showing both refusal and pass, and an explicit statement that no model was registered and
no predictive claim is made.

## Limits

No `@prod` alias change. No Model Serving endpoint. No registration on a failed gate. No
threshold weakened to accommodate the existing fixture. No claim of predictive value from
any fixture in this repository. Training on a workspace consumes compute and needs
facilitator authorisation; the gate and its tests run locally.
