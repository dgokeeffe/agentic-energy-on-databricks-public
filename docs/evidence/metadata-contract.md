# Evidence — metadata contract improvement (`agentic-energy-g77`)

Issue: `agentic-energy-g77` — *Engineering: inspect and improve the metadata
contract.* "Inspect source metadata, schema, timezone, natural key, watermark,
quality, and quarantine behavior. Make a bounded contract or test improvement
without creating a source-specific job."

Companion to [`foundation-run.md`](foundation-run.md), which records the
deterministic fixture run this work started from (`agentic-energy-4w2`).

## Run context

| Item | Value |
|---|---|
| Branch | `SM` (off `main`) |
| Starting commit | `76cb812` — *docs: record deterministic foundation run evidence* |
| Python / uv / pytest | 3.10.12 / 0.10.2 / 9.1.1 |
| Mode | `fixture` only — no live sources, no network egress to `nemweb.com.au` |
| Production files changed | `agentic_energy/pipeline.py` only (+110 / −11) |
| Tests added | `tests/test_metadata_contract.py` (71 tests) |
| Suite | 34 → **95 passing** (`test_pipeline.py` unchanged at 14) |

## The finding

`agentic_energy/resources/metadata/sources.json` declares 21 fields per source.
Before this change **eight were read by no line of code**: `compression`,
`format`, `ingestion_timestamp_field`, `quality_checks`, `quarantine_policy`,
`schedule`, `schema_reference`, `watermark_field`. No test referenced any of them.

Two of those mattered, because the acceptance gate explicitly requires them
(`docs/workshop-acceptance.md:136-137`, `:164`, `:166` — "natural keys,
watermarks, timezone, quality, and quarantine reconcile"; the run manifest must
carry "counts, watermark, freshness").

### `quality_checks` was decorative

The contract declared the rules:

```json
"quality_checks": ["demand_mw >= 0", "price_per_mwh is not null"]
```

while row validation was hardcoded in `pipeline.py` behind a dataset branch:

```python
is_market = source["dataset"] in {"DISPATCH_SCADA", "DISPATCHIS"}
...
if is_market:
    if ... demand < 0:     reasons.append("INVALID_DEMAND")
    if ... price is None:  reasons.append("MISSING_PRICE")
else:
    if ...:                reasons.append("MISSING_TEMPERATURE")
```

The same rule was expressed twice, in two places, with nothing linking them.
Editing the contract changed nothing. Worse, `is_market` is source-specific
behaviour *inside the generic worker* — the shape the issue explicitly forbids.

**Demonstrated rather than asserted.** Appending a check every market row
violates, then re-running the shipped fixtures:

```
declared checks now include 'demand_mw >= 999999'
EVERY market row violates it, so all 6 should quarantine.
actual counts: {'bronze': 11, 'silver': 6, 'quarantine': 3, 'gold': 3}

GAP CONFIRMED: the new declared check was ignored entirely.
```

`quarantine` stayed at 3. The contract had no effect on behaviour.

## What changed

### 1. Declared quality checks now execute

Three helpers in `pipeline.py`, plus a field registry:

| Function | Role |
|---|---|
| `_parse_quality_check(check)` | one declared string → `(field, operator, bound)` |
| `_validate_quality_checks(source)` | parses all declared checks; fails fast |
| `_quality_check_reasons(row, checks)` | violated checks → reason codes, declared order |

The row-validation branch was deleted and replaced by:

```python
for reason in _quality_check_reasons(row, declared_checks):
    if reason not in reasons:
        reasons.append(reason)
```

**Exactly two expression forms are supported**, by design:

* `"<field> is not null"`
* `"<field> >= <number>"`

No `and`/`or`, no arithmetic, and **no `eval`** — the contract is a data file, so
it is parsed as data. Evaluating it would make `sources.json` an injection
vector.

An expression that cannot be parsed raises `UNSUPPORTED_QUALITY_CHECK` during
source validation, before any output is written. A silently-skipped rule is
worse than an absent one: the contract would claim a guarantee the pipeline does
not provide. 20 malformed inputs are pinned as rejected, including
`"demand_mw > 0"` (wrong operator), `"unknown_field >= 0"` (unregistered field),
`"demand_mw >= nan"` (a bound that fails every comparison),
`"demand_mw >= 0 and price_per_mwh >= 0"` (composition), and
`"__import__('os').system('boom') is not null"`.

### 2. A type floor, because the declared check alone is weaker

Found before the branch was deleted, by testing the evaluator against
non-numeric values:

```
temperature_c='abc'  -> declared check says []   ← ACCEPTED
temperature_c=True   -> declared check says []   ← ACCEPTED
```

`"temperature_c is not null"` constrains nullness only, but the hardcoded code it
replaces required `isinstance(int|float)` and `math.isfinite`. A naive swap would
have **silently weakened validation** while every test stayed green, because the
fixture contains no such row.

The registry supplies the missing floor, keyed on **field name** — deliberately
not on `source_id` or `dataset`, which would reintroduce source-specific
behaviour:

```python
_QUALITY_CHECK_FIELDS = {
    "demand_mw":     ("INVALID_DEMAND",      "numeric"),
    "price_per_mwh": ("MISSING_PRICE",       "numeric"),
    "temperature_c": ("MISSING_TEMPERATURE", "numeric"),
    "region":        ("MISSING_REGION",      "string"),
}
```

After the fix, parity with the old behaviour is restored: `'abc'`, `True`, `[1]`,
`nan` and `inf` all yield `MISSING_TEMPERATURE`; `21.5` passes.

### 3. `watermark_field` is honoured and reported

`_validate_source` now rejects a missing or unusable `watermark_field`
(`INVALID_WATERMARK_FIELD`, `UNSUPPORTED_WATERMARK_FIELD`). Only the declared
event timestamp is normalised to UTC, so it is the only field a comparable mark
can be derived from; a contract naming anything else is refused rather than
honoured meaninglessly.

Each per-source manifest entry gained two keys:

```json
"aemo_dispatch_fixture": {
  "accepted": 4, "bronze": 6, "deduplicated": 1, "quarantine": 2, "silver": 3,
  "watermark": "2024-04-07T00:30:00Z", "watermark_field": "interval_datetime"
}
```

`watermark_field` is emitted next to the value so the manifest is
self-describing: a reader can see which declared field produced the mark instead
of having to trust it. The value is the **normalised UTC** high-water mark — the
declared field holds local time, and a mark in mixed local time cannot drive an
incremental load. It is `null`, not an epoch or empty string, when no row reached
Silver; a falsy watermark would make an incremental load silently re-read from
the beginning of time.

## Verification

### The contract now drives behaviour, in both directions

Tightening — the same experiment that proved the gap:

| | quarantine | silver | gold |
|---|---|---|---|
| before the change | 3 (ignored) | 6 | 3 |
| after the change | **7** | 3 | 0 |

Loosening — removing a declared rule stops it being enforced:

| Contract mutation | quarantine | reason codes |
|---|---|---|
| as shipped | 3 | `INVALID_DEMAND`, `MISSING_PRICE`, `MISSING_TEMPERATURE` |
| drop `demand_mw >= 0` | 2 | `MISSING_PRICE`, `MISSING_TEMPERATURE` |
| drop `price_per_mwh is not null` | 2 | `INVALID_DEMAND`, `MISSING_TEMPERATURE` |
| drop `temperature_c is not null` | 2 | `INVALID_DEMAND`, `MISSING_PRICE` |

A typo'd check aborts the run and leaves no partial output:

```
run aborted: ValueError(UNSUPPORTED_QUALITY_CHECK)
output dir created? False (False = previous state preserved)
```

### No behaviour drift on the shipped fixture

Counts remain `bronze=11, silver=6, quarantine=3, gold=3`, and quarantine output
is byte-identical to the run recorded in `foundation-run.md`:

| Artifact | SHA-256 | vs foundation run |
|---|---|---|
| `bronze/aemo_dispatch_fixture.jsonl` | `74b81048350cda0bc9ce3f1bfe976e8b363de0934a517a73c1d725aca64849c7` | identical |
| `bronze/weather_fixture.jsonl` | `d45bab3f6e3e0df90170e7cd08155ea4b0a5968efaf9c847c7c85d43756f9be4` | identical |
| `silver/aemo_dispatch_fixture.jsonl` | `f757635ce33ffcce60836690fb000bbe38c1e3d172a05a66d43cee6bfe6065fb` | identical |
| `silver/weather_fixture.jsonl` | `28c28552326461045f69f28efca05afe774222c399a9ec1c848725d13e833989` | identical |
| `quarantine/rejected.jsonl` | `42abde41b303b6fa3dbecdfc3038d416684d065e451a5d4f7576b20f55329e92` | identical |
| `gold/market_weather.jsonl` | `f56fe6473b47cf8f31e6bbfede38cb71b923dee068edbc6f6d89f38e313d9f3d` | identical |
| `manifest.json` | `28c2a5413fa4905dafb3f05413c854e8308929ae6518009f093431487b69d99c` | **changed** by design (was `76a44264…7009ed`, 691 → 863 bytes) |

`diff -rq` against the reproduced foundation run reports exactly one difference,
`manifest.json`. Replay determinism (EQ6) still holds: three successive runs are
byte-identical to each other. Per-source row accounting (EQ1–EQ3) still
reconciles alongside the new fields.

### Mutation testing

Tests that cannot fail are not evidence, so each guarantee was checked by
injecting the corresponding regression and confirming the suite catches it.
`pipeline.py` was restored from backup after every mutant.

| # | Injected fault | Failures |
|---|---|---|
| 1 | remove the numeric type floor | 6 |
| 2 | make the evaluator a no-op (revert to decorative) | 11, incl. 3 pre-existing `test_pipeline.py` tests |
| 3 | silently skip unparseable checks (`except ValueError: pass`) | 1 |
| 4 | drop reason-code de-duplication | 1 |
| 5 | hardcode the watermark instead of deriving it | 2 |
| 6 | mis-report `watermark_field` | 2 |

Mutant 2 matters most: reverting to the decorative contract breaks 11 tests, so
this cannot quietly rot back.

## Findings recorded, not worked around

1. **`is_market` still exists at `pipeline.py:390` and `:433`.** It no longer affects
   validation, but still selects which measure columns the Silver projection
   emits. Removing it needs a declared field or schema list, i.e. activating
   `schema_reference` — a larger change than "bounded" allows. The generic worker
   is not yet fully free of dataset branching.
2. **`weather_fixture` declares `region is not null`, which duplicates an
   existing structural check.** Reason codes are de-duplicated so the row reports
   `MISSING_REGION` once. `aemo_dispatch_fixture` does *not* declare it, yet
   market rows with a non-string region must still be rejected — so
   contract-driven checks add to the structural floor rather than replacing it.
   Both behaviours are pinned by test.
3. **Six contract fields remain unread**: `compression`, `format`,
   `ingestion_timestamp_field`, `quarantine_policy`, `schedule`,
   `schema_reference`. `quarantine_policy` is asserted to equal
   `isolate_with_reason` but does not select behaviour; only one policy exists.
4. **`foundation-run.md` gaps 2 and 3 remain open** — no explicit run-status
   field, and no code or parser version in the manifest
   (`docs/workshop-acceptance.md:166` asks for the latter). Both are candidate
   scope for a follow-up; neither was needed to satisfy this issue.
5. **`sources.live.json` also declares `quarantine_policy`** and the other unread
   fields. Nothing in this change touches the live path, which was not exercised:
   fixture mode only, as the issue scope requires.

## Result

`quality_checks` and `watermark_field` moved from decorative declarations to
enforced contract terms, with no source-specific job added and no change to the
pipeline's output for the shipped fixture beyond the intended manifest addition.
Suite: **95 passing**. One production file touched.
