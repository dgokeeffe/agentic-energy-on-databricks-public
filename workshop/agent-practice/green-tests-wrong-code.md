# Facilitator demonstration: green tests, wrong code

A short demonstration, drawn from a real defect found in this repository's own
Lakeflow pipeline. It is **not** a participant exercise and adds no clock pressure.
Placement and rehearsal are pending facilitator approval, as with the rest of
[agent practice](README.md).

## The question it asks

> **Where does your test suite touch the code that actually runs?**

## The setup, in three artefacts

Show these in order. Each looks correct on its own.

**1. A well-tested pure function.** `agentic_energy/nemweb/corrections.py`:

```python
def build_facility_dimension(duids, dudetail, allocations, genunits, *, as_of: str)
```

`as_of` is a required keyword argument. Six tests in
`tests/nemweb/test_facility_enrichment.py` exercise it, every one pinning
`as_of="2026/07/15 00:00:00"`. Region completeness, fuel coverage above 90%,
DUALLOC fallback, open-ended registration, pseudo-units. It is genuinely good
test coverage.

**2. The deployed pipeline.** `agentic_energy/nemweb/pipeline/silver_facilities.py`,
as it was:

```python
now = F.current_timestamp()
...
.where((F.col("start_date") <= now) & (F.col("end_date").isNull() | (F.col("end_date") > now)))
```

It imports `dp`, `F` and `Window`. **It does not import `build_facility_dimension`.**
It reimplements the same three-way MMSDM join in PySpark, with
`current_timestamp()` where the tested function took a pinned parameter.

**3. The suite passing.** `make foundation-test` → **290 passed**.

## The reveal

Ask the room what the test suite proves about the pipeline. Then run:

```bash
grep -rn "as_of" nemweb_foundation/agentic_energy/nemweb/pipeline/
```

Nothing. The deployed pipeline has no `as_of` concept at all. The tests and the
pipeline are two different implementations of the same join, and they diverge on
exactly the input that is time-dependent.

## Why it is a real defect, not a style complaint

That `now` sits in a `WHERE` clause, so it decides **which rows exist** — not what a
timestamp column says. Every DUID in the governed snapshot carries two registration
periods, split at 13 July 2026:

```
ADPBA1  2026-07-01 → 2026-07-13  SA1
ADPBA1  2026-07-13 → 2999-12-31  SA1
```

Demonstrate the consequence with the tested function, which makes the instant
explicit:

```
as_of 2026-07-05 → region VIC1
as_of 2026-07-20 → region NSW1
```

Same Bronze data. Different Silver output. No code change, no new source file, no
failing expectation.

`gold_nem_scada_generation_5min` groups by `region_id` and `fuel_type`, so a
re-refresh across a boundary moves generation between regional and fuel buckets —
and moves the revenue and capture figures the Track C app computes from them. Every
number on screen stays plausible.

Worth stating plainly: in the current snapshot both periods carry identical region
and fuel, so **nothing moves today**. The mechanism is real; the trigger is not in
the fixture. Distinguish a proven mechanism from an observed failure.

## The second lesson, which is the better one

The first version of the guard written for this defect **passed against the defect
it was written to catch.**

It walked the AST for clock calls inside `.where()` and `.filter()`. But the
original code did not write the call in the filter. It bound it to a variable on
one line and used the variable two lines later:

```python
now = F.current_timestamp()          # line 15
... .where(F.col("start_date") <= now)   # line 24
```

The checker inspected the filter expression, found only a `Name`, and reported
clean. A guard that has never been shown to fail is indistinguishable from one that
cannot fail.

The fix tracks local names bound to a clock call, and
`test_the_guard_would_catch_the_original_defect` now asserts three shapes: the
inline call, the via-variable call, and a label-only `select` that must **not** be
reported. Verified by reverting the view under `git stash`: 9 pass on the fix, 2
fail on the original.

## What to draw out

- Green tests measure the code they touch, nothing else. "290 passed" was true and
  told you nothing about the pipeline.
- Duplicated logic diverges silently. The second implementation is where the
  parameter quietly becomes a clock call.
- Agent speed changes how fast a plausible second implementation appears, not
  whether this defect class exists. A human writes the same bug more slowly.
- A new check must be shown to fail before it is trusted. Revert the fix and watch
  it go red.
- Non-determinism in a `WHERE` clause is a different category from non-determinism
  in a `SELECT`. This pipeline has 21 of the harmless kind and had exactly one of
  the other.

## Sources

- [`miniwiki/decisions/facility-dimension-as-of.md`](../../miniwiki/decisions/facility-dimension-as-of.md)
  — the defect, the reproduction, three rejected alternatives, and the narrow audit.
- `nemweb_foundation/tests/nemweb/test_facility_dimension_determinism.py` — the guard.
- [`opening-demo.md`](../../miniwiki/decisions/opening-demo.md) — the same defect
  class reached from the result side rather than the test side.
