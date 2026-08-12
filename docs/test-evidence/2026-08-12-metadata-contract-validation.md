# Test evidence — metadata contract validation hardening

| | |
|---|---|
| Captured (UTC) | 2026-08-12 |
| Beads issue | `agentic-energy-zwh` — Engineering: inspect and improve the metadata contract |
| Acceptance stages | B1 (understand the contract), B2/B4 (bounded improvement with tests) |
| Python / pytest | 3.10.12 / 9.1.1 |
| Suite | **40 passed** (was 24 before this change) |
| Fixture baseline | unchanged — `bronze=11, silver=6, quarantine=3, gold=3`, all 7 artifact hashes identical |
| Overall | **PASS** |

## The defect found (stage B1)

`_validate_source()` validated `source_id`, `natural_key`, `extraction_mode` and
fixture paths, but six fields are read **unconditionally** by the generic worker
without ever being validated. Static comparison of direct indexing against
guarded access:

```text
indexed directly (KeyError risk): ['dataset', 'deduplication_rule', 'event_timestamp_field',
                                   'fixture_path', 'licensing_provenance', 'natural_key',
                                   'provider', 'source_id', 'source_timezone',
                                   'source_version', 'url_or_fixture_path']
accessed via .get()             : ['dataset', 'event_timestamp_field', 'extraction_mode',
                                   'fixture_path', 'natural_key', 'source_id',
                                   'url_or_fixture_path']

INDEXED BUT NEVER VALIDATED     : ['deduplication_rule', 'licensing_provenance',
                                   'provider', 'source_timezone', 'source_version']
```

Probing each against a real external contract (`--metadata` + `--metadata-root`
+ `--metadata-snapshot-id`), **before** the fix:

```text
baseline (unmodified)            exit=0  ACCEPTED           bronze=11, silver=6, quarantine=3, gold=3
drop source_timezone             exit=1  KeyError CRASH     KeyError: 'source_timezone'
drop deduplication_rule          exit=1  KeyError CRASH     KeyError: 'deduplication_rule'
drop provider                    exit=1  KeyError CRASH     KeyError: 'provider'
drop source_version              exit=1  KeyError CRASH     KeyError: 'source_version'
drop licensing_provenance        exit=1  KeyError CRASH     KeyError: 'licensing_provenance'
bogus timezone value             exit=1  clean reject       ZoneInfoNotFoundError: 'Mars/Olympus'
unknown dedup rule               exit=1  clean reject       ValueError: Unsupported deduplication_rule…
unknown quality-check expr       exit=0  ACCEPTED SILENTLY  bronze=11, silver=6, quarantine=3, gold=3
```

An incomplete contract failed with a raw `KeyError` part-way through the run.
That violates the "validates before side effects" invariant in
[`../workshop-acceptance.md`](../workshop-acceptance.md) and the *operational
safety → clear failures* scoring signal: a participant adding a source in stage
B2 got a stack trace instead of a contract error naming the missing field.

The two "clean reject" rows were already acceptable, but both fired **late** —
the timezone only when the first row was converted, the dedup rule only after
Bronze and Quarantine had been written.

## The change (stages B2/B4)

Bounded, in `agentic_energy/pipeline.py` only. No orchestration, no job
definition, and no per-source branch was touched.

- `REQUIRED_SOURCE_FIELDS` — the six fields the worker reads unconditionally,
  validated as non-blank strings up front, raising
  `MISSING_SOURCE_FIELD:<field>` so the error names the offending field.
- `SUPPORTED_DEDUPLICATION_RULES` — a single shared frozenset. The late runtime
  check now reads from it too, so the accepted-rule list cannot drift between
  validation and execution.
- `source_timezone` is resolved through `ZoneInfo` **at validation time**,
  raising `INVALID_SOURCE_TIMEZONE` before any layer is written.

## Results

### Full suite

```text
........................................                                 [100%]
40 passed in 0.18s
```

16 new tests, parameterised over the required fields and invalid values.

### Mutation test — do the new tests actually catch the defect?

The new validation block was deleted and the suite re-run:

```text
14 failed, 26 passed in 0.57s
```

Restored:

```text
40 passed in 0.23s
```

14 of the 16 new tests fail without the fix. The 2 that pass either way are the
deliberate regression guards (`test_shipped_contracts_still_satisfy_the_stricter_validation`,
`test_validation_change_preserves_the_fixture_baseline`) — they assert *nothing
broke*, so passing before and after is the correct behaviour for them.

### No side effects on rejection

Every rejection test also asserts `not output.exists()`, proving validation
happens before any layer is written rather than merely being reported.

### Unchanged behaviour (stage B4 requirement)

Both shipped contracts still validate under the stricter rules:

```text
OK   sources.json         aemo_dispatch_fixture
OK   sources.json         weather_fixture
OK   sources.live.json    aemo_dispatchis_live
OK   sources.live.json    weather_fixture
```

The fixture run is byte-for-byte identical to the pre-change anchor:

```text
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3
IDENTICAL to pre-change run: all 7 artifact hashes unchanged
```

## Deliberately not fixed

**`quality_checks` is declarative fiction.** `grep` confirms the field is never
read anywhere in the codebase; the real quality rules are hardcoded in
`pipeline.py` (`INVALID_DEMAND`, `MISSING_PRICE`, `MISSING_TEMPERATURE`). Setting
it to `["demand_mw >= 0 OR 1=1"]` changed nothing about the run.

This is a trap for stage B2 — the metadata looks authoritative but is inert, so a
participant "changing source behaviour" through it would see no effect and no
error. Wiring it up is a **behaviour change**, not a bounded contract fix, so it
belongs in its own issue rather than smuggled into this one.

**A CLI papercut worth its own issue:** `--metadata-root` is silently ignored
unless `--metadata` is also passed (`cli.py:34`,
`metadata_root=args.metadata_root if args.metadata else None`). This first
invalidated the probe run above — mutated contracts appeared to be "accepted"
when the packaged contract was being read instead. A flag that silently does
nothing is an operational-safety issue in its own right.

## Reproducing

```bash
uv run --extra test python -m pytest -q                       # expect 40 passed

# unchanged fixture baseline
uv run python -m agentic_energy.cli --output /tmp/post
# expect bronze=11, silver=6, quarantine=3, gold=3

# the new rejections, listed
uv run --extra test python -m pytest tests/test_pipeline.py -q -k \
  "incomplete_contract or invalid_contract_values or non_string_required" -v
```
