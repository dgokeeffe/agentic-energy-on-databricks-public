# Give capture rate a governed definition, so everyone computes it the same way

**Track A · advanced · no Lakebase · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: advanced`, `area: genie`, `area: dashboard`

## Operator outcome

An analyst asking Genie for capture rate gets the same number the app shows, because
both read one governed definition instead of two independent implementations.

## Fits Stage 4: 90 minutes

Capture rate currently exists **only in TypeScript**, in
`nemweb_app/client/src/domain/fuelCapture.ts`. Genie cannot compute it, the dashboard
cannot show it, and any SQL an analyst writes will diverge from the app.

This is the exact shape of the defect this session found in the pipeline: one concept,
two implementations, no shared definition — and the copies drifted. Here you get to
prevent it rather than repair it.

The definition also has real edge cases already worked out in the TypeScript, which
must survive the move to SQL:

- capture rate is **withheld**, not zero, when energy is zero;
- withheld when the regional time-weighted price is at or below zero, because dividing
  inverts the sign and shows loss as outperformance;
- withheld for net consumption, because a battery buying cheaply is a good outcome the
  ratio would score as the worst;
- a charging battery's energy stays **negative**.

**If time runs short, define the measure and skip the dashboard tile.** A metric view
that reconciles to the app is a complete result.

## Where to start

- `nemweb_app/client/src/domain/fuelCapture.ts` — the authoritative definition today,
  including all three withholding cases.
- `nemweb_foundation/sql/nemweb_metric_views.sql` — existing metric views.
- `nemweb_foundation/tests/nemweb/test_metric_reconciliation.py` — the reconciliation
  pattern to follow.
- `nemweb_foundation/genie/nemweb_space.json`.

## Required change

- A metric view defining volume-weighted price, the regional time-weighted price, and
  capture rate over `gold_nem_scada_generation_5min` and
  `gold_nem_region_dispatch_5min`.
- The withholding rules expressed in SQL as `NULL`, not as `0`.
- Reconciliation proving the metric view and `fuelCapture.ts` agree on the same input.
- Genie instructions and one example query referencing the metric view.

Do not change the TypeScript semantics to make the SQL easier. If the two genuinely
cannot agree, that is a finding worth reporting rather than papering over.

## 30-minute checkpoint

The measure defined and returning a number for one region. Reconciliation and the Genie
example are the second half.

## Deterministic tests

- the metric view reconciles to `fuelCapture.ts` on identical input, to a stated
  tolerance;
- zero energy yields `NULL`, not `0`;
- a non-positive regional time-weighted price yields `NULL` for every fuel;
- net consumption yields `NULL` for capture rate while still reporting energy and
  revenue;
- signed energy is preserved for a charging battery;
- `is_effective_run` is filtered, so both intervention runs are not double counted;
- every canonical SQL statement executes against the target schema before any analyst
  asset is created or updated.

## Agentic eval

Did the agent read all three withholding cases out of the TypeScript, or implement the
happy path and return `0` for the rest? Returning `0` where the app returns "not
comparable" is the defect this exercise exists to prevent. Ask it to show the
reconciliation failing if it changes one rule deliberately.

## Evidence required

Approved plan, changed files, the reconciliation output, SQL execution output against the
target schema, and the Genie example with its result. Mark snapshot results as non-live.

## Limits

No change to the app's capture semantics to simplify the SQL. No new Gold table. No
Genie or dashboard asset created before its SQL has executed successfully. Executing
against a warehouse consumes compute and needs facilitator authorisation.
