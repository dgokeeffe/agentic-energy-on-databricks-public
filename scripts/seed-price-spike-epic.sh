#!/usr/bin/env bash
# Seed the "price spike detector" epic and its child tasks into the participant
# Beads graph. Idempotent: re-running detects the existing epic and exits.
#
# Usage:
#   scripts/bootstrap-participant-beads.sh   # once, to create/sync the graph
#   scripts/seed-price-spike-epic.sh
#   bd epic status && bd ready
set -euo pipefail

if ! command -v bd >/dev/null 2>&1; then
  echo "bd is required; install Beads before seeding the epic." >&2
  exit 1
fi

EPIC_TITLE='Epic: NEMWEB price spike detector'

if bd list --all --flat --no-pager 2>/dev/null | grep -qF "$EPIC_TITLE"; then
  echo "Price spike epic already present."
  bd epic status 2>/dev/null || true
  exit 0
fi

# Resolve the foundation bead so the epic is blocked by a verified fixture run.
foundation_id="$(bd list --all --flat --no-pager 2>/dev/null \
  | grep -F 'Foundation: run the deterministic fixture ETL' \
  | head -1 | awk '{print $2}')"

create() {
  # create <title> <type> <priority> <labels> <parent-or-empty> <<<description
  local title="$1" issue_type="$2" priority="$3" labels="$4" parent="$5"
  local acceptance="$6"
  local args=(--stdin --type="$issue_type" --priority="$priority"
              --labels="$labels" --acceptance="$acceptance" --silent)
  if [ -n "$parent" ]; then
    args+=(--parent "$parent")
  fi
  bd create "$title" "${args[@]}"
}

# ---------------------------------------------------------------- epic --------
epic_id="$(create "$EPIC_TITLE" epic 1 'participant,analytics,price-spike' '' \
  'Gold carries a documented spike flag and per-region/day spike metrics; the threshold is metadata-driven, not hard-coded; deterministic fixture tests cover boundary, negative-price, and null-price cases; a metric view + Genie Agent answer the three benchmark questions; docs record the definition, owner, and freshness.' <<'EOF'
## Problem

The Gold projection (`gold/market_weather.jsonl`) exposes raw
`price_per_mwh` per `(region, interval_utc)` but nothing that identifies the
intervals that actually matter commercially. Price spikes in the NEM are where
most of the cost and most of the risk sits: a handful of 5-minute intervals can
dominate a region's daily spend. Today a participant has to eyeball raw prices,
and no two people define "spike" the same way.

## Outcome

A governed, metadata-driven price spike detector that turns NEMWEB DISPATCHIS
prices into a defensible signal:

- a per-interval spike flag on the Gold grain, with the rule that fired;
- per-region/day spike metrics (count, max price, minutes in spike, spend
  concentration);
- a metric view and scoped Genie Agent so a business user can ask "which region
  spiked most last week?" without writing SQL.

## Scope

In scope:
- spike rule definition and thresholds carried in the source metadata contract;
- detection over the existing canonical market rows (`region`,
  `interval_utc`, `demand_mw`, `price_per_mwh`);
- a Gold spike projection plus manifest evidence;
- deterministic fixtures and tests;
- metric view / Genie Agent / dashboard surface;
- documentation of the definition, owner, and freshness.

Out of scope (follow-on beads):
- forecast-error analytics (`P5MIN`, `PREDISPATCH`);
- FCAS spike detection;
- alerting/notification delivery;
- any writeback to AEMO/NEMWEB.

## Why now

It is the highest value-per-hour analytic available on the current Gold grain:
it needs no new source, no new report family, and no network access, and it
produces the measurable value hypothesis the business lane needs.

## Evidence

- Canonical market row shape: `agentic_energy/acquisition.py`
  (`parse_dispatchis_zip` emits `region`, `interval_datetime`, `demand_mw`,
  `price_per_mwh`).
- Gold projection: `agentic_energy/pipeline.py` (`gold/market_weather.jsonl`).
- Source contract fields, including `quality_checks`:
  `agentic_energy/resources/metadata/sources.live.json`.
- Layer invariants and the manifest contract:
  `docs/serverless-architecture.md`.

## Risks

- **Definition drift** — an undocumented or hard-coded threshold makes the
  metric unauditable. Mitigation: threshold lives in metadata, and the fired
  rule is recorded on every flagged row.
- **Negative and null prices** — NEM prices go negative and DISPATCHIS can omit
  `RRP`; a naive comparison misclassifies both. Mitigation: explicit test cases.
- **Timezone misattribution** — "spikes per day" is a business-local question,
  so day bucketing must use the declared source timezone, not UTC.
- **Live non-determinism** — thresholds must be validated on fixtures, since a
  live NEMWEB run is not reproducible.
EOF
)"

echo "epic: $epic_id"

if [ -n "$foundation_id" ]; then
  bd dep add "$epic_id" "$foundation_id" >/dev/null
  echo "  blocked by foundation: $foundation_id"
fi

# ------------------------------------------------------------- children -------
spec_id="$(create 'Define the price spike rule and thresholds' task 1 \
  'participant,analytics,price-spike,lane-a' "$epic_id" \
  'A written definition names the rule, threshold values per region, the comparison window, the tie/boundary behaviour, and how negative and null prices are treated; the definition is reviewed by the paired lane before implementation starts.' <<'EOF'
Agree and record what counts as a price spike before any code is written.

Decide and document:
- **Absolute rule**: `price_per_mwh > threshold` — pick the workshop default
  (e.g. 300 AUD/MWh) and say why.
- **Relative rule**: `price > k x rolling median` over a stated window
  (e.g. 5x the trailing 24h median) so quiet-market spikes are still caught.
- **Which rule wins** when both fire, and whether the flag is one field plus a
  rule name or one field per rule.
- **Boundary behaviour**: is the comparison strict (`>`) or inclusive (`>=`)?
- **Negative prices**: excluded from spikes, and counted by a separate metric.
- **Null / missing `RRP`**: not a spike; routed by existing quarantine rules.
- **Day bucketing**: business day in the declared `source_timezone`, not UTC.
- **Severity bands** (optional): warn / high / extreme, with numbers.

Deliverable: a short definition block in `docs/` (or the design field of this
bead) that the implementation bead can be checked against, plus a worked example
using the existing fixture rows.
EOF
)"

metadata_id="$(create 'Carry spike thresholds in the metadata contract' task 1 \
  'participant,analytics,price-spike,lane-b,engineering' "$epic_id" \
  'Thresholds are read from the source metadata entry with a documented default; no threshold literal remains in pipeline code; the metadata hash in the manifest changes when a threshold changes; an invalid threshold fails fast with a clear error code.' <<'EOF'
Extend the source metadata contract so the spike rule is configuration, not
code. This is the bead that proves the metadata-driven claim: changing a
threshold must not require a code change or a new job.

Work:
- Add a `spike_rules` (or equivalent) block to the market source entries in
  `agentic_energy/resources/metadata/sources.json` and
  `sources.live.json`, carrying threshold, window, and rule name.
- Document the new fields in the metadata contract table in
  `docs/challenge-spec.md` and `docs/serverless-architecture.md`.
- Mirror the fields in the Lakebase control plane
  (`resources/lakebase/control_plane.sql`) so a deployed run can read them from
  a metadata snapshot.
- Validate on load: missing block falls back to a documented default; a
  malformed threshold raises a clear, named error rather than silently
  disabling detection.
- Confirm the threshold change is visible as a new `metadata_sha256` in
  `manifest.json`.
EOF
)"

impl_id="$(create 'Emit spike flags and metrics into Gold' feature 1 \
  'participant,analytics,price-spike,lane-b,engineering' "$epic_id" \
  'Gold rows carry is_spike plus the fired rule and threshold; a per-region/day spike metrics projection is written; the manifest reports spike counts; existing Gold consumers and layer invariants are unchanged; the same generic worker path is used with no source-specific branch.' <<'EOF'
Implement detection in the pipeline on top of the agreed definition and the
metadata-driven thresholds.

Per-interval, on the existing Gold grain `(region, interval_utc)`:
- `is_spike` (bool), `spike_rule` (name of the rule that fired),
  `spike_threshold` (value applied), and optionally `spike_severity`.
- Preserve existing lineage and freshness fields untouched.

Per-region/day metrics projection (e.g. `gold/spike_metrics.jsonl`):
- `spike_interval_count` and `spike_minutes` (count x 5);
- `max_price_per_mwh` and the interval it occurred in;
- `vwap_per_mwh` = `sum(price x demand) / sum(demand)`;
- `top10_interval_spend_share` — share of daily spend in the 10 priciest
  intervals, the number that justifies load shifting;
- `negative_price_interval_count`;
- day key computed in the declared `source_timezone`.

Manifest: add spike counts to the reconciliation evidence so a run can be
verified without opening the data.

Constraints: no new source-specific job or dispatcher branch; deterministic
output ordering; rolling-window logic must be well defined at the start of a
window where history is short.
EOF
)"

test_id="$(create 'Deterministic tests and fixtures for spike detection' task 1 \
  'participant,analytics,price-spike,lane-b,testing' "$epic_id" \
  'Tests cover threshold boundary, negative price, null/missing price, duplicate interval resolution, rolling-window start, timezone day bucketing, and metadata-driven threshold change; the suite passes offline with no network or credentials.' <<'EOF'
Prove the detector with the deterministic fixture path, not a live run.

Extend `agentic_energy/resources/fixtures/aemo_dispatch.jsonl` (or add a
dedicated spike fixture) and `tests/test_pipeline.py` to cover:
- price exactly at the threshold (boundary semantics from the definition bead);
- price just above and just below;
- a negative price (must not be a spike; must be counted separately);
- a null / missing `price_per_mwh`;
- duplicate rows for the same `(region, interval_datetime)` where the winning
  record by `ingestion_sequence` decides the flag;
- rolling-window start with insufficient history;
- a day boundary in the declared source timezone, including a daylight-saving
  edge for the `Australia/Sydney` fixture source;
- changing the metadata threshold flips the flag with no code change.

Also assert the manifest spike counts reconcile with the Gold rows, and that
`gold/market_weather.jsonl` remains byte-stable for non-spike fields.

Run: `uv run --extra test python -m pytest`
EOF
)"

view_id="$(create 'Metric view and scoped Genie Agent for spikes' task 2 \
  'participant,analytics,price-spike,lane-a,genie' "$epic_id" \
  'A metric view exposes the spike measures over the governed Gold projection; a scoped Genie Agent grounded in it answers the three benchmark questions correctly and refuses out-of-scope questions; owner, source, and freshness are visible on the surface.' <<'EOF'
Make the spike signal answerable in natural language by a business user.

- Build a metric view over the governed Gold spike projection with dimensions
  `region` and time, and measures `spike_interval_count`, `max_price_per_mwh`,
  `vwap_per_mwh`, `negative_price_interval_count`,
  `top10_interval_spend_share`.
- Ground a scoped Genie Agent in that metric view only (no raw Bronze/Silver).
- Benchmark questions to verify:
  1. "Which region had the most price spikes last week?"
  2. "What was the highest 5-minute price in VIC1 yesterday, and when?"
  3. "What share of yesterday's NSW1 spend landed in the 10 priciest
     intervals?"
- Record a refusal or fallback case for a question the data cannot answer
  (e.g. anything about individual generators, which needs `Dispatch_SCADA`).
- Surface owner, source, and freshness on the resulting dashboard or app.

Depends on the Gold spike projection existing.
EOF
)"

docs_id="$(create 'Document the spike definition, owner, and freshness' task 2 \
  'participant,analytics,price-spike,docs' "$epic_id" \
  'Documentation states the spike definition and thresholds, the owner, the grain, the freshness expectation and its source, the negative/null price treatment, and the known limitations; a reader can reproduce the metric from the docs alone.' <<'EOF'
Write the definition down where a consumer of the metric will find it.

Cover:
- the spike rule, thresholds, and severity bands as shipped;
- the grain (`region` x 5-minute dispatch interval) and the day bucketing
  timezone;
- the owner and the escalation path for a disputed number;
- freshness: DISPATCHIS publishes every 5 minutes, so state the expected lag
  and where it is measured (`pipeline_ingested_at` vs `latest_event_utc` in the
  manifest);
- treatment of negative prices, null prices, and quarantined rows;
- limitations: no FCAS, no interconnector/constraint context, no unit-level
  attribution, and live runs are non-deterministic;
- licensing/provenance note for AEMO NEMWEB data reuse.
EOF
)"

# Sequencing inside the epic: definition -> metadata -> implementation ->
# tests, with the consumer surfaces gated on the implementation.
bd dep add "$metadata_id" "$spec_id"  >/dev/null
bd dep add "$impl_id"     "$spec_id"  >/dev/null
bd dep add "$impl_id" "$metadata_id"  >/dev/null
bd dep add "$test_id"     "$impl_id"  >/dev/null
bd dep add "$view_id"     "$impl_id"  >/dev/null
bd dep add "$docs_id"     "$spec_id"  >/dev/null

if [ -n "$foundation_id" ]; then
  bd dep add "$spec_id" "$foundation_id" >/dev/null
fi

echo
echo "Seeded the price spike epic:"
echo "  $epic_id     $EPIC_TITLE"
echo "  $spec_id     Define the price spike rule and thresholds"
echo "  $metadata_id Carry spike thresholds in the metadata contract"
echo "  $impl_id     Emit spike flags and metrics into Gold"
echo "  $test_id     Deterministic tests and fixtures for spike detection"
echo "  $view_id     Metric view and scoped Genie Agent for spikes"
echo "  $docs_id     Document the spike definition, owner, and freshness"
echo
bd epic status 2>/dev/null || true
echo
bd ready
