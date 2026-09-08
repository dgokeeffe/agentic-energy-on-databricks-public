# Facility dimension: pinned effective instant

## Decision

`silver_nem_facility_dimension` now evaluates registration validity at a **pinned
instant derived from the data** — the maximum SCADA `interval_end` present in
Bronze — instead of `F.current_timestamp()`.

## The defect

The view selected the effective `DUDETAILSUMMARY` and `DUALLOC` rows like this:

```python
now = F.current_timestamp()
...
.where((F.col("start_date") <= now) & (F.col("end_date").isNull() | (F.col("end_date") > now)))
```

That `now` was not a metadata column. It sat in a `WHERE` clause, so it decided
**which rows existed**. The same Bronze data therefore produced different Silver
rows depending on when the refresh happened to run.

This is one of 22 `current_timestamp()` uses in the pipeline. The other 21 are
`gold_published_at` / `silver_published_at` labels, which never affect row
selection and are correct as they stand. Only this one was in a filter — confirmed
by grepping for `<= now`, `> now` and equivalents across the pipeline.

### Reproduction

Every DUID in the governed snapshot carries two registration periods, split at
13 July 2026:

```
ADPBA1  2026-07-01 → 2026-07-13  SA1
ADPBA1  2026-07-13 → 2999-12-31  SA1
```

Against a DUID whose region genuinely changes at that boundary:

```
as_of 2026-07-05 → region VIC1
as_of 2026-07-20 → region NSW1
```

No code change, no new source file, no failing expectation. A fully expired
registration resolves to `UNKNOWN` / `UNMATCHED`.

### Why it mattered downstream

`gold_nem_scada_generation_5min` groups by `region_id` and `fuel_type`, both from
this dimension. Re-attributing a DUID moves its generation between regional and
fuel buckets, which moves the revenue and capture figures the Track C app computes
from it — while every value on screen stays plausible. Same class of defect as the
[opening demo](opening-demo.md): the result cannot reveal it.

**Latent, not active, in the current snapshot.** Both periods there carry identical
region and fuel, so no value moves today. The mechanism is real; the trigger is
not present in the fixture.

## Why the test suite missed it

This is the part worth keeping.

There was already a correct, well-tested implementation:

```python
def build_facility_dimension(duids, dudetail, allocations, genunits, *, as_of: str)
```

It takes an explicit `as_of`, and all six tests in `test_facility_enrichment.py`
pinned it to `2026/07/15`. **The pipeline never called it.** `silver_facilities.py`
imported only `dp`, `F` and `Window`, and reimplemented the same three-way join in
PySpark with `current_timestamp()` substituted for the pinned parameter.
`grep -rn "as_of" agentic_energy/nemweb/pipeline/` returned nothing.

So the tested code and the deployed code had diverged on precisely the input that
was time-dependent. 290 foundation tests passed and none exercised the code that
runs. `test_snapshot_idempotency.py` covers landing and parsing only, never the
Spark layer.

## Why the maximum SCADA interval, not a config value

Three alternatives were considered.

**A bundle configuration value.** Rejected: it goes stale. Someone must remember to
advance it, and a forgotten value silently freezes the dimension at an old
registration.

**Calling `build_facility_dimension` from the pipeline.** The strongest fix, since
it would collapse the two implementations into one. Deferred as too large a change
to a table five Gold surfaces depend on, without a live gate to validate it. It
remains the right eventual direction.

**Maximum SCADA `interval_end` (chosen).** Derived, so it cannot go stale. It also
carries the better semantics: the dimension answers *which registration applied to
the market intervals this data describes*, rather than *which applies at the moment
the job ran*. The view stays a pure function of its inputs.

`COALESCE` to `1900-01-01` guards a cold or SCADA-empty schema: a NULL maximum
would make every `start_date <= NULL` comparison NULL and silently empty the
dimension. The floor yields UNKNOWN enrichment instead, which is visible in
`dimension_match_status`.

The instant is published as `registration_effective_at` on every row, so an
operator can read which registration window a refresh used.

## The guard, and the bug in the guard

`tests/nemweb/test_facility_dimension_determinism.py` checks two levels:

1. **Behavioural**, on the shared pure function: registration selection genuinely
   depends on the instant, identical inputs reproduce exactly, and an expired
   registration degrades visibly rather than disappearing.
2. **Structural**, on the deployed PySpark: no wall-clock time in a row-selecting
   filter, and the instant is derived from Bronze and published.

The structural checker is deliberately narrow — it flags clock calls only inside
`.where()` / `.filter()`, because the same call in a `select` is a legitimate
processing-time label used 21 times elsewhere.

**The first version of that checker passed against the real defect.** It only
inspected the filter expression, and the original code bound
`F.current_timestamp()` to `now` on one line and used `now` in the `where` two
lines later. The checker now tracks local names bound to a clock call, and
`test_the_guard_would_catch_the_original_defect` asserts both shapes plus the
label-only case that must *not* be reported.

Verified by reverting the view under `git stash`: 9 tests pass on the fix, and two
fail on the original defect, including the row-selecting clock check.

## Narrow audit of what the app reads

Scoped to the lineage behind the two tables the Track C app queries.

| Checked | Finding |
|---|---|
| SCADA correction dedup | Sound. `latest_correction` takes `row_number() == 1` on `(interval_end, duid)`, so one row per key. No double count. |
| Facility join fan-out | Sound. All three registration sources deduplicate to one row per key *before* joining, so the SCADA join cannot multiply rows. |
| `is_effective_run` on price | Sound, filtered at three levels: the `gold_nem_app_region_status` expectation, the Gold view itself, and the app's reviewed SQL. |
| `is_effective_run` on fuel | **Not applicable, and this is correct.** SCADA carries no intervention dimension at all, so there is nothing to filter and the absent `WHERE` clause on `latest_fuel_generation.sql` is right rather than an omission. |
| Wall-clock row selection elsewhere | None. Only `silver_facilities.py` used a clock in a filter. |

**Not audited**, and still open: interconnector and constraint join fan-out,
late-arriving Bronze against full materialized-view recomputation, the timezone
boundary between fixed AEST and session timezone, and full-recompute cost at
five-minute cadence. These sit outside the app's read path.

## Evidence and limits

Foundation suite 299 passed with 36 subtests, including the 9 new tests. Modern-API
check passes over 33 sources.

**The Spark view has not been executed.** The defect mechanism is proven with the
shared pure function and by static reading of the PySpark; runtime behaviour is
inferred from the code. Confirming it needs a workspace and an authorised run,
which the live gate has not closed.

## Human review

- **Decision:** fix approach chosen by the repository owner; implementation pending
  independent review.
- **Open question:** whether to collapse the PySpark reimplementation into
  `build_facility_dimension` so tested and deployed logic are the same code.
