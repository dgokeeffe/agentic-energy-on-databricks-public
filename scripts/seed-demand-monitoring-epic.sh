#!/usr/bin/env bash
# Seed the "demand monitoring" epic and its child stories into the participant
# Beads graph. Idempotent: re-running detects the existing epic and exits.
#
# Extends the pipeline to a SECOND NEMWEB report family (DISPATCHREGIONSUM) so
# operators can monitor regional demand, not just price.
#
# Usage:
#   scripts/bootstrap-participant-beads.sh   # once, to create/sync the graph
#   scripts/seed-demand-monitoring-epic.sh
#   bd epic status && bd ready
set -euo pipefail

if ! command -v bd >/dev/null 2>&1; then
  echo "bd is required; install Beads before seeding the epic." >&2
  exit 1
fi

EPIC_TITLE='Epic: demand monitoring from a second NEMWEB report family'

if bd list --all --flat --no-pager 2>/dev/null | grep -qF "$EPIC_TITLE"; then
  echo "Demand monitoring epic already present."
  bd epic status 2>/dev/null || true
  exit 0
fi

# Resolve the foundation bead so the epic is blocked by a verified fixture run.
# Optional: a clean database (no bootstrap yet) has no foundation bead, and grep
# exiting 1 must not abort the seed under `set -o pipefail`.
foundation_id="$(bd list --all --flat --no-pager 2>/dev/null \
  | { grep -F 'Foundation: run the deterministic fixture ETL' || true; } \
  | head -1 | awk '{print $2}')"

create() {
  # create <title> <type> <priority> <labels> <parent-or-empty> <acceptance>
  # description on stdin
  local title="$1" issue_type="$2" priority="$3" labels="$4" parent="$5"
  local acceptance="${6:-}"
  local args=(--stdin --type="$issue_type" --priority="$priority"
              --labels="$labels" --silent)
  if [ -n "$acceptance" ]; then
    args+=(--acceptance="$acceptance")
  fi
  if [ -n "$parent" ]; then
    args+=(--parent "$parent")
  fi
  bd create "$title" "${args[@]}"
}

LABELS='demand-monitoring,engineering,lane-b'

# ---------------------------------------------------------------- epic --------
epic_id="$(create "$EPIC_TITLE" epic 1 "$LABELS" '' '' <<'EOF'
Extend the metadata-driven pipeline to ingest DISPATCHREGIONSUM (region demand)
as a second NEMWEB report family and publish hourly/daily demand aggregates in
Gold, so operators can monitor regional demand without a source-specific job.

Scope
- New parser for DISPATCHREGIONSUM in `agentic_energy/acquisition.py`
- Recognise DISPATCHREGIONSUM as a dataset in `agentic_energy/pipeline.py`
  (validation allowlist + market/weather branching + live acquisition dispatch)
- New Gold outputs: `gold/hourly_demand.jsonl`, `gold/daily_demand.jsonl`
- Fixture + metadata entries so the work is testable offline

Constraints
- Python stdlib only; no new dependencies
- No new source-specific orchestration: metadata drives the same worker path
- Deterministic output: byte-identical reruns, sorted keys, stable ordering
- TDD: failing test -> minimal implementation -> passing test -> commit

Reference
- `docs/challenge-spec.md` section 7 (shared data foundation) and the stretch
  goal "Add a second live NEMWEB report family"
- `docs/serverless-architecture.md:156` for the existing DISPATCHIS adapter
EOF
)"

# --------------------------------------------------------------- stories ------
parser_id="$(create 'Parse DISPATCHREGIONSUM archives into canonical demand rows' story 1 "$LABELS" "$epic_id" \
  'parse_dispatchregionsum_zip returns one row per (settlement, region, intervention) with region/interval_datetime/demand_mw/ingestion_sequence/source_file; raises NEMWEB_DISPATCHREGIONSUM_NO_REGION_ROWS when no usable D REGIONSUM rows exist; enforces MAX_ARCHIVE_MEMBER_BYTES; rows sorted deterministically; unit test builds an in-memory ZIP fixture and passes.' <<'EOF'
Add `parse_dispatchregionsum_zip(payload: bytes, source_file: str) -> list[dict]`
to `agentic_energy/acquisition.py`, plus
`acquire_live_dispatchregionsum(source)` mirroring `acquire_live_dispatchis`.

Files
- Modify: `agentic_energy/acquisition.py` (model on `parse_dispatchis_zip`, currently line 92, and `acquire_live_dispatchis`, line 158)
- Test: `tests/test_pipeline.py` (see `parse_dispatchis_zip` import at line 9 for the existing pattern)

Behaviour
- Read the first `.CSV` / `.CSV.TXT` member, reject members over
  `MAX_ARCHIVE_MEMBER_BYTES`, decode latin-1 (same as DISPATCHIS)
- Track `I` header rows per (report, version); consume only `D` rows where
  report == "REGIONSUM"
- Key on (SETTLEMENTDATE, REGIONID, INTERVENTION default "0")
- Emit demand-only canonical rows:
  `{"region", "interval_datetime": _timestamp(SETTLEMENTDATE), "demand_mw":
  _parse_number(TOTALDEMAND), "ingestion_sequence": int(DISPATCHINTERVAL or 0),
  "source_record_types": ["REGIONSUM"], "source_line_numbers": [line],
  "source_file"}`
- Skip rows with empty TOTALDEMAND; raise
  `RuntimeError("NEMWEB_DISPATCHREGIONSUM_NO_REGION_ROWS")` if nothing usable
- Sort output by (settlement, region, intervention) for determinism

Steps (TDD)
1. Write a failing test that builds an in-memory ZIP with I/D REGIONSUM rows
   (plus a PRICE record that must be ignored) and asserts the parsed rows.
2. Run `uv run --extra test python -m pytest tests/test_pipeline.py -k regionsum -v` and confirm it fails.
3. Implement the parser minimally.
4. Re-run the test; then run the full suite.
5. Commit.

Notes
- No network access in tests; never hit NEMWEB from a unit test.
- Do NOT reuse the PRICE join from DISPATCHIS: this source is demand-only, so
  `price_per_mwh` must not be invented.
EOF
)"

dataset_id="$(create 'Recognise DISPATCHREGIONSUM as a first-class dataset in the pipeline' story 1 "$LABELS" "$epic_id" \
  'A DISPATCHREGIONSUM source in sources.json validates and flows through Bronze/Silver/Quarantine with correct reconciliation; demand-only validation rejects negative/non-finite demand without requiring price; live mode dispatches to acquire_live_dispatchregionsum; no source-specific branch is added outside the dataset lookup; existing DISPATCHIS and weather tests still pass.' <<'EOF'
Teach `agentic_energy/pipeline.py` about the new dataset so metadata alone can
enable it — no new orchestration path.

Files
- Modify: `agentic_energy/pipeline.py`
  - `_validate_source` dataset allowlist (line ~145): add `DISPATCHREGIONSUM`
    with allowed natural-key fields `region`, `interval_utc`,
    `ingestion_sequence`, `demand_mw` (NOT `price_per_mwh`)
  - `_source_rows` (line ~174): dispatch live acquisition by dataset instead of
    unconditionally calling `acquire_live_dispatchis`
  - Row validation (line ~291): replace the boolean `is_market` split with a
    dataset-driven notion of which measure columns are required, so
    DISPATCHREGIONSUM requires `demand_mw` only and emits `INVALID_DEMAND`
    without demanding `price_per_mwh`
  - Silver projection (line ~344): emit `demand_mw` only for this dataset
- Test: `tests/test_pipeline.py`

Steps (TDD)
1. Failing test: run the pipeline over a tiny metadata doc containing a
   DISPATCHREGIONSUM fixture source; assert Bronze/Silver/Quarantine counts and
   that an accepted Silver row has `demand_mw` and no `price_per_mwh` key.
2. Failing test: a row with `demand_mw: -1` is quarantined with
   `INVALID_DEMAND`, and a row missing `price_per_mwh` is NOT quarantined.
3. Run the tests, confirm they fail for the right reason.
4. Implement minimally; keep the change table-driven (a dataset -> required
   measures map) rather than adding `if dataset == ...` chains.
5. Full suite green, then commit.

Watch out
- `market_sources` at line ~378 asserts exactly one market source and one
  weather source. Adding DISPATCHREGIONSUM must not break that guard — scope
  the existing market/weather Gold join to `DISPATCH_SCADA`/`DISPATCHIS` only.
- Reconciliation invariants (`BRONZE_RECONCILIATION_FAILED`,
  `SILVER_RECONCILIATION_FAILED`) must still hold per source.
EOF
)"

gold_id="$(create 'Publish hourly and daily demand aggregates in Gold' story 1 "$LABELS" "$epic_id" \
  'gold/hourly_demand.jsonl and gold/daily_demand.jsonl are written with region/bucket/avg_demand_mw/peak_demand_mw/interval_count/freshness/lineage; aggregates derive from deduplicated Silver only; manifest.layers reports the new counts; two runs produce byte-identical files; rounding and ordering are deterministic.' <<'EOF'
Add demand aggregate Gold outputs alongside the existing
`gold/market_weather.jsonl`.

Files
- Modify: `agentic_energy/pipeline.py` (Gold section, lines ~378-400, and the
  `manifest` dict at ~400)
- Test: `tests/test_pipeline.py`

Output contract
`gold/hourly_demand.jsonl`, one row per (region, hour):
```json
{"region": "NSW1", "interval_hour_utc": "2024-04-07T00:00:00Z",
 "avg_demand_mw": 8225.0, "peak_demand_mw": 8250.0, "interval_count": 2,
 "freshness": {"pipeline_ingested_at": "...", "latest_event_utc": "..."},
 "lineage": {"source_ids": ["..."]}}
```
`gold/daily_demand.jsonl` is the same shape with `interval_day_utc`
(`YYYY-MM-DD`) instead of `interval_hour_utc`.

Rules
- Aggregate from the deduplicated Silver rows of every demand-bearing dataset
  (`DISPATCH_SCADA`, `DISPATCHIS`, `DISPATCHREGIONSUM`)
- Buckets are derived from `interval_utc` (already UTC) — never re-derive from
  local time
- `avg_demand_mw` rounded to 3 decimals to keep output byte-stable
- Sort by (region, bucket); write with `_write_jsonl` so JSON stays canonical
- Extend `manifest["layers"]` with `gold_hourly_demand` and
  `gold_daily_demand` counts; keep the existing `gold` key meaning unchanged
- Empty input must produce an empty file, not a missing one (staging/promotion
  path in `_promote_output` already handles replacement)

Steps (TDD)
1. Failing test: assert hourly rows for a two-interval hour give the expected
   avg/peak/count, and that a day bucket spans its hours.
2. Failing test: idempotency — run twice into different dirs and compare bytes
   (mirror `test_end_to_end_contract_and_idempotency`, line 17).
3. Confirm failures, implement minimally, re-run, full suite.
4. Commit.
EOF
)"

fixture_id="$(create 'Ship DISPATCHREGIONSUM fixtures and metadata entries' story 1 "$LABELS" "$epic_id" \
  'sources.json gains a fixture DISPATCHREGIONSUM entry backed by a checked-in JSONL fixture including at least one quarantine case; sources.live.json gains the live NEMWEB entry with an https URL and Australia/Sydney timezone; end-to-end counts in tests/test_pipeline.py are updated to the new expected totals; docs describe the new source and Gold outputs; the offline suite passes with no network access.' <<'EOF'
Make the new source usable offline (fixture profile) and deployable (live
profile), and document it.

Files
- Create: `agentic_energy/resources/fixtures/aemo_regionsum.jsonl`
- Modify: `agentic_energy/resources/metadata/sources.json`
- Modify: `agentic_energy/resources/metadata/sources.live.json`
- Modify: `tests/test_pipeline.py` (expected layer counts, line ~22)
- Modify: `docs/challenge-spec.md` (section 7 source table) and
  `docs/serverless-architecture.md` (acquisition adapters section, ~line 156)

Fixture design (deliberate, small, deterministic)
- 2 valid NSW1 intervals in the same hour (exercises hourly averaging)
- 1 duplicate of one of those with a higher `ingestion_sequence`
  (exercises `last_by_ingestion_sequence`)
- 1 VIC1 interval on a different day (exercises daily bucketing)
- 1 row with `demand_mw: -1` (must quarantine as `INVALID_DEMAND`)
- Local wall-clock `interval_datetime` values, `Australia/Sydney` timezone

Metadata entry (fixture profile)
```
source_id: aemo_regionsum_fixture, provider: AEMO, dataset: DISPATCHREGIONSUM,
format: JSONL, extraction_mode: fixture,
event_timestamp_field: interval_datetime, source_timezone: Australia/Sydney,
natural_key: ["region", "interval_datetime"], watermark_field: interval_datetime,
deduplication_rule: last_by_ingestion_sequence,
quality_checks: ["demand_mw >= 0"], quarantine_policy: isolate_with_reason,
licensing_provenance: "AEMO-shaped deterministic workshop fixture"
```

Steps
1. Write the fixture and metadata entries.
2. Run the suite; update the asserted Bronze/Silver/Quarantine/Gold totals in
   `test_end_to_end_contract_and_idempotency` to the new expected values —
   recompute them by hand from the fixture, do not just paste whatever the run
   printed.
3. Add the live entry to `sources.live.json` with the NEMWEB
   `Reports/Current/DispatchIS_Reports/` style URL for the REGIONSUM family and
   confirm `_validate_remote_url` accepts the host.
4. Update both docs; commit.

Watch out
- Live metadata must not be exercised by the offline test suite.
- Do not change existing fixtures; that would perturb other tests' evidence.
EOF
)"

# Sequencing inside the epic: parse -> recognise as a dataset -> {Gold
# aggregates, fixtures+metadata}. The parser lands first because everything
# else consumes its canonical rows.
bd dep add "$dataset_id" "$parser_id"  >/dev/null
bd dep add "$gold_id"    "$dataset_id" >/dev/null
bd dep add "$fixture_id" "$dataset_id" >/dev/null

if [ -n "$foundation_id" ]; then
  bd dep add "$parser_id" "$foundation_id" >/dev/null
fi

echo
echo "Seeded the demand monitoring epic:"
echo "  $epic_id    $EPIC_TITLE"
echo "  $parser_id  Parse DISPATCHREGIONSUM archives into canonical demand rows"
echo "  $dataset_id Recognise DISPATCHREGIONSUM as a first-class dataset in the pipeline"
echo "  $gold_id    Publish hourly and daily demand aggregates in Gold"
echo "  $fixture_id Ship DISPATCHREGIONSUM fixtures and metadata entries"
echo
bd epic status 2>/dev/null || true
echo
bd ready
