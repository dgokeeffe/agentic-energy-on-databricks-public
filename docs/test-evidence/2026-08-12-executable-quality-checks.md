# Test evidence — executable quality checks and manifest watermark

| | |
|---|---|
| Captured (UTC) | 2026-08-12 |
| Commit | `73f66f15ccc4397c5753ab71db5874199908f3f1` |
| Beads issue | `agentic-energy-g77` — Engineering: inspect and improve the metadata contract |
| Acceptance stages | B1 (understand the contract), B2/B4 (bounded improvement with tests) |
| Python / pytest / uv | 3.10.12 / 9.1.1 / 0.10.2 |
| Suite | **107 passed** |
| Fixture baseline | unchanged — `bronze=11, silver=6, quarantine=3, gold=3`, all 6 data artifact hashes identical |
| Overall | **PASS** |

Relationship to the two existing records in this directory: they were captured
against a different local Beads graph, where these two pieces of work are
`agentic-energy-93y` (foundation) and `agentic-energy-zwh` (metadata contract).
This record's `agentic-energy-g77` is the same *metadata contract* work item
under a graph seeded separately. Notably
[`2026-08-12-metadata-contract-validation.md`](2026-08-12-metadata-contract-validation.md)
independently observed the defect fixed here, recording
`unknown quality-check expr → exit=0 ACCEPTED SILENTLY`. That row is what this
change closes.

## The defect (stage B1)

Each source in the contract declares `quality_checks`, but **no line of code read
them**. Row validation was hardcoded behind an `is_market` branch, so editing
`quality_checks` in the contract looked effective and did nothing.

Demonstrated by appending a check no fixture row can satisfy —
`demand_mw >= 999999` — to `aemo_dispatch_fixture` and running the same mutated
contract against both revisions:

```text
--- PRE-CHANGE code (76cb812), mutated contract ---
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3     <- unchanged: check ignored

--- CURRENT code (73f66f1), same mutated contract ---
Pipeline complete: bronze=11, silver=3, quarantine=7, gold=0     <- check now bites
```

The declared rule is now the rule that runs.

## Unsupported expressions are refused, not skipped

The evaluator is a manual parser over a strict allowlist. There is deliberately
no `eval`/`exec` anywhere near contract data, which is attacker-influenced input
in any real deployment. Exactly two forms are supported:
`<field> is not null` and `<field> >= <number>`.

Anything else fails validation. Verbatim, one run per expression:

```text
demand_mw > 0                                  ValueError: UNSUPPORTED_QUALITY_CHECK
demand_mw >= 0 and price_per_mwh is not null   ValueError: UNSUPPORTED_QUALITY_CHECK
region >= 0                                    ValueError: UNSUPPORTED_QUALITY_CHECK
demand_mw >= nan                               ValueError: UNSUPPORTED_QUALITY_CHECK
1=1; DROP TABLE                                ValueError: UNSUPPORTED_QUALITY_CHECK
__import__('os').system('id')                  ValueError: UNSUPPORTED_QUALITY_CHECK
```

Two of these are worth naming. `region >= 0` is rejected because `region` is a
string-kind field, so a numeric comparison on it is a contract error rather than
something to coerce. `demand_mw >= nan` is rejected because a `nan` bound makes
every comparison false, which would quarantine an entire source while looking
like a valid threshold.

Rejection happens **before any side effect** — the run leaves no partial output:

```text
ValueError: UNSUPPORTED_QUALITY_CHECK
  output dir exists: NO
```

This matters because the pre-existing failure mode for a bad contract was a
`KeyError` part-way through, *after* Bronze and Quarantine had been written.

## Manifest watermark

`docs/workshop-acceptance.md:166` requires the manifest to report a watermark.
Each source now reports one, in normalised UTC, with the field it came from:

```text
aemo_dispatch_fixture: watermark=2024-04-07T00:30:00Z  field=interval_datetime
weather_fixture:       watermark=2024-04-07T00:30:00Z  field=observed_at
```

Two decisions behind this. The watermark is `null` — not epoch, not `""` — when
nothing reaches Silver, because a falsy watermark would make an incremental load
silently re-read from the beginning of time. And `watermark_field` must equal
`event_timestamp_field`: only that field is UTC-normalised, so any other choice
is refused rather than honoured meaninglessly.

## Suite

```text
tests/test_bundle_concurrency.py: 6
tests/test_metadata_contract.py: 71
tests/test_pipeline.py: 30

107 passed in 0.33s
```

Targeted subsets:

```text
-k quality_check    5 passed, 102 deselected
-k watermark       12 passed,  95 deselected
```

## Mutation testing

A passing suite does not prove the tests can fail. Each mutant was applied to
`agentic_energy/pipeline.py`, the suite run, then the file restored and verified
byte-identical (`diff -q` clean).

| # | Mutant | Caught |
|---|---|---|
| 1 | Accept any expression instead of the allowlist | yes |
| 2 | Treat a failed check as a pass | yes |
| 3 | Drop the numeric type floor | yes |
| 4 | Reuse one source's checks for every source | yes |
| 5 | Emit the watermark without UTC normalisation | yes |
| 6 | Emit epoch instead of `null` for an empty Silver | yes |
| 7 | Silver count off by one | yes |
| 8 | Remove the watermark emission entirely | yes |
| 9 | Add an unreviewed extra key to the manifest | yes |

Mutants 7–9 target the assertion repaired during the `main` merge, described
below.

## Merge with `main`

`main` moved 15 commits ahead while this work was open. `54e72c8` added
`REQUIRED_SOURCE_FIELDS` validation; that work does not overlap this one
(`quality_checks` appears nowhere on `main`), and all of `main`'s
`test_pipeline.py` tests are kept.

The textual merge was clean but left one failing test:
`test_validation_change_preserves_the_fixture_baseline` guards row accounting,
but compared the whole per-source manifest dict for equality, which also froze
the key set. Adding `watermark`/`watermark_field` therefore failed a test about
counts, for a reason unrelated to counts.

It now compares only the counting keys and stays strict in both directions: the
five counts are pinned exactly; every counting key must be present, so a renamed
or dropped count fails; and non-counting keys must be exactly
`{watermark, watermark_field}`, so an unreviewed manifest addition still fails
there. Freezing the key set would have had to be undone by the next required
field anyway — `docs/workshop-acceptance.md:166` still requires a code/parser
version the manifest does not yet carry.

## Reproducibility and limitations

Reproducible by anyone from a clean clone, with no workspace or credentials:

- the suite, the targeted subsets, and the mutation table;
- the pre/post gap demonstration, by pointing `--metadata-root` at a copy of
  `agentic_energy/resources` with `quality_checks` edited;
- the artifact hashes, via a local fixture run.

What this evidence does **not** prove:

- **`is_market` is not gone.** It no longer drives *validation*, but still drives
  the Silver *projection*. Removing that needs `schema_reference` and was out of
  scope for a bounded change.
- **Six contract fields remain unread**: `compression`, `format`,
  `ingestion_timestamp_field`, `quarantine_policy`, `schedule`,
  `schema_reference`.
- **The manifest still lacks a run-status field and a code/parser version**, both
  required by `docs/workshop-acceptance.md:166`.
- **Live mode is untested.** Every run here is `mode=fixture`; no network egress
  to NEMWEB occurred and `sources.live.json` was not exercised beyond validation.
- The 2 supported expression forms are a floor, not a general expression
  language. A contract needing `<=`, `or`, or arithmetic will be rejected, which
  is intended for now but will need revisiting rather than quietly extending the
  parser.

## A workspace run, recorded separately

The same commit was deployed to a Databricks `dev` target and run serverless in
fixture mode; output landed in a Unity Catalog Volume, hashed identically to the
local run, and SQL independently computed `max(interval_utc)` equal to the
manifest's declared watermark for both sources. That capture is **not** included
here because it contains workspace host, service principal, catalog and group
identifiers, which this directory's README excludes from committed evidence.
