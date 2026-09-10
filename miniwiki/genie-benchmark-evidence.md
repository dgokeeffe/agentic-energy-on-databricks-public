# Genie benchmark evidence — issue #6

Evidence for issue #6, *Strengthen Genie supported-answer and refusal benchmarks*.

**Status of this material: snapshot, not live.** The newest source publication in
the queried deployment is `2026-09-02T01:30:00Z` against a capture date of
2026-09-10 — eight days stale. Nothing here may be cited as live AEMO evidence.

Captured 2026-09-10 by read-only query with `--profile DEFAULT`. No deployment,
no grant change, no job run, no schedule change. Host, token, account and
workspace identifiers are deliberately absent.

## Where the governed data was found

The foundation was already deployed and already readable; **no grant was
required.** An initial claim that this was blocked on permissions was wrong — it
came from sweeping 4 of 12 catalogs. A full sweep found:

| Catalog | Governed `nem_` tables |
|---|---|
| `<governed-catalog>` | **34** (schema `<governed-schema>` holds all 6 Genie assets) |
| four other readable catalogs | 0 |
| five further catalogs owned by other users | not readable |

The deployment belongs to another user. It was read, never written.

## Deterministic test 2 — supported-answer SQL reconciles with the source

Executed via the SQL Statement Execution API, polling each `statement_id` to a
terminal state. A CLI exit code was treated as transport evidence only.

| Benchmark | Terminal state | Rows | `expected_columns` match live manifest, exactly and in order | Verdict |
|---|---|---|---|---|
| `effective-intervention-uniqueness` | SUCCEEDED | 0 | yes | **pass** — 0 rows is the assertion |
| `regional-price-demand` | SUCCEEDED | 1 | yes | **pass** |
| `generation-by-fuel` | SUCCEEDED | 11 | yes | **pass** |
| `binding-constraints` | SUCCEEDED | 0 | yes | **pass** — row-count-independent |
| `interconnector-source-sign` | SUCCEEDED | 0 | yes | **fail** — below `minimum_row_count: 1` |
| `t1-unit-availability` | SUCCEEDED | 0 | yes | **fail** — below `minimum_row_count: 1` |

**All six reconcile structurally.** Every column contract matched the live result
manifest exactly and in order, which is the claim DT2 makes. Two fail their row
minimum.

### The two failures are a pre-existing snapshot gap, not a regression

Traced upstream to Bronze:

| Bronze table | Rows |
|---|---|
| `bronze_nem_dispatch_price` | 4 |
| `bronze_nem_dispatch_unit_scada` | 28 |
| `bronze_nem_dispatch_interconnector_res` | **0** |
| `bronze_nem_dispatch_constraint` | **0** |
| `quarantine_nem_dispatch_interconnector_res` | 0 |

The quarantine table is empty, so nothing was dropped or rejected: the synthetic
DISPATCHIS archive never carried the `INTERCONNECTORRES` or `CONSTRAINT`
sections. Both benchmarks and both `minimum_row_count: 1` values pre-date this
change.

`binding-constraints` has the same empty source but **passes**, because its
expectation was made row-count-independent (`empty_result_is_valid` plus a grain
contract) while remaining non-vacuous. `interconnector-source-sign` was
deliberately left at `minimum_row_count: 1` on instruction, so its failure stands
as a true signal about snapshot content. **No check was relaxed to obtain a pass.**

## Grain contracts verified against real rows

The `distinct_key_columns` contracts added in this change, checked against the
returned rows rather than synthetic fixtures:

| Benchmark | Key columns | Rows | Key tuples unique |
|---|---|---|---|
| `regional-price-demand` | `region_id` | 1 | yes |
| `generation-by-fuel` | `region_id`, `fuel_type` | 11 | yes |
| `binding-constraints` | `constraint_id` | 0 | yes (vacuously) |
| `interconnector-source-sign` | `interconnector_id` | 0 | yes (vacuously) |
| `t1-unit-availability` | `region_id`, `fuel_type` | 0 | yes (vacuously) |

`generation-by-fuel` is the only non-vacuous case, and it is the meaningful one:
11 distinct `(region_id, fuel_type)` tuples with no repeat confirms the declared
grain matches the statement's actual `GROUP BY ALL` output. Before this change
`_check_result_grain` had never run against real data.

## Supported-answer transcript

`regional-price-demand`, the case issue #6 names:

> Which NEM regions had the highest average dispatch price and demand over the
> last 24 hours?

| region_id | avg price AUD/MWh | max price AUD/MWh | avg demand MW | newest source publication | newest Gold publication |
|---|---|---|---|---|---|
| NSW1 | 255.0 | 260.0 | 7006.5 | 2026-09-02T01:30:00Z | 2026-09-10T01:51:50Z |

Reads correctly against the governed semantics: price in AUD/MWh kept distinct
from demand in MW, one region only (the snapshot holds one), and both freshness
columns present so the eight-day source lag is visible rather than implied.

`generation-by-fuel`, top rows:

| region_id | fuel_type | avg actual MW | est. energy MWh | partially enriched |
|---|---|---|---|---|
| SA1 | Solar | 40.5 | 6.75 | 0 |
| QLD1 | Solar | 40.0 | 6.667 | 0 |
| NSW1 | UNKNOWN | 23.5 | 3.917 | **2** |
| NSW1 | Solar | 21.5 | 3.583 | 0 |

`UNKNOWN` fuel remains visible rather than dropped, and the MWh figures satisfy
the `MW * 5 / 60` interval conversion (40.5 × 5/60 = 3.375 per interval, 6.75
across two). The `partially_enriched_observation_count` of 2 on the `UNKNOWN` row
is the governed disclosure working.

## Deterministic tests 1, 3 and 4

| Test | Result |
|---|---|
| Assets and SQL reference existing governed objects | **pass** — all 6 within the Genie asset set; every metric view defined in `sql/nemweb_metric_views.sql`; all 6 confirmed present in the live schema |
| Availability described as T+1 `Next_Day_Dispatch`, not five-minute Current | **pass** — instructions state Current does not publish five-minute availability and attribute it to daily T+1 `UNIT_SOLUTION` |
| Examples preserve effective-intervention handling and units | **pass** — 5 of 6 use `MEASURE()` with `GROUP BY ALL`; the 6th is the raw-Gold intervention audit, which must bypass metric views to inspect intervention rows |

## What remains unavailable

**Refusal transcript: `unavailable`.** Two Genie spaces matching the bundle's
`${var.resource_prefix}-analyst` pattern are deployed, but both belong to other
users and both pre-date this change, so neither carries the `## Refusal policy`
added here. Interrogating them would transcribe a different space's behaviour.
`nemweb_foundation/scripts/capture_genie_refusals.py` exists and is tested; it
needs a space carrying these instructions.

Per `lane_a_business/skills/06-benchmarks/SKILL.md`, `unavailable` is the correct
disposition rather than a substitute.

## Reproducing this

```bash
uv run --project nemweb_foundation python \
  nemweb_foundation/scripts/validate_nemweb_genie.py \
  --execute --profile DEFAULT \
  --catalog <governed-catalog> \
  --schema <governed-schema> \
  --warehouse-id <warehouse-id>
```

This stops at the first contract failure, which is `interconnector-source-sign`.
The per-benchmark table above was produced by iterating all six rather than
aborting, so the two failures did not mask the four passes.
