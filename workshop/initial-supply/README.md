# Initial supply: regional actual SCADA output

This is a self-paced implementation exercise on `lab/initial-supply`, based on
`baseline-v1`. The reference implementation lives on `solution/initial-supply`.
The baseline on `main` has no exercise solution.

**Provisional scope assumption:** historical materials never define “initial
supply.” Here it means the first supply-side analytical product: observed signed
SCADA output grouped by region and five-minute interval. It is neither all supply
serving regional demand nor availability, a dispatch target, a forecast, or a
supply/demand balance. Imports, losses, rooftop PV and unobserved units are not
invented. This small SQL boundary can be revised if the requester intended
another meaning. See [scope evidence](../scope.md).

## Starting state

The baseline pipeline already selects source corrections and enriches each unit
with deterministic registration attribution. The app reads three Lakebase tables
and owns native investigations. The fixture is synthetic, non-live, and has NSW
regional prices only. The exercise adds one Gold MV to the same pipeline; no app
route, serving source, sync, or investigation schema changes are required.

The learner helper deliberately raises `NotImplementedError`. The library is
wired but must not be deployed until the exercise passes. `make check` validates
the retained baseline; `make lab-test` is the separate exercise acceptance gate.
A clean learner checkout must produce six failures at the marked stub.

```sh
git clone --branch lab/initial-supply https://github.com/dgokeeffe/agentic-energy-on-databricks-public.git energy-learner
cd energy-learner
make setup
make check
make lab-test
```

## Work the exercise

1. Inspect `docs/data-contracts.md`, `gold/gold_unit_dispatch.py` under
   `src/agentic_energy`, and the concrete Given/When/Then cases in `scenarios.json`.
   Record why negative battery values and UNKNOWN attribution must survive.
2. Write a short plan and have a peer or facilitator review it. Edit only
   `src/agentic_energy/labs/initial_supply.py` for the implementation. Tests,
   pipeline configuration, and existing data contracts are fixed inputs.
3. Implement `initial_supply_sql()` as a SELECT over
   `gold_nem_unit_dispatch_5min`. Return these columns, in order:

   | Column | Required behavior |
   |---|---|
   | `interval_end` | Original fixed-AEST interval, unchanged |
   | `region_id` | Preserve each source region, including UNKNOWN |
   | `actual_supply_mw` | Signed sum of `actual_generation_mw` |
   | `observed_unit_count` | Number of unique observed DUIDs |
   | `partially_enriched_unit_count` | Count where status differs from REGION_AND_FUEL |
   | `source_publication_at` | Latest nonnull UTC source publication, null if none |

   One row per `(interval_end, region_id)`. No input means no output, not a
   fabricated zero row. An observed zero remains present. Re-evaluation after an
   upstream correction changes the existing result without accumulating it.
   The supplied dataset wrapper adds `gold_published_at` as a processing instant.
4. Run `make lab-test` and `make check`. Do not skip or weaken a scenario.
   SQLite executes your actual SELECT locally; it does not prove Spark execution.
5. Ask the facilitator to deploy your reviewed revision into its assigned
   isolated environment, refresh the pipeline, and run the remote verification
   in the [facilitator runbook](../RUNBOOK.md). Record the exact revision and
   pipeline update ID. No baseline resource is a valid exercise target.
6. Review the result and limitations. Compare with the solution checkpoint only
   after the facilitator accepts your evidence. Explore the curated questions in
   `workshop/genie/` when the data passes verification.

## Evidence to retain

Record your starting and ending commits, red and green command exits, unchanged
scenario file, peer review decision, remote update ID, row/key reconciliation,
and any remaining uncertainty. Passing local tests is not a deployment claim.
Do not label prepared data live or claim that SCADA establishes availability.
