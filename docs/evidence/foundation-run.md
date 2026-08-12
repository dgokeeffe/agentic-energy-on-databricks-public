# Foundation run evidence — deterministic fixture ETL

Evidence bundle for Beads issue **`agentic-energy-4w2`** — *"Foundation: run the
deterministic fixture ETL"*.

> Run the checked-in fixture profile and verify Bronze, Silver, Quarantine, Gold,
> and manifest reconciliation. Record commands and evidence; do not enable live
> sources.

**Live sources were never enabled.** No request was made to `nemweb.com.au`. Both
runs used the packaged fixture contract in fixture mode only.

## Run context

| Item | Value |
|---|---|
| Repository commit | `96f25496d8aa06ee2af6d4fae6368f8053fd73da` (`96f2549 docs: add participant workshop deck`) |
| Branch | `SM` |
| Metadata contract | `agentic_energy/resources/metadata/sources.json` |
| Contract SHA-256 | `e2235552b0131cfc2272a6a1da5075a8bea2d5a66c13d57496b8f770562ca94e` |
| Mode | `fixture` |
| Working tree at start | clean |

| Tool | Version |
|---|---|
| Python | 3.10.12 |
| uv | 0.10.2 |
| bd (Beads) | 1.2.1 (`634cbbc4b`) |
| jq | 1.7.1 |
| git | 2.34.1 |
| pytest | 9.1.1 |

## Commands and verbatim output

### Run A

```console
$ uv run python -m agentic_energy.cli --output output/run-a
Using CPython 3.10.12 interpreter at: /usr/bin/python3
Creating virtual environment at: .venv
   Building agentic-energy-on-databricks @ file:///.../agentic-energy-on-databricks-public
      Built agentic-energy-on-databricks @ file:///.../agentic-energy-on-databricks-public
Installed 1 package in 1ms
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3
```

### Run B (replay)

```console
$ uv run python -m agentic_energy.cli --output output/run-b
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3

$ diff -r output/run-a output/run-b
$ echo $?
0
```

### Test suite

```console
$ uv run --extra test python -m pytest -v
platform linux -- Python 3.10.12, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
testpaths: tests
collected 24 items

tests/test_bundle_concurrency.py ......                                  [ 25%]
tests/test_lakebase_artifacts.py ....                                    [ 41%]
tests/test_pipeline.py ..............                                    [100%]

============================== 24 passed in 0.29s ==============================
```

## Artifacts

Seven files per run. SHA-256 values are identical for run A and run B.

| Artifact | Bytes | SHA-256 |
|---|---|---|
| `bronze/aemo_dispatch_fixture.jsonl` | 2546 | `74b81048350cda0bc9ce3f1bfe976e8b363de0934a517a73c1d725aca64849c7` |
| `bronze/weather_fixture.jsonl` | 1825 | `d45bab3f6e3e0df90170e7cd08155ea4b0a5968efaf9c847c7c85d43756f9be4` |
| `silver/aemo_dispatch_fixture.jsonl` | 1413 | `f757635ce33ffcce60836690fb000bbe38c1e3d172a05a66d43cee6bfe6065fb` |
| `silver/weather_fixture.jsonl` | 1326 | `28c28552326461045f69f28efca05afe774222c399a9ec1c848725d13e833989` |
| `quarantine/rejected.jsonl` | 897 | `42abde41b303b6fa3dbecdfc3038d416684d065e451a5d4f7576b20f55329e92` |
| `gold/market_weather.jsonl` | 2361 | `f56fe6473b47cf8f31e6bbfede38cb71b923dee068edbc6f6d89f38e313d9f3d` |
| `manifest.json` | 691 | `76a442644e994d35c05b85adb6781a6cda5abbfefb6e1d2224d2b9f4a37009ed` |

Output directories are gitignored (`.gitignore:14`), so this document is the
durable record of the run.

> **Superseded for `manifest.json` only.** `agentic-energy-g77` added a per-source
> `watermark` and `watermark_field` to the manifest, so it is now 863 bytes with
> hash `28c2a5413fa4905dafb3f05413c854e8308929ae6518009f093431487b69d99c`. The row
> above is the correct value for this commit and remains the reference point for
> that change. The other six artifacts are byte-identical before and after —
> re-verified with `diff -r` against a run reproduced from this document — so the
> data-plane evidence below still stands unchanged. See *Gaps and findings* item 1.

## Manifest

```json
{
  "layers": { "bronze": 11, "gold": 3, "quarantine": 3, "silver": 6 },
  "metadata_sha256": "e2235552b0131cfc2272a6a1da5075a8bea2d5a66c13d57496b8f770562ca94e",
  "mode": "fixture",
  "pipeline_ingested_at": "2024-04-07T00:00:00Z",
  "source_definitions": { "read": 2, "selected": 2 },
  "source_ids": ["aemo_dispatch_fixture", "weather_fixture"],
  "sources": {
    "aemo_dispatch_fixture": {
      "accepted": 4, "bronze": 6, "deduplicated": 1, "quarantine": 2, "silver": 3
    },
    "weather_fixture": {
      "accepted": 4, "bronze": 5, "deduplicated": 1, "quarantine": 1, "silver": 3
    }
  }
}
```

Post-`agentic-energy-g77` each entry under `sources` additionally carries
`"watermark": "2024-04-07T00:30:00Z"` and `"watermark_field"` (`interval_datetime`
for the market source, `observed_at` for weather). Nothing shown above was
removed or renamed.

`metadata_sha256` was cross-checked against
`sha256sum agentic_energy/resources/metadata/sources.json` — identical.

## Acceptance equations

The common acceptance gate is defined in
[`docs/workshop-acceptance.md`](../workshop-acceptance.md) (§ *Shared foundation
outcome*).

| # | Equation | Status | Proof |
|---|---|---|---|
| 1 | source definitions read = source definitions selected | PASS | `read` 2 = `selected` 2 |
| 2 | Bronze input rows = accepted rows + quarantined rows | PASS | market 6 = 4 + 2; weather 5 = 4 + 1 |
| 3 | accepted rows = Silver rows + rows removed by declared deduplication | PASS | market 4 = 3 + 1; weather 4 = 3 + 1 |
| 4 | Silver keys unique by declared natural key | PASS | evaluated against the contract's `natural_key`, mapping `event_timestamp_field` to `interval_utc` as `pipeline.py:362-366` does — 3/3 distinct for both sources |
| 5 | Silver timestamps normalized using declared source timezone | PASS | see *Timezone normalisation* below |
| 6 | identical replay = unchanged output keys and layer counts | PASS | `diff -r` exit 0 and 7/7 identical SHA-256 across two independent runs |
| 7 | run status = success only after all selected sources complete | PASS (implicit + tests) | manifest is written last (`pipeline.py:411`) and reconciles all 2 selected sources; write-once and failure-recovery semantics proven by test — see *Gaps* |

Additional cross-checks, all passing:

- layer totals equal the sum of per-source counters (bronze 11, silver 6, quarantine 3);
- `layers.gold` (3) equals surviving market Silver rows (3) — one Gold row per market interval;
- `source_ids` set equals the `sources` map keys.

## Layer verification

### Bronze — immutable landing

- 6 + 5 = 11 rows.
- 11/11 rows carry `source_id`, `source_file`, `source_row_number`, `raw_line`,
  `raw_record`, `_ingested_at`.
- Exactly one distinct `_ingested_at` (`2024-04-07T00:00:00Z`), taken from the
  contract rather than a wall clock.
- `raw_line` preserves the original source bytes alongside the parsed
  `raw_record`, so the append-only, no-transformation invariant holds.

### Silver — typed, normalised, deduplicated

| region | interval_utc | demand_mw | price_per_mwh | ingestion_sequence |
|---|---|---|---|---|
| NSW1 | 2024-01-14T23:00:00Z | 8100 | 68.0 | 1 |
| NSW1 | 2024-04-07T00:00:00Z | 8250 | 70.0 | 2 |
| VIC1 | 2024-04-07T00:30:00Z | 5100 | 65.0 | 1 |

| region | interval_utc | temperature_c | ingestion_sequence |
|---|---|---|---|
| NSW1 | 2024-01-14T23:00:00Z | 29.0 | 1 |
| NSW1 | 2024-04-07T00:00:00Z | 24.5 | 2 |
| VIC1 | 2024-04-07T00:30:00Z | 18.5 | 1 |

Deduplication was proven rather than assumed: the market fixture contains both
`demand_mw=8200, ingestion_sequence=1` and `demand_mw=8250, ingestion_sequence=2`
for `NSW1 2024-04-07T10:00:00` local. Silver retains **8250** (sequence 2),
matching the declared `last_by_ingestion_sequence` rule.

### Quarantine — isolate with reason

| source | row | reason code | offending value |
|---|---|---|---|
| `aemo_dispatch_fixture` | 4 | `INVALID_DEMAND` | `demand_mw: -1` (QLD1) |
| `aemo_dispatch_fixture` | 5 | `MISSING_PRICE` | `price_per_mwh: null` |
| `weather_fixture` | 4 | `MISSING_TEMPERATURE` | `temperature_c: null` |

- 3/3 rows carry a non-empty `reason_codes` array, `source_file`, a numeric
  `source_row_number`, and `rejected_at`.
- Both sources are represented (2 + 1).
- Each rejection corresponds to a declared `quality_checks` entry
  (`demand_mw >= 0`, `price_per_mwh is not null`), and the run still completed
  successfully rather than aborting.

### Gold — market/weather projection

| region | interval_utc | demand_mw | price_per_mwh | temperature_c |
|---|---|---|---|---|
| NSW1 | 2024-01-14T23:00:00Z | 8100 | 68.0 | 29.0 |
| NSW1 | 2024-04-07T00:00:00Z | 8250 | 70.0 | 24.5 |
| VIC1 | 2024-04-07T00:30:00Z | 5100 | 65.0 | 18.5 |

- Grain `(region, interval_utc)` is unique: 3 rows, 3 distinct keys.
- 3/3 rows carry `freshness` and both lineage sides, with two `source_ids`.
- No null weather joins on this fixture — every market interval found a weather
  partner.
- `freshness` distinguishes processing time (`pipeline_ingested_at`) from event
  time (`latest_event_utc`).
- Lineage resolves to the exact source line on both sides, including `provider`,
  `dataset`, `source_version`, and `licensing_provenance`.

## Timezone normalisation

Both sources declare `source_timezone: Australia/Sydney`. `_utc_timestamp`
(`pipeline.py:47-66`) was applied directly to each accepted fixture timestamp and
cross-checked against an independent `zoneinfo` computation.

| Fixture local time | Zone abbreviation | UTC offset | Normalised | Matches Silver |
|---|---|---|---|---|
| `2024-01-15T10:00:00` | AEDT | +11:00 | `2024-01-14T23:00:00Z` | yes |
| `2024-04-07T10:00:00` | AEST | +10:00 | `2024-04-07T00:00:00Z` | yes |
| `2024-04-07T10:30:00` | AEST | +10:00 | `2024-04-07T00:30:00Z` | yes |

Two different offsets are applied within a single source, so the conversion is
derived from the timezone database rather than a fixed offset.

The fixture deliberately sits on Sydney's 2024 daylight-saving changeover day.
Verified locally: `2024-04-07T01:59` is AEDT (+11) and `2024-04-07T03:00` is AEST
(+10). The fixture's 10:00 and 10:30 rows fall after the transition, so AEST is
correct; a hardcoded +11 implementation would emit `2024-04-06T23:00:00Z` and
still look plausible.

DST-safety behaviour, confirmed by direct calls:

| Input | Result |
|---|---|
| `2024-04-07T02:30:00` (ambiguous, fold) | rejected — `NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME` |
| `2024-10-06T02:30:00` (nonexistent, gap) | rejected — `NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME` |
| `2024-04-07T10:00:00+10:00` (offset-bearing) | rejected — `OFFSET_NOT_ALLOWED` |

The implementation refuses to invent an offset; such rows become quarantine
reason codes instead of plausible but wrong UTC values.

## Test coverage mapped to the gate

| Equation or property | Test |
|---|---|
| Row accounting (EQ1–3) | `tests/test_pipeline.py::test_manifest_reconciles_source_row_accounting` |
| Natural key and replay (EQ4, EQ6) | `test_end_to_end_contract_and_idempotency` |
| Timezone normalisation (EQ5) | `test_aest_and_aedt_are_normalized_using_source_timezone` |
| Run status, write-once, failure recovery (EQ7) | `test_run_id_output_is_write_once`, `test_failed_run_preserves_previous_output_and_rejects_unsafe_metadata`, `test_failed_promotion_cleans_staging_and_restores_output` |
| Quarantine without aborting the run | `test_malformed_rows_are_quarantined_without_aborting` |
| Metadata identity and orchestration context | `test_manifest_carries_orchestration_context` |
| Deterministic vs real ingestion instant | `test_fixture_mode_uses_declared_ingestion_timestamp`, `test_live_mode_stamps_the_real_ingestion_instant` |
| Generic worker path for live metadata | `test_live_metadata_path_uses_generic_pipeline` |
| Fixture-mode and metadata-root enforcement | `test_external_metadata_root_and_fixture_mode_are_enforced` |

## Gaps and findings

Recorded rather than worked around. `docs/workshop-acceptance.md` permits
attaching focused deterministic test output where the manifest does not yet emit
a named counter.

1. **No watermark counter in the manifest.** `watermark_field` is declared for
   every source in the contract but is not read anywhere in `agentic_energy/`.
   Deduplication is driven by `ingestion_sequence` instead. No test covers a
   watermark, because no watermark behaviour exists.

   > **Resolved by `agentic-energy-g77`.** The manifest now reports, per source,
   > `watermark` (the high-water mark over the declared field, normalised to UTC)
   > and `watermark_field` (the declared field it came from), and the pipeline
   > rejects a contract whose `watermark_field` it cannot honour. Both fixture
   > sources report `2024-04-07T00:30:00Z`, matching `max(interval_utc)` in Silver.
   > This is the only change to the artifacts recorded above, and it affects
   > `manifest.json` alone.
2. **No explicit run-status field.** EQ7 holds only implicitly: `manifest.json`
   is written last, so its presence signals completion. The three write-once and
   failure-recovery tests listed above supply the missing proof.
3. **No code or parser version in the manifest.** `docs/workshop-acceptance.md`
   asks the run manifest to carry code/parser version alongside metadata version;
   only `metadata_sha256` is currently emitted.
4. **Timezone normalisation is correct on this fixture.** The symptom described
   by `agentic-energy-amg` ("local market timestamps are not normalized
   correctly") does not reproduce from the checked-in fixture; investigating it
   will need a DST-edge row the fixture does not contain. Noted for that issue,
   out of scope here.

5. **Declared `quality_checks` did not execute.** Found while scoping
   `agentic-energy-g77`: the contract declared `demand_mw >= 0` and
   `price_per_mwh is not null`, but row validation was hardcoded in
   `pipeline.py` behind an `is_market` branch, so the declared rules were
   decorative. Appending a check the fixture violates left `quarantine` at 3,
   proving the contract had no effect.

   > **Resolved by `agentic-energy-g77`.** Quality rules are now parsed from the
   > contract and evaluated generically; the `is_market` branch is gone from row
   > validation, and an unparseable check aborts the run rather than being
   > silently skipped. Quarantine output for this fixture is unchanged
   > (`42abde41…`), so the evidence above still holds.

Items 1 and 5 were taken up by `agentic-energy-g77` ("Engineering: inspect and
improve the metadata contract") and are resolved as noted. Items 2 and 3
(no run-status field, no code/parser version in the manifest) remain open and
are still candidate scope for a follow-up.

## Environment deviations

1. **Beads graph is local-only.** `scripts/bootstrap-participant-beads.sh`
   reported `Remote has no Dolt data yet; initialized a fresh local database`,
   followed by `failed to commit beads files: exit status 128` and
   `Git upstream not configured`. No organizer Dolt remote had been seeded, and
   `BEADS_DOLT_REMOTE` was unset, so the six participant issues exist only in the
   local (gitignored) database. The `128` warning is `bd` attempting to commit its
   own files; the repository was not modified by it.
2. **`bd init` edited a tracked file.** It appended a `*.gate.lock*` rule to
   `.gitignore` and staged the change, to ignore the lock files it creates in
   `.beads/`. The edit is tool-generated, not part of this foundation work.
3. `uv` created `.venv/` and `uv.lock`; both are gitignored
   (`.gitignore:9,17`).

## Beads state

| ID | Title | State at close |
|---|---|---|
| `agentic-energy-4w2` | Foundation: run the deterministic fixture ETL | closed by this evidence |
| `agentic-energy-g77` | Engineering: inspect and improve the metadata contract | unblocked |
| `agentic-energy-010` | Defect: malformed rows are not safely quarantined | unblocked |
| `agentic-energy-amg` | Defect: local market timestamps are not normalized correctly | unblocked |
| `agentic-energy-vox` | Defect: synchronized Gold reconciliation is inconsistent | unblocked |
| `agentic-energy-lcz` | Defect: annotation access does not enforce identity boundaries | unblocked |

Before this run, `bd ready` returned exactly one issue (`agentic-energy-4w2`),
confirming that the dependency gate holds the five dependent issues closed until
the foundation is complete.

## Result

The deterministic fixture profile reconciles. All seven acceptance equations pass
— five from run artifacts directly, one from byte-identical replay, and one from
the manifest's write-once semantics plus the failure-recovery tests. The full
suite passes (24 tests). No production code, test, resource, or bundle file was
modified in the course of producing this evidence.
