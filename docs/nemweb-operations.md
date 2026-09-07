# NEMWEB operation, validation and evidence

This runbook is for the workshop operator. It separates repository validation,
workspace mutation and live proof so configuration cannot be mistaken for data
freshness.

## Runtime contracts

| Path | Source cadence | Published contract |
|---|---:|---|
| DISPATCHIS PRICE + REGIONSUM | five minutes | regional price (AUD/MWh) and demand (MW) |
| Dispatch SCADA UNIT_SCADA | five minutes | per-DUID actual MW and region/fuel aggregation |
| DISPATCHIS CONSTRAINT | five minutes | raw constraints in Silver; non-zero marginal-value binding derivation in Gold |
| DISPATCHIS INTERCONNECTORRES | five minutes | AEMO source-sign flow MW |
| Next_Day_Dispatch UNIT_SOLUTION | T+1 daily | authoritative target, availability, ramp and AGC fields |
| MMSDM DUDETAILSUMMARY + DUALLOC + GENUNITS | monthly | DUID region and `CO2E_ENERGY_SOURCE` fuel context |
| bids, trading and settlement | source appropriate | separately labelled analyst context |

NEM timestamps are interval-ending fixed AEST (UTC+10, no daylight saving).
Bronze retains every archive version. Silver selects the latest valid correction
by report version/RUNNO, publication time and ingestion sequence. Gold retains
intervention rows and exposes `is_effective_run`; do not sum across both runs.

## 1. Local and identity gates

Do not overwrite unrelated working-tree changes. From the repository root:

```bash
git status --short
databricks --version
databricks current-user me --profile daveok
databricks catalogs get "${NEMWEB_CATALOG:?}" --profile daveok
databricks warehouses get "${NEMWEB_WAREHOUSE_ID:?}" --profile daveok
python3 scripts/validate-miniwiki.py
uv run --extra test python -m pytest
rm -rf dist && uv build --wheel --out-dir dist
(
  cd nemweb_foundation
  uv run python scripts/validate_nemweb_snapshot.py
  rm -rf dist && uv build --wheel --out-dir dist
  python3 scripts/check_modern_pipeline_apis.py
)
git diff --check
```

The CLI must meet the loaded Databricks skill requirement (>=1.0 for Lakeflow;
this implementation was validated with 1.14.1). Stop if `daveok` is missing,
unauthenticated or identifies an unexpected workspace/user.

Before deployment, also run this side-effect-free package probe:

```bash
uv run --project nemweb_foundation python - <<'PY'
from agentic_energy.nemweb import lander
assert callable(getattr(lander, "main", None)), "NEMWEB lander CLI main is missing"
PY
```

The deployed lander Job invokes that package entry point. Both `land` and
`snapshot` are installed-wheel tested; a missing command remains a blocking
implementation defect rather than an operator workaround.

Snapshot output is deterministic and explicitly `live_evidence: false`. It is
safe for local workshop demonstrations, but it cannot close the live gate.
Snapshot and live landings use sibling roots under the managed Volume:
`<landing_path>/snapshot/` and `<landing_path>/live/`. Configure `landing_path`
as the unscoped Volume root; supplying either sibling itself is rejected rather
than silently creating `live/live` or `snapshot/snapshot`. Each sibling retains its
own permanent `.nemweb-source-mode` marker, so the modes can coexist without
allowing either one to write into the other. A legacy marker or raw/parsed data
at the Volume parent is ignored: the new code does not delete or migrate it.
Operators may retain that legacy layout for audit, but new runs and the pipeline
read only the selected mode sibling.

## 2. Target configuration and strict validation

Use a dedicated development schema. Never commit these values. Run all bundle
commands below from the authoritative solution project:

```bash
cd nemweb_foundation
export BUNDLE_VAR_catalog="${NEMWEB_CATALOG:?set target catalog}"
export BUNDLE_VAR_schema="${NEMWEB_DEV_SCHEMA:?set isolated dev schema}"
export BUNDLE_VAR_landing_volume="${NEMWEB_LANDING_VOLUME:?set Volume name}"
export BUNDLE_VAR_warehouse_id="${NEMWEB_WAREHOUSE_ID:?set SQL warehouse id}"
export BUNDLE_VAR_participant_group="${PARTICIPANT_GROUP:?set group}"
export BUNDLE_VAR_facilitator_group="${FACILITATOR_GROUP:?set group}"
export BUNDLE_VAR_nemweb_mode=snapshot
export BUNDLE_VAR_allow_live_nemweb=false

databricks bundle validate --strict -t dev --profile daveok
databricks bundle summary -t dev --profile daveok
```

Review the summary. Resource names should be developer-namespaced, and the
schema and Volume names must themselves include the operator identity because
bundle development mode does not isolate UC data-plane paths. Both periodic
Jobs must be paused. The lander, pipeline, semantic job, dashboard and Genie
assets should be present. Stop if any pipeline source is missing or commented
out.

Validate the production target separately because its `run_as`, workspace root
and runtime-principal Volume grant are target-specific:

```bash
export BUNDLE_VAR_runtime_service_principal="${NEMWEB_RUNTIME_SP:?}"
databricks bundle validate --strict -t workshop --profile daveok
```

Schema-level `USE CATALOG`, `USE SCHEMA` and Gold/metric-view `SELECT` grants are
managed by the platform owner because the bundle consumes an existing schema.
Before workshop use, verify those grants for the participant group with `SHOW
GRANTS`; do not rely on ambient catalog access. The workshop Volume grant is
bundle-declared for the runtime service principal as well as facilitators.

## 3. Controlled deployment and initial publication

Deployment is an external mutation and requires the executing user's explicit
authorisation. No worker or CI validation step should deploy implicitly.

```bash
databricks bundle deploy -t dev --profile daveok
databricks bundle summary -t dev --profile daveok
```

Keep schedules paused. Run one critical DAG manually:

```bash
databricks bundle run nemweb_refresh -t dev --profile daveok
```

Do not use `--refresh-all`, request a full refresh, drop a table or delete the
schema. A pipeline task must have `full_refresh: false`.

### Exact pipeline update polling

Record the orchestration run ID, child lander result, pipeline ID and **exact
update ID** before interpreting the run. Use:

```bash
databricks jobs get-run "$NEMWEB_JOB_RUN_ID" --profile daveok -o json
databricks pipelines get-update "$NEMWEB_PIPELINE_ID" "$NEMWEB_UPDATE_ID" \
  --profile daveok -o json
databricks pipelines list-pipeline-events "$NEMWEB_PIPELINE_ID" \
  --filter "update_id = '$NEMWEB_UPDATE_ID'" --max-results 250 \
  --profile daveok -o json
```

Poll `get-update` until `COMPLETED`, `FAILED` or `CANCELED`. If the task metadata
does not expose an update ID, use the pipeline task start/end timestamps to list
candidate updates and continue only when exactly one candidate matches; never
select “latest” without that proof. On failure, extract the nested
`error.exceptions[0].message` from the filtered events. A top-level pipeline
state or CLI exit status is not the underlying error.

## 4. Data and analyst gates

After a `COMPLETED` update, query all critical tables. Confirm landed/Bronze
reconciliation, correction ordering, Gold natural-key uniqueness, effective-run
uniqueness and data watermarks. Then execute semantic SQL and every benchmark
and dashboard statement:

```bash
databricks bundle run nemweb_semantics -t dev --profile daveok
uv run python scripts/validate_nemweb_genie.py --execute \
  --profile daveok --warehouse-id "$BUNDLE_VAR_warehouse_id" \
  --catalog "$BUNDLE_VAR_catalog" --schema "$BUNDLE_VAR_schema" \
  --output /tmp/nemweb-analyst-sql-results.json
```

Do not create/update or publish dashboard/Genie assets until all statements have
terminal state `SUCCEEDED`. After deployment, retrieve both resources and
confirm the dashboard resolves the deployed Genie ID and renders without a SQL
error. Metric measures must reconcile to Gold sources.

The T+1 table is validated separately. Its source lag is daily and must never be
reported as five-minute availability. Reconcile overlapping
`actual_generation_mw` and `total_cleared_mw` intervals without asserting they
must be equal.

## 5. Three-cycle live proof

Only after Sections 1–4 pass may an authorised operator deploy live mode.
Do not repoint the snapshot development pipeline: its Auto Loader checkpoints
retain the snapshot file-system path. Use the separate `live_evidence` target,
schema, resource prefix, tables, event log, and checkpoints. The target shares
only the existing run-owned landing Volume and selects its immutable `live/`
sibling. Participants cannot override the lander Job parameters because they
have `CAN_VIEW` only:

```bash
export BUNDLE_VAR_resource_prefix="${NEMWEB_LIVE_RESOURCE_PREFIX:?set isolated live prefix}"
export BUNDLE_VAR_landing_schema="${NEMWEB_DEV_SCHEMA:?set snapshot schema containing the Volume}"
export BUNDLE_VAR_schema="${NEMWEB_LIVE_SCHEMA:?set isolated live schema}"
export BUNDLE_VAR_nemweb_mode=live
export BUNDLE_VAR_allow_live_nemweb=true
databricks bundle validate --strict -t live_evidence --profile daveok
databricks bundle summary -t live_evidence --profile daveok
databricks bundle deploy -t live_evidence --profile daveok \
  --select jobs.nemweb_lander,jobs.nemweb_context_refresh,jobs.nemweb_refresh,pipelines.nemweb_pipeline
```

The selective live deployment deliberately excludes the existing managed
Volume. Confirm in the summary that both `resources.volumes.nemweb_landing` and
`landing_path` resolve to `catalog.landing_schema.landing_volume`, and verify the
live runtime identity already has `READ_VOLUME` and `WRITE_VOLUME` there from
the development deployment. Do not run an unselected full deployment of the
`live_evidence` target or create a second Volume.

Run the full live context DAG once to materialise registration dependencies,
then keep its schedule paused. Unpause only the isolated five-minute live job.
Observe three consecutive scheduled cycles, capture each one, and pause it
again. Do not deploy snapshot values to the live target because that would
cross its checkpoint paths. The ordinary `dev` target stays at its
snapshot/false defaults throughout. Do not manufacture source rows when AEMO
publishes nothing new.

For the first cycle:

```bash
uv run python scripts/capture_nemweb_evidence.py \
  --profile daveok --warehouse-id "$BUNDLE_VAR_warehouse_id" \
  --catalog "$BUNDLE_VAR_catalog" --schema "$BUNDLE_VAR_schema" \
  --pipeline-id "$NEMWEB_PIPELINE_ID" \
  --pipeline-update-id "$NEMWEB_UPDATE_ID" \
  --orchestration-run-id "$NEMWEB_JOB_RUN_ID" \
  --output-json /tmp/nemweb-evidence.json \
  --output-markdown /tmp/nemweb-evidence.md
```

Use the same command with new run/update IDs and `--append` for cycles two and
three. The capture tool:

- polls the explicitly supplied update to terminal state;
- filters events to that update and extracts nested exceptions on failure;
- checks current NEMWEB listings and records their publication timestamps;
- queries latest interval, cumulative counts and watermarks in each medallion layer;
- calculates a bounded order-independent Gold business-column fingerprint so a
  same-interval correction is observable, then checks Gold natural-key duplicates;
- requires emitted Lakeflow expectation metrics with zero failures;
- requires source-to-Gold, Bronze-to-Gold, and landed-to-Gold lags to be present
  and equal to the captured timestamps (within the timestamps' 1 ms precision);
- permits a signed source-to-Gold value only for an explicitly recorded
  `PASS_SOURCE_WITHIN_LEAD` listing race of at most two dispatch intervals,
  while Bronze-to-Gold and landed-to-Gold processing lags remain non-negative;
- separates source-publication lag from those processing lags; and
- permits `PASS_NO_NEW_SOURCE` only when the source signature is unchanged.

The source publication timestamp comes from the public listing entry for the
exact filename. Dispatch reports can be posted shortly before their labelled
interval end, so publication-minus-source-interval lag may legitimately be a
small negative signed value; do not clamp it. Evidence capture occurs after a
cycle and its listing may already be one or two intervals ahead of the Bronze
watermark processed by that cycle. `PASS_SOURCE_WITHIN_LEAD` reports this race
rather than claiming the later file was processed; the Bronze-to-Gold lag is
the processing-cadence measure for the represented interval.

Validate the complete pack:

```bash
uv run python scripts/validate_nemweb_live.py /tmp/nemweb-evidence.json
```

The validator requires exactly one row for all five subjects in every cycle,
one update ID per cycle and a distinct update ID across cycles, successful
lander/pipeline/orchestration outcomes,
non-empty Gold output with a publication timestamp, zero key/expectation
failures and consecutive cycle starts approximately five minutes apart. Dense
Gold subjects must match their Bronze interval watermark. The
binding-constraint Gold table can remain at an older watermark when a new
DISPATCHIS interval contains no binding row; its evidence count and fingerprint
then describe the newest actually published binding interval at or before the
Bronze cycle. It must still be non-empty and may never claim a watermark ahead
of Bronze. Bronze and source watermarks prove the new interval was inspected.

Copy the reviewed Markdown table and exact command results to
`docs/test-evidence/nemweb-e2e-YYYY-MM-DD.md`. Include Git state, source
versions, resource names, snapshot/SQL reconciliations, failures/fixes and T+1
limitations. Exclude tokens, workspace URLs, tenant identifiers and private
operator details.

## No-change semantics

A row is a genuine no-new-source cycle only when:

1. the latest listing filename, publication timestamp, source interval and raw
   checksum signature are unchanged from the preceding capture;
2. the listing interval is not ahead of the Bronze watermark;
3. the exact pipeline update completed; and
4. quality and duplicate checks passed.

A changed DISPATCHIS archive with no new binding Gold row is not labelled “no
new source”; it is a source-changed/no-Gold-change observation. No fixture or
synthetic row may enter a live landing root/schema.

## Troubleshooting

| Symptom | Safe action |
|---|---|
| NEMWEB listing or download timeout | Inspect durable lander failure manifest; retain finite retries; do not switch host or disable TLS/redirect controls. |
| ZIP expansion/section error | Preserve raw checksum and failure; review source size/schema; do not globally weaken limits. |
| Listing more than two intervals ahead of Bronze, or ahead with failed quality/key checks | Inspect the lander manifest and Auto Loader events for the exact update. Do not call the cycle fresh. |
| Pipeline `FAILED` with generic message | Query events for the exact update and read `error.exceptions[0].message`. |
| Unknown DUID/fuel | Retain the row with `UNKNOWN`; refresh monthly MMSDM dimension. RT_/DG_ pseudo-units are expected. |
| Duplicate Gold natural key | Stop analyst publication; inspect correction ordering/intervention key. Do not delete Bronze history. |
| Missing expectation metrics | Treat as failed evidence even when tables have rows. |
| SQL/dashboard failure | Fix and rerun SQL before any dashboard/Genie update. |
| T+1 table not fresh intraday | Report daily source publication lag; never substitute/fabricate Current availability. |

## Rollback

1. Pause the five-minute job.
2. Preserve immutable raw ZIPs and manifests.
3. Redeploy the last known-good revision with identical variables.
4. Prefer a selective rerun after fixing code; never use full refresh as routine rollback.
5. Never change a table from streaming to materialised in place.
6. Do not use `bundle destroy` as routine rollback.
7. Schema/Volume deletion requires explicit approval after retention review.
8. Restore prior serialised dashboard/Genie definitions using their stable IDs.
