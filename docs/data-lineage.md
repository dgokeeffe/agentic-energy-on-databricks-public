# Data lineage — Bronze / Silver / Quarantine / Gold

Technical reference for the layer contracts, per-record lineage, and the
datasets each layer produces. All record-level examples in this document are the
**actual output** of the deterministic fixture profile:

```bash
uv run python -m agentic_energy.cli --output output
# Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3
```

Because fixture mode pins `pipeline_ingested_at` from the metadata contract
(`agentic_energy/pipeline.py`, `_ingestion_timestamp`), replaying the run
reproduces every file byte-for-byte. Verified: two runs into separate output
directories are `sha256`-identical.

> Scope note: this document describes the **local fixture profile**, which is
> the scored baseline. The Databricks deployment writes the same layer
> structure to a Unity Catalog Volume — see [Physical layout](#physical-layout).

## Contents

- [Pipeline at a glance](#pipeline-at-a-glance)
- [Datasets per layer](#datasets-per-layer)
- [Layer schemas](#layer-schemas)
- [Record-level lineage](#record-level-lineage)
- [Quarantine reason codes](#quarantine-reason-codes)
- [Reconciliation contract](#reconciliation-contract)
- [Physical layout](#physical-layout)
- [Control-plane tables](#control-plane-tables)
- [How to reproduce](#how-to-reproduce)

## Pipeline at a glance

```
metadata/sources.json  (contract; sha256 recorded in the manifest)
        │
        ▼
   ┌─────────┐   every raw row, unmodified + row number
   │ BRONZE  │   11 rows / 2 files
   └────┬────┘
        │  validate: shape, region, sequence, measures, event timestamp
        │  normalize: local wall-clock ──▶ UTC via declared source_timezone
        ├──────────────────────────────▶ ┌────────────┐  3 rows / 1 file
        │        rows failing a check    │ QUARANTINE │  reason_codes + raw_record
        │                                └────────────┘
        ▼  accepted = 8
   deduplicate by natural_key, rule last_by_ingestion_sequence  (−2)
        │
        ▼
   ┌─────────┐   typed, UTC-normalized, unique by natural key
   │ SILVER  │   6 rows / 2 files
   └────┬────┘
        │  inner-ish join on (region, interval_utc); market row drives the grain
        ▼
   ┌─────────┐   market × weather projection + freshness + dual lineage
   │  GOLD   │   3 rows / 1 file
   └─────────┘
        │
        ▼
   manifest.json  (layer counts, per-source reconciliation, metadata_sha256)
```

The worker is generic: it is driven entirely by the source metadata rows and
contains no source-specific branching beyond dataset **class**
(`DISPATCH_SCADA`/`DISPATCHIS` = market, `HOURLY_WEATHER` = weather).

## Datasets per layer

| Layer | Dataset / file | Grain | Rows | Written by |
|---|---|---|---|---|
| Bronze | `bronze/aemo_dispatch_fixture.jsonl` | one per raw source line | 6 | per source, in metadata order |
| Bronze | `bronze/weather_fixture.jsonl` | one per raw source line | 5 | per source, in metadata order |
| Silver | `silver/aemo_dispatch_fixture.jsonl` | one per natural key | 3 | after dedup, sorted `(region, interval_utc)` |
| Silver | `silver/weather_fixture.jsonl` | one per natural key | 3 | after dedup, sorted `(region, interval_utc)` |
| Quarantine | `quarantine/rejected.jsonl` | one per rejected raw row | 3 | **single shared file, all sources**, sorted `(source_id, source_row_number)` |
| Gold | `gold/market_weather.jsonl` | one per market natural key | 3 | sorted `(region, interval_utc)` |
| Evidence | `manifest.json` | one per run | 1 | last, after all reconciliation asserts pass |

Two structural points worth knowing:

- Bronze and Silver are **partitioned by `source_id`** (one file each). Adding a
  source adds files, not code.
- Quarantine is **not** partitioned — every source's rejects land in one
  `rejected.jsonl`, discriminated by the `source_id` field.

## Layer schemas

### Bronze — `bronze/<source_id>.jsonl`

Immutable capture. No coercion, no filtering; malformed JSON is still captured
here with `raw_record: null`.

| Field | Type | Meaning |
|---|---|---|
| `source_id` | string | source that produced the row |
| `source_file` | string | fixture path or live artifact name |
| `source_row_number` | int | **1-based line number in the source** — the lineage spine |
| `raw_line` | string | the original line, verbatim |
| `raw_record` | object \| null | parsed JSON, or `null` when unparseable |
| `_ingested_at` | string | run ingestion instant (`ingestion_timestamp_field`) |

```json
{"_ingested_at":"2024-04-07T00:00:00Z","raw_line":"{\"region\":\"NSW1\",...}",
 "raw_record":{"region":"NSW1","interval_datetime":"2024-04-07T10:00:00","demand_mw":8200,
               "price_per_mwh":72.5,"ingestion_sequence":1},
 "source_file":"fixtures/aemo_dispatch.jsonl","source_id":"aemo_dispatch_fixture",
 "source_row_number":1}
```

### Silver — `silver/<source_id>.jsonl`

Typed, timezone-normalized, deduplicated. Shared columns plus a per-dataset
measure set.

| Field | Type | Notes |
|---|---|---|
| `source_id`, `source_file`, `source_row_number` | — | carried from Bronze; **the surviving row's** number |
| `region` | string | validated non-empty string |
| `interval_utc` | string | local `event_timestamp_field` converted to UTC, `Z`-suffixed |
| `ingestion_sequence` | int | dedup tiebreaker |
| `demand_mw`, `price_per_mwh` | number | market datasets only |
| `temperature_c` | number | weather datasets only |
| `lineage` | object | `source_id`, `source_version`, `provider`, `dataset`, `licensing_provenance`, `source_file`, `source_row_number` |

Note the field **rename**: the source's local field (`interval_datetime` /
`observed_at`) does not survive into Silver. It becomes `interval_utc` for both
datasets, which is what makes the Gold join uniform. Natural keys are therefore
evaluated *after* normalization — `natural_key: ["region","interval_datetime"]`
is resolved against `interval_utc`.

### Quarantine — `quarantine/rejected.jsonl`

| Field | Type | Notes |
|---|---|---|
| `source_id`, `source_file`, `source_row_number` | — | points back to the exact Bronze row |
| `reason_codes` | **array** of string | **all** failed checks, not just the first |
| `rejected_at` | string | equals the run ingestion instant |
| `raw_record` | object \| null | the offending payload, preserved for triage |

`reason_codes` is a list, not a scalar `reason_code`. A row failing two checks
carries both codes.

### Gold — `gold/market_weather.jsonl`

| Field | Type | Notes |
|---|---|---|
| `region`, `interval_utc` | string | join key; grain is the **market** row |
| `demand_mw`, `price_per_mwh` | number | from the market source |
| `temperature_c` | number \| **null** | from the weather source, `null` on no match |
| `freshness` | object | `pipeline_ingested_at`, `latest_event_utc` |
| `lineage.market` | object | full market Silver lineage block |
| `lineage.weather` | object \| **null** | full weather Silver lineage, `null` on no match |
| `lineage.source_ids` | array | both contributing source ids |

The join is **left, market-driven**: an unmatched market interval still emits a
Gold row with `temperature_c: null` and `lineage.weather: null`. Quarantining a
weather row therefore silently degrades Gold enrichment rather than dropping the
market fact — see the QLD1 case below.

## Record-level lineage

Every one of the 11 Bronze rows, traced to its fate. This is the table to read
if you want to understand the pipeline in one screen.

### `aemo_dispatch_fixture` — 6 Bronze → 3 Silver, 2 quarantined, 1 deduped

| Bronze row | seq | region | local timestamp | Outcome | `interval_utc` |
|---|---|---|---|---|---|
| 1 | 1 | NSW1 | 2024-04-07T10:00:00 | **DEDUPED** — superseded by row 2 | — |
| 2 | 2 | NSW1 | 2024-04-07T10:00:00 | **SILVER** → Gold | `2024-04-07T00:00:00Z` |
| 3 | 1 | VIC1 | 2024-04-07T10:30:00 | **SILVER** → Gold | `2024-04-07T00:30:00Z` |
| 4 | 1 | QLD1 | 2024-04-07T11:00:00 | **QUARANTINE** `["INVALID_DEMAND"]` (`demand_mw: -1`) | — |
| 5 | 1 | NSW1 | 2024-04-07T11:30:00 | **QUARANTINE** `["MISSING_PRICE"]` (`price_per_mwh: null`) | — |
| 6 | 1 | NSW1 | 2024-01-15T10:00:00 | **SILVER** → Gold | `2024-01-14T23:00:00Z` |

### `weather_fixture` — 5 Bronze → 3 Silver, 1 quarantined, 1 deduped

| Bronze row | seq | region | local timestamp | Outcome | `interval_utc` |
|---|---|---|---|---|---|
| 1 | 1 | NSW1 | 2024-04-07T10:00:00 | **DEDUPED** — superseded by row 3 | — |
| 2 | 1 | VIC1 | 2024-04-07T10:30:00 | **SILVER** → Gold | `2024-04-07T00:30:00Z` |
| 3 | 2 | NSW1 | 2024-04-07T10:00:00 | **SILVER** → Gold | `2024-04-07T00:00:00Z` |
| 4 | 1 | QLD1 | 2024-04-07T11:00:00 | **QUARANTINE** `["MISSING_TEMPERATURE"]` (`null`) | — |
| 5 | 1 | NSW1 | 2024-01-15T10:00:00 | **SILVER** → Gold | `2024-01-14T23:00:00Z` |

Dedup is *not* positional: in the market source the later line wins, in the
weather source row 3 beats row 1. The rule is `last_by_ingestion_sequence` —
highest `ingestion_sequence` per natural key, with `>=` so equal sequences
resolve to last-seen.

### DST correctness

The two fixture dates straddle the Australian DST boundary, and the offsets
differ accordingly — the pipeline does not hardcode one:

| Local (`Australia/Sydney`) | UTC | Offset | Period |
|---|---|---|---|
| 2024-01-15T10:00:00 | `2024-01-14T23:00:00Z` | +11 | AEDT (summer) |
| 2024-04-07T10:00:00 | `2024-04-07T00:00:00Z` | +10 | AEST (winter) |

`_utc_timestamp` round-trips each candidate offset and rejects a value it cannot
resolve to exactly one, emitting `NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME` for DST
gaps and folds instead of guessing. 2024-04-07 is Australia's DST-end date, so
the 02:00–03:00 fold sits inside this fixture's day by design.

### Gold join provenance

| region | `interval_utc` | demand | price | temp | market Bronze row | weather Bronze row |
|---|---|---|---|---|---|---|
| NSW1 | `2024-01-14T23:00:00Z` | 8100 | 68.0 | 29.0 | 6 | 5 |
| NSW1 | `2024-04-07T00:00:00Z` | 8250 | 70.0 | 24.5 | 2 | 3 |
| VIC1 | `2024-04-07T00:30:00Z` | 5100 | 65.0 | 18.5 | 3 | 2 |

Any Gold value is attributable to two source lines by number. Note the QLD1
11:00 interval appears in **neither** Gold nor Silver: its market row was
quarantined (`INVALID_DEMAND`) *and* its weather row was quarantined
(`MISSING_TEMPERATURE`), so the region drops out of the projection entirely —
visible only in `quarantine/rejected.jsonl`. That is the intended behaviour, and
it is why quarantine is load-bearing evidence rather than a log.

## Quarantine reason codes

Emitted per row into `reason_codes` (`agentic_energy/pipeline.py`):

| Code | Trigger | Applies to |
|---|---|---|
| `INVALID_JSON:<detail>` | line is not parseable JSON | all |
| `INVALID_RECORD_SHAPE` | parsed value is not an object | all |
| `MISSING_REGION` | `region` absent or falsy | all |
| `INVALID_REGION` | `region` present but not a string | all |
| `INVALID_INGESTION_SEQUENCE` | not a non-negative int (bools rejected) | all |
| `INVALID_DEMAND` | `demand_mw` non-numeric, non-finite, or `< 0` | market |
| `MISSING_PRICE` | `price_per_mwh` non-numeric or non-finite | market |
| `MISSING_TEMPERATURE` | `temperature_c` non-numeric or non-finite | weather |
| `MISSING_EVENT_TIMESTAMP` | declared event field absent or falsy | all |
| `INVALID_EVENT_TIMESTAMP` | unparseable or date-only value | all |
| `OFFSET_NOT_ALLOWED` | value carries a tz offset; contract expects local wall-clock | all |
| `NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME` | DST gap or fold | all |

Guardrails that **fail the run** rather than quarantine a row (these are
`ValueError`/`RuntimeError`, not reason codes): `INVALID_SOURCE_ID`,
`INVALID_NATURAL_KEY`, `INVALID_EXTRACTION_MODE`, `INVALID_FIXTURE_PATH`,
`FIXTURE_PATH_OUTSIDE_ROOT`, `INVALID_LIVE_SOURCE_URL`, `DUPLICATE_SOURCE_ID`,
`LIVE_MODE_NOT_ALLOWED`, `METADATA_PATH_OUTSIDE_ROOT`,
`OUTPUT_PATH_CONFLICTS_WITH_METADATA_ROOT`, `INVALID_METADATA_SNAPSHOT_ID`,
`INVALID_RUN_MODE`, `BRONZE_RECONCILIATION_FAILED:<source_id>`,
`SILVER_RECONCILIATION_FAILED:<source_id>`. Bad **data** is isolated; a bad
**contract** stops everything.

## Reconciliation contract

`manifest.json` from the current fixture run:

```json
{
  "layers":   {"bronze": 11, "silver": 6, "quarantine": 3, "gold": 3},
  "mode":     "fixture",
  "metadata_sha256": "e2235552b0131cfc2272a6a1da5075a8bea2d5a66c13d57496b8f770562ca94e",
  "pipeline_ingested_at": "2024-04-07T00:00:00Z",
  "source_definitions": {"read": 2, "selected": 2},
  "source_ids": ["aemo_dispatch_fixture", "weather_fixture"],
  "sources": {
    "aemo_dispatch_fixture": {"bronze": 6, "accepted": 4, "quarantine": 2, "silver": 3, "deduplicated": 1},
    "weather_fixture":       {"bronze": 5, "accepted": 4, "quarantine": 1, "silver": 3, "deduplicated": 1}
  }
}
```

The acceptance equations from [`workshop-acceptance.md`](workshop-acceptance.md),
each checked against this run:

| Equation | aemo | weather |
|---|---|---|
| `source definitions read == selected` | 2 == 2 ✓ | — |
| `bronze == accepted + quarantine` | 6 == 4+2 ✓ | 5 == 4+1 ✓ |
| `accepted == silver + deduplicated` | 4 == 3+1 ✓ | 4 == 3+1 ✓ |
| `silver keys unique by natural key` | 3/3 ✓ | 3/3 ✓ |
| `silver timestamps normalized` | all `Z` ✓ | all `Z` ✓ |
| `identical replay` | byte-identical `sha256` ✓ | ✓ |

The first two equations are enforced **in code** and abort the run
(`BRONZE_RECONCILIATION_FAILED` / `SILVER_RECONCILIATION_FAILED`), so a manifest
that exists at all has already passed them.

`metadata_sha256` hashes the contract bytes, which is what ties a set of
artifacts to the exact metadata that produced them. Suite status at time of
writing: `uv run --extra test python -m pytest` → 24 passed.

### Write-once promotion

Layers are built in a staging directory and promoted with `os.replace` only
after the manifest is written. When `--run-id` is supplied (the deployed job
path) promotion is **write-once**: an existing output raises
`OUTPUT_ALREADY_EXISTS` under an advisory `flock`, so a job retry can never
overwrite a prior run's evidence. Local runs without `--run-id` may replace, and
a failed promotion restores the previous output from a backup.

## Physical layout

Local:

```
output/
├── bronze/{aemo_dispatch_fixture,weather_fixture}.jsonl
├── silver/{aemo_dispatch_fixture,weather_fixture}.jsonl
├── quarantine/rejected.jsonl
├── gold/market_weather.jsonl
└── manifest.json
```

Deployed (`resources/agentic_energy_job.job.yml`) — same tree, per run, on a
Unity Catalog Volume:

```
/Volumes/<catalog>/<schema>/<landing_volume>/<target>/runs/<job.run_id>/
```

Dev values are `edp_entdata_exp_dev_landing` / `agentic_energy` /
`agentic_energy_landing`. The immutable per-run manifest under the Volume — not
the disposable per-developer job — is the durable evidence of a run. The
deployed task pins `--mode fixture`; live mode requires a reviewed bundle change
and a human gate.

## Control-plane tables

`resources/lakebase/control_plane.sql` defines the Lakebase (Postgres) control
plane. It holds **metadata and run evidence, never the ETL data itself**.

| Table | Grain | Purpose |
|---|---|---|
| `agentic_energy.source_metadata` | one per `source_id` | the contract: format, timezone, natural key, watermark, quality checks, quarantine policy. Rows *select* registered adapters; they never carry executable code. |
| `agentic_energy.metadata_versions` | one per `snapshot_id` | immutable validated snapshots (`validated`/`superseded`/`rejected`) making each run reproducible |
| `agentic_energy.pipeline_runs` | one per dispatcher run | status plus `bronze/accepted/quarantine/silver/gold` counts, watermark, freshness, failure stage/code |
| `agentic_energy.pipeline_run_sources` | one per (run, source) | per-source worker execution and reconciliation evidence |

The count columns on `pipeline_runs` / `pipeline_run_sources` mirror
`manifest.json` exactly — the same reconciliation equations hold in the
control plane as on disk. `pipeline_runs.snapshot_id` is a FK to
`metadata_versions`, so no run can exist without the contract it ran.

## How to reproduce

```bash
# 1. deterministic fixture run — no workspace, credentials, or network
uv run python -m agentic_energy.cli --output output

# 2. contract tests
uv run --extra test python -m pytest

# 3. prove determinism (expect identical hashes)
uv run python -m agentic_energy.cli --output output-replay
find output        -type f | sort | xargs sha256sum | sed 's#output/##'
find output-replay -type f | sort | xargs sha256sum | sed 's#output-replay/##'

# 4. trace one Bronze row end to end
python3 - <<'PY'
import json
row = 6
for layer in ("bronze", "silver"):
    for line in open(f"output/{layer}/aemo_dispatch_fixture.jsonl"):
        r = json.loads(line)
        if r["source_row_number"] == row:
            print(layer, json.dumps(r, indent=2)[:400])
PY
```

## Related

- [`workshop-acceptance.md`](workshop-acceptance.md) — the acceptance gate these equations come from
- [`serverless-architecture.md`](serverless-architecture.md) — dispatcher/worker design
- [`deployment.md`](deployment.md) — bundle targets, UC grants, per-developer `dev` rules
- [`challenge-spec.md`](challenge-spec.md) — seeded defect classes, including quarantine bypass
