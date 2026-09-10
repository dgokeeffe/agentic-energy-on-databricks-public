# Registration coverage: measuring publication time, not market time

Status: implemented on `feat/registration-attribution-freshness`, open as a draft
pull request. Decided 2026-09-10.

Companion to [`facility-dimension-as-of.md`](facility-dimension-as-of.md), which
pinned the dimension's effective instant. That fix made the instant reproducible;
this one makes its **staleness** detectable.

## What prompted it

Public issue #7 asked to surface registration attribution freshness on the Track C
value-capture screen. Two gaps were real and confirmed by grep:
`registration_effective_at` was written by `silver_facilities.py` and read by no
Gold surface, and `registration_enrichment_quality()` was called only from its own
test.

The underlying risk is genuine. `gold_nem_scada_generation_5min` groups by
`region_id` and `fuel_type`, both from a dimension built from **monthly** MMSDM
registration, while generation is **five-minute** SCADA. A stalled monthly load
attributes generation to the wrong region or fuel, and every revenue and capture
figure moves while each value stays plausible.

## The decisive finding: the issue's own metric cannot fire

Issue #7 asked to "report the lag between the registration instant and the market
intervals being priced." **That subtraction is identically zero by construction.**

- `registration_effective_at` = `COALESCE(MAX(interval_end), …)` over
  `bronze_nem_dispatch_unit_scada` — `silver_facilities.py:48-50`.
- The Gold product aggregates `silver_nem_dispatch_unit_scada`
  (`gold_scada_generation.py:22`), which is
  `latest_correction(bronze_nem_dispatch_unit_scada)` (`silver_scada.py:17-18`).
  Correction dedup picks one row per `(interval_end, duid)`; it never introduces a
  new maximum interval and never removes the existing one.

Both sides are `MAX(interval_end)` of the same table. Implementing the issue
literally would have shipped a freshness indicator permanently reading zero — a
green check proving only that it was wired to itself, which is the same class of
defect as the one recorded in
[`../workshop/agent-practice/green-tests-wrong-code.md`](../../workshop/agent-practice/green-tests-wrong-code.md).

An independent reviewer verified this claim rather than accepting it.

## Rejected alternative: market-time coverage

`MAX(interval_end) − MAX(dudetail.start_date)` was the obvious repair and is
wrong twice over.

- `start_date` only advances when a registration actually **changes**. A stable
  fleet drifts toward "stale" on a perfectly fresh load. Measured against the
  governed snapshot it reports **2750 days stale** where publication-time coverage
  correctly reports 26 hours healthy.
- It goes **negative** whenever AEMO ships future-effective registrations, which
  the snapshot does — the same two-period shape
  `test_facility_dimension_determinism.py:38-53` was built around.

Both rejected designs are now encoded as tests
(`test_registration_coverage.py::test_coverage_is_not_the_difference_of_a_column_with_itself`
and `::test_a_fresh_load_of_an_unchanged_fleet_reads_healthy`) so neither can be
silently reintroduced by someone who reads the issue and not this page.

## What was built

```
registration_coverage_seconds =
    MAX(scada.source_publication_at)                       -- UTC
  − oldest(per-table MAX(registration.source_publication_at))  -- UTC
```

UTC−UTC, so it never crosses the fixed-AEST market domain. Three load-bearing
choices:

- **The oldest of three sources governs.** `genunits` alone supplies fuel
  (`silver_facilities.py:100`), so a stalled GENUNITS load must not be masked by a
  fresh DUDETAILSUMMARY. `F.min`, never `F.max`.
- **Signed, never clamped.** Negative means registration was published after the
  SCADA — ordinary for a monthly source landing behind five-minute intervals.
- **Measured on pre-filter frames.** After the `_rank == 1` window it would
  describe the surviving row rather than the load, and coverage is a property of
  the load.

`is_assessable` is a fail-closed third state. A near-zero coverage under a degraded
basis is evidence of nothing, because the publication instant was fabricated from
our own retrieval time. "Not assessable" is therefore distinct from "fresh", and
collapsing the two is the failure the contract exists to prevent.

Threshold is 45 days (`quality.py`), derived from the monthly cadence: 31 days
between archives by definition, plus AEMO's publication delay into the following
month, plus the lander's own 35-day lookback. Under ~35 days it alarms every normal
month; beyond ~60 a wholly skipped archive passes unnoticed for two cycles.
Deliberately **not** the app's `SOURCE_STALE_AFTER_MS` (15 minutes), which is
calibrated for five-minute SCADA and four orders of magnitude out.

## What the tests do not establish

**The pipeline hops are statically proven and runtime-unverified.** `pyspark` is not
a test dependency (`pyproject.toml:17` is `pytest` + `pyyaml`), so no local test
executes PySpark. The `F.min` across three sources, the `F.max` aggregates, the
pre-filter placement, and the `ALTER TABLE` have never run against a cluster.

This is exactly the divergence that shipped the previous defect in this view. The
mitigation is that the rule lives in a pure, behaviourally-tested function and
seven structural guards bind the deployed expression to it — including an AST check
that market time is never differenced against a UTC instant, mechanising the issue
#22 defect class rather than leaving it to a comment.

Confirming runtime behaviour needs an authorised workspace run with
`--profile DEFAULT`, schedules PAUSED and `allow_live_nemweb` false.

## Guard quality: four of the author's own tests were inadequate

Every guard was mutation-tested for its ability to **fail**, on the principle that
a guard never shown failing is indistinguishable from one that cannot fail. Four
were caught doing nothing:

1. **A structural guard permitted its worst regression.** Dropping
   `bronze_nem_genunits` from the coverage tuple — the fuel source, the leg whose
   staleness matters most — passed all 17 guards, because the test asserted the
   name appeared *somewhere* in the file and it still did, in an unrelated window.
   **Substring presence is not membership.** Now read from the AST.
2. **A staleness guard could not detect its own removal.** A degraded basis was
   tested only at 30 seconds coverage, so deleting the `assessable &&` guard from
   `stale` passed all 96 tests — the threshold was not crossed either way. Now
   tested at 200 days.
3. **A boundary assertion would have been satisfied by deleting the boundary.** A
   no-curtailment check scanned the whole page, where other sections legitimately
   mention curtailment *in order to deny it*. Now scoped to the provenance note.
4. **The same mistake again**, one commit later: an `autoMerge` assertion failed on
   the comment explaining why autoMerge is deliberately not used. Now checks
   executable SQL only.

Pattern worth carrying forward: **three of the four were over-broad substring
assertions that the correct code satisfied accidentally, and that deleting an
explanation would also have satisfied.** Assert on structure or on scoped elements,
not on whole-file text.

## A `.pyc` hazard in this repository

A same-size `<` → `>` mutation **survived a file restore**. CPython validates
bytecode cache on (mtime, size), so the mutant `.pyc` was still being executed
after the source was correct again. Mutation runs here need `__pycache__` cleared
between iterations, or a mutation can appear caught when it was not — the mirror
image of green-tests-wrong-code.

## Open, and needing a human

- **E1, still to be filed, and worse than first described.** A draft body is
  prepared. Two corrections to the original note, both verified:

  - **The blast radius is 8 Bronze tables, not the 3 registration ones.**
    `io.py:281` sits in `section_stream`'s `subject_key` branch, which also serves
    `dispatch_price`, `dispatch_region_sum`, `dispatch_constraint`,
    `dispatch_interconnector_res` and `dispatch_unit_scada` — 8 of the 9
    `CRITICAL_TABLES`. The 6 legacy-branch call sites (bids, trading, settlement,
    unit_solution_t1) inherit the **correct** basis from the manifest. So
    `source_publication_basis` currently means two different things across Bronze,
    which is worse than being uniformly wrong. An earlier version of this page said
    "every Bronze table using `section_stream`"; that is not exact.
  - **There is a second, independent fabrication upstream, and repairing
    `io.py:281` alone would leave the deployed job still lying.**
    `scripts/land_nemweb_delta.py:49` does
    `item.get("source_publication_at") or item["retrieved_at"]` **before**
    `lander.py:432` tests the same field, so `archive.source_publication_at` is
    never falsy on the deployed path and the `retrieval_fallback` arm is
    **unreachable**. Confirmed by contrast: `land_snapshot` passes the value
    uncoalesced (`lander.py:532`) and does yield `retrieval_fallback` for all six
    fixture archives. The deployed entrypoint is
    `resources/nemweb_lander.job.yml` → `scripts/land_nemweb_delta.py`.
  - The Delta landing path also has **no basis column at all** to project from —
    `delta_lander.py:177` (DDL), `:25-33` (`LandingProvenance`), `:123-127` all
    lack it. So the fix is not a one-line change at `io.py:281`.

  Consequence here: the **basis leg of the degradation guard is inert**, and the
  timing heuristic (publication implausibly close to `landed_at`) is what actually
  fires. Until this is fixed, treat `source_publication_basis` as unreliable.

  Also note the snapshot manifest **omits the `source_publication_at` key
  entirely** rather than setting it null, so under snapshot mode the fallback path
  is 100% of rows. Existing Bronze rows are therefore known-wrong rather than
  merely unverified, and forward-only is not obviously sufficient — a facilitator
  needs to check deployed row counts before choosing a migration.
- **E2, needs a facilitator decision:** all six snapshot manifest artifacts have
  `source_publication_at: null`, so the default path renders "not assessable".
  Correct behaviour, invisible demo. **Anyone assigning #7 as a workshop exercise
  gets a feature that never shows its interesting state.** Re-cutting the snapshot
  is a fixture-provenance decision.
- **The coverage columns are not deployed.** Queried
  `system.information_schema.columns` on 2026-09-10: the serving table carries
  eleven columns and none of the four this change publishes. That shape is now a
  test fixture, because it is what the app meets between merge and the next
  authorised deployment.
- **A tautological expectation, relevant to issue #2:**
  `gold_scada_generation.py:17-19` asserts
  `partially_enriched_facility_count BETWEEN 0 AND facility_count`, which
  100%-UNKNOWN data satisfies perfectly — 14 of 14 is a valid subset of 14. The
  real protection is the market-wide assertion at `nemweb_semantics.sql:58-72`,
  which already exists.
- **Cross-language duplication remains.** `STALE_REGISTRATION_AFTER_SECONDS` is
  written twice, in Python and TypeScript, coupled only by a test that reads both
  literals. A repo-wide constant-sharing mechanism would be better and does not
  exist.
