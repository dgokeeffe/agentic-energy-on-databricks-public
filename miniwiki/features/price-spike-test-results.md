# Test results — governed dispatch-price spike measure

Evidence record for [`price-spike-detector.md`](price-spike-detector.md) and pull
request #26. Every figure below was produced by running the command shown, on the
commit shown, and not carried over from an earlier session.

- **Commit:** `2864988` on `feature/governed-dispatch-price-spike-measure`
- **Run at:** 2026-09-10 04:29 UTC
- **Workspace touched:** read-only queries only. No resource created, changed or
  deployed.

## Suites, against the `main` baseline

Baseline measured from a temporary worktree of `main`, not quoted from memory.

| Suite | `main` | This branch | Added |
|---|---|---|---|
| Foundation (`make foundation-test`) | 265 passed | **479 passed** | +214 |
| Root (`make test`) | 320 passed + 37 subtests | **534 passed + 37 subtests** | +214 |

## Spike-specific test files

| File | Result | What it fixes in place |
|---|---|---|
| `test_price_spike_rule.py` | 21 passed | The agreed decisions: inclusive boundary, `NULL` not `false`, negative and zero baselines withheld, plateau stops registering, regions independent |
| `test_price_spike_properties.py` | **175 passed** | Invariants over 25 seeded series: verdicts unchanged under positive rescaling, so an absolute threshold cannot hide inside a relative rule; regions never influence each other |
| `test_spike_threshold_config.py` | 9 passed | The threshold has no default anywhere in the bundle; 288 is stated identically across every surface |

## Mutation guard — 10 of 10, exit 0

`make mutation-spike`

```
Baseline green. Injecting 10 mutants one at a time.
  caught    baseline-includes-judged-interval
  caught    insufficient-history-returns-false
  caught    non-positive-baseline-not-withheld
  caught    boundary-becomes-strict
  caught    effective-run-filter-dropped
  caught    deployed-frame-includes-current-row
  caught    deployed-null-becomes-false
  caught    deployed-median-reverts-to-median-function
  caught    deployed-median-becomes-approximate
  caught    deployed-threshold-hard-coded

All 10 mutants caught by their intended tests. Sources restored.
```

Each mutant must be caught by the *specific* test written for it. Being caught by
an unrelated test also fails the guard, because that means the intended guard is
gone and something incidental noticed.

**The guard was itself verified by breaking a test**, not by trusting a green run:
relaxing the boundary assertion to accept either verdict made
`boundary-becomes-strict` **survive** and the script exit 1. Restoring it returned
exit 0 with a clean `git diff`. A guard that can never fail is indistinguishable
from a working one until you try this.

## Workspace SQL verification — exit 0, read-only

`verify_spike_sql_semantics.py --profile <name> --warehouse-id <id>`

```
Read-only: every case runs over range() literals. No table is read or created.
  ok  median() rejects a window frame
  ok  percentile_approx diverges from an exact median
  ok  percentile() matches statistics.median exactly
  ok  full rule agrees with the pure-Python rule
```

This is the only result here that reached Databricks, and it is the one that found
a real defect. The measure originally shipped `F.median()` over a `ROWS` frame:

| Mechanism | Accepted over `ROWS`? | Exact? | Used |
|---|---|---|---|
| `median(x)` | **no** — `INVALID_WINDOW_SPEC_FOR_AGGREGATION_FUNC` | — | no |
| `percentile_approx(x, 0.5)` | yes | **no** — returns `0.0` for `[0, 1]` where the median is `0.5` | no |
| `percentile(x, 0.5)` | yes | yes | **yes** |

The middle row is the trap. `percentile_approx` is accepted, so it looks like the
fix, but it would have left the pipeline green while silently disagreeing with
every test above. Two mutants now guard against reverting to either.

The full rule was also checked end to end over 330 synthetic intervals: `NULL`
before interval 288, `false` at 288, `true` on the spike, `false` at 149.99 and
`true` at exactly 150.0 — matching the pure-Python rule at every boundary.

## Remaining gates

| Gate | Result |
|---|---|
| `make miniwiki` | 19 pages, relative links resolve |
| `make links` | 120 tracked files |
| `make safety` | 436 candidate files |
| `make modern-apis` | 33 Python sources |
| `make foundation-snapshot` | manifest `9d2e577a…`, `live_evidence=False`, 103 rows, 0 quarantined |
| `git diff --check` | clean |

## What these results do NOT establish

A green suite is not the same as a working deployment. Three things remain unproven,
and none is closed by anything above.

**CI has never run.** Every figure here came from one sandbox.
`.github/workflows/ci.yml` is held in a local commit because pushing it needs the
`workflow` OAuth scope. The YAML parses and every `make` target it names exists,
but `setup-uv` resolution and the app job's label condition are untested. Expect
the first run to need adjustment.

**No Lakeflow pipeline has run.** The SQL semantics are proven; the view has never
been materialised, so nothing confirms it publishes, clusters, or passes its
expectations in a real update.

**No spike has ever fired on real data.** Verified read-only against the richest
deployment in the workspace:

| | |
|---|---|
| Intervals per region | 137, against the 288 required — short by ~12.6h each |
| ETL jobs | all `PAUSED`, so the window is not growing |
| Observed price range | −58.68 to 119.02 against a ~$50 median |

At a 3× multiple nothing would fire even with enough history. So the tests prove
the rule is correctly *withheld* and correctly *computed*, never that it detects a
real spike. Demonstrating that needs either ≥24h of continuous data or a purpose-built
fixture — **not** a shortened window, which would make the rule indefensible.

The threshold value itself remains unset and unreviewed by design.
