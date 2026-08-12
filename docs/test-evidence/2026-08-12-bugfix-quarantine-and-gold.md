# Bug-fix run: quarantine evidence, Gold reconciliation, DST coverage

Covers beads `agentic-energy-yx8`, `agentic-energy-aln`, and `agentic-energy-02f`.
All console blocks are verbatim capture. Absolute container paths are redacted.

## What each bead turned out to be

Probing came before code, and two of the three beads did not describe the defect
their title claims.

| Bead | Title claims | Probed finding |
|---|---|---|
| `yx8` | malformed rows not safely quarantined | Quarantine is already crash-safe: 11 adversarial shapes (dict/list/scalar/null rows, `NaN`, non-string timestamps) all quarantine without aborting. Narrower real defect: the offending **raw text is discarded** exactly when it matters most. |
| `aln` | Gold reconciliation inconsistent | Confirmed, two distinct defects: a totally failed join is invisible, and freshness was a tautology. |
| `02f` | market timestamps not normalized across DST | **The logic is correct.** No wrong answer was reproducible. The defect is that nothing protected it — see the mutation result. |

`agentic-energy-5g3` is not addressed here. The annotation feature does not exist
in this repo (`grep` finds no `operator_annotations`, `author_identity`, or
`audit_version` in any code or SQL), so there is no authorization logic to fix.

## yx8 — quarantine rows were not self-contained

`raw_record` holds the *parsed* object, so it is `None` precisely when the failure
is a parse error. Before the fix, a malformed line produced:

```json
{
  "raw_record": null,
  "reason_codes": ["INVALID_JSON:Expecting property name enclosed in double quotes",
                   "INVALID_RECORD_SHAPE", "MISSING_REGION", "INVALID_DEMAND",
                   "MISSING_PRICE", "MISSING_EVENT_TIMESTAMP"],
  "rejected_at": "2024-04-07T00:00:00Z",
  "source_file": "fixtures/aemo_dispatch.jsonl",
  "source_id": "aemo_dispatch_fixture",
  "source_row_number": 7
}
```

The operator is told row 7 is malformed with no way to see what it said.
Recovering it from Bronze assumes Bronze is still retained.

Fix: carry `raw_line`, truncated at `MAX_QUARANTINE_RAW_LINE = 4096` with an
explicit `...[truncated N chars]` marker so a truncated value cannot be mistaken
for a complete one.

## aln — a totally failed join was invisible

Gold left-joins weather onto market rows on `(region, interval_utc)`. Gold row
count equals market row count whether every weather row matched or none did.

The shipped fixture contract hides this because both sources declare
`Australia/Sydney`. But `sources.live.json` declares market as
`Australia/Brisbane` (no DST) against weather as `Australia/Sydney` (DST). On that
pairing, the same local wall clock normalizes an hour apart:

```text
silver market  NSW1 2024-01-15T00:00:00Z      (Brisbane, +10)
silver weather NSW1 2024-01-14T23:00:00Z      (Sydney,   +11)
gold           temperature_c = null, lineage.weather = null
manifest       layers.gold = 1        <-- reported success
```

Every enrichment silently lost, and the manifest looked healthy. That is the
shipped live contract, not a contrived input.

After the fix the same input reports:

```json
{"gold": 1, "market_silver": 1, "weather_silver": 1,
 "weather_matched": 0, "weather_unmatched": 1, "weather_unused": 1,
 "market_source_timezone": "Australia/Brisbane",
 "weather_source_timezone": "Australia/Sydney",
 "latest_market_event_utc": "2024-01-15T00:00:00Z",
 "latest_weather_event_utc": "2024-01-14T23:00:00Z"}
```

Second defect: every Gold row reported `freshness.latest_event_utc` equal to its
own `interval_utc`, so a consumer reading it learned nothing about dataset
freshness. Now `row_event_utc` carries the row's instant and `latest_event_utc`
carries the true dataset maximum.

An unmatched join is **not** made fatal. Left-join semantics with a null
temperature may be intended; silently *unreported* was the defect. Making it fail
is a product decision for whoever owns the acceptance gate.

## 02f — the guard was correct and completely unprotected

Sydney 2024 transitions: DST ends 07 Apr (local 02:00–02:59 occurs twice), DST
starts 06 Oct (local 02:00–02:59 never occurs). Probed behaviour before any change:

```text
2024-04-07T01:30:00  ->  2024-04-06T14:30:00Z                | +11, once only
2024-04-07T02:30:00  ->  ValueError:NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME | ambiguous
2024-04-07T03:00:00  ->  2024-04-06T17:00:00Z                | +10, once only
2024-10-06T01:59:59  ->  2024-10-05T15:59:59Z                | +10 before gap
2024-10-06T02:30:00  ->  ValueError:NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME | gap
2024-10-06T03:00:00  ->  2024-10-05T16:00:00Z                | +11 after gap
```

All correct. So the guard was mutation-tested — the fold/gap search replaced with
a naive `parsed.replace(tzinfo=zone)`:

```text
........................................                                 [100%]
40 passed in 0.20s
```

**The entire DST protection could be deleted with the whole suite still green.**
The only timezone test asserted two unambiguous timestamps. The fix for `02f` is
therefore tests, not a code change.

## Verification

Full suite, 40 → 60 tests:

```text
............................................................             [100%]
60 passed in 0.31s
```

Fixture run and artifact hashes:

```text
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3

74b81048350cda0bc9ce3f1bfe976e8b363de0934a517a73c1d725aca64849c7  ./bronze/aemo_dispatch_fixture.jsonl
d45bab3f6e3e0df90170e7cd08155ea4b0a5968efaf9c847c7c85d43756f9be4  ./bronze/weather_fixture.jsonl
38c5df744ecf5677177ecd706c9b0a99cfc1bd8b3db20de78d77ca31a975adbb  ./gold/market_weather.jsonl
26e6ffdb95c059e27f63124298107bae3e23cf34860973ed332be6c4af441482  ./manifest.json
e2ee4a49e633d5c6d35c7beccf07d801625a27753780bd42c5b93e2c1701e319  ./quarantine/rejected.jsonl
f757635ce33ffcce60836690fb000bbe38c1e3d172a05a66d43cee6bfe6065fb  ./silver/aemo_dispatch_fixture.jsonl
28c28552326461045f69f28efca05afe774222c399a9ec1c848725d13e833989  ./silver/weather_fixture.jsonl
```

Replay determinism preserved:

```text
IDENTICAL ./bronze/aemo_dispatch_fixture.jsonl
IDENTICAL ./bronze/weather_fixture.jsonl
IDENTICAL ./gold/market_weather.jsonl
IDENTICAL ./manifest.json
IDENTICAL ./quarantine/rejected.jsonl
IDENTICAL ./silver/aemo_dispatch_fixture.jsonl
IDENTICAL ./silver/weather_fixture.jsonl
```

### Baseline hash change — deliberate

Two artifacts no longer match the foundation-run baseline:

| Artifact | Before | After | |
|---|---|---|---|
| `bronze/aemo_dispatch_fixture.jsonl` | `74b81048…` | `74b81048…` | same |
| `bronze/weather_fixture.jsonl` | `d45bab3f…` | `d45bab3f…` | same |
| `silver/aemo_dispatch_fixture.jsonl` | `f757635c…` | `f757635c…` | same |
| `silver/weather_fixture.jsonl` | `28c28552…` | `28c28552…` | same |
| `quarantine/rejected.jsonl` | `42abde41…` | `e2ee4a49…` | **changed** |
| `gold/market_weather.jsonl` | `f56fe647…` | `38c5df74…` | **changed** |

Row counts (`bronze=11, silver=6, quarantine=3, gold=3`) and all business values
are unchanged, verified field by field. The changes are additive keys only:
`raw_line` in quarantine; `weather_matched` and the expanded `freshness` block in
Gold. This repo scores byte-identical replay, so the change is called out rather
than absorbed silently. The two prior evidence documents keep their original
hashes and carry a superseding note.

### Mutation testing

Each fix was reverted individually against the new suite:

```text
### MUTATION 1: revert yx8 (drop raw_line from quarantine)
FAILED tests/test_pipeline.py::test_every_quarantine_row_carries_its_raw_line
FAILED tests/test_pipeline.py::test_pathological_raw_line_is_truncated_with_an_explicit_marker

### MUTATION 2: revert aln manifest block (drop gold reconciliation)
FAILED tests/test_pipeline.py::test_a_totally_failed_weather_join_is_reported_not_silent
FAILED tests/test_pipeline.py::test_weather_matched_distinguishes_absent_join_from_null_temperature

### MUTATION 3: revert 02f DST guard (naive tz conversion)
FAILED tests/test_pipeline.py::test_ambiguous_and_nonexistent_local_times_are_rejected[2024-10-06T02:30:00]
FAILED tests/test_pipeline.py::test_ambiguous_and_nonexistent_local_times_are_rejected[2024-10-06T02:59:59]

### RESTORED
60 passed
```

Mutation 3 is the significant one: that same mutation survived the previous
40-test suite. The assertions are load-bearing.

## Limitations

- **Not re-run on Databricks.** The deployed job last ran before these fixes, so
  the local-vs-serverless byte-equality check has not been repeated against them.
- **`5g3` unaddressed** — the feature it audits does not exist.
- **Cross-contract timezone mismatch is reported, not prevented.** Whether the
  pipeline should warn or fail when market and weather declare different
  `source_timezone` is left open; `sources.live.json` ships that pairing today.
- **Six contract fields remain unread** by any code path: `watermark_field`,
  `quality_checks`, `quarantine_policy`, `schema_reference`,
  `ingestion_timestamp_field`, `compression`, `schedule`. `quality_checks` is the
  concerning one: the real rules are hardcoded, so the contract looks like it
  drives validation and does not.
