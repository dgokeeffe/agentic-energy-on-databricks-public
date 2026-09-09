#!/usr/bin/env bash
# End-to-end deployment of the NEMWEB foundation, the Lakebase attendee branch,
# and the per-attendee Databricks App.
#
# MUTATES THE WORKSPACE. Requires explicit human authorisation in the current
# task. It deploys bundles, runs jobs, and creates a Lakebase branch. It never
# unpauses a schedule, enables live NEMWEB, drops a schema, deletes a branch, or
# touches Git.
#
# Idempotent: every stage is safe to re-run. Bundle deploys converge, schema
# creation uses IF NOT EXISTS, branch creation is skipped when the branch exists,
# and the cold-start jobs are skipped once their output tables are present.
#
# Usage:
#   bash scripts/deploy-workshop.sh              # full sequence
#   bash scripts/deploy-workshop.sh --dry-run    # print the plan, change nothing
#   STAGES=app bash scripts/deploy-workshop.sh   # one stage only
#
# Stages: schemas foundation coldstart serving lakebase app verify
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

STAGES="${STAGES:-schemas foundation coldstart serving lakebase app verify}"

# Profile is configurable because a workspace need not have a profile named
# daveok; a sandbox commonly has only DEFAULT. Every workspace-aware command
# below passes it explicitly, so no implicit profile is ever used.
PROFILE="${PROFILE:-DEFAULT}"

log()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
info() { printf '   %s\n' "$*"; }
run()  { if (( DRY_RUN )); then printf '   DRY RUN: %s\n' "$*"; else "$@"; fi; }

: "${DATABRICKS_CONFIG_FILE:=}"

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy env.example to .env and set every BUNDLE_VAR_ value." >&2
  exit 2
fi
set -a; . ./.env; set +a

for v in catalog schema app_serving_schema landing_volume warehouse_id \
         participant_group facilitator_group attendee_slug lakebase_project_id \
         sql_warehouse_id; do
  eval "val=\${BUNDLE_VAR_$v:-}"
  [[ -n "$val" ]] || { echo "Missing BUNDLE_VAR_$v in .env (required, no default)" >&2; exit 2; }
done

CATALOG="$BUNDLE_VAR_catalog"
SCHEMA="$BUNDLE_VAR_schema"
SERVING_SCHEMA="$BUNDLE_VAR_app_serving_schema"
WAREHOUSE="$BUNDLE_VAR_warehouse_id"
SLUG="$BUNDLE_VAR_attendee_slug"
PROJECT="$BUNDLE_VAR_lakebase_project_id"
BRANCH="dev-${SLUG}"
APP_NAME="${BUNDLE_VAR_app_name_prefix:-aew}-${SLUG}"

has_stage() { [[ " $STAGES " == *" $1 "* ]]; }

# --- helpers ---------------------------------------------------------------

sql() {
  # Run one statement on the warehouse and print the first returned value, or
  # "ok" for a statement with no result set. Fails closed: a non-SUCCEEDED state
  # is an error, not a warning.
  local statement="$1"
  local payload
  payload=$(STMT="$statement" WH="$WAREHOUSE" python3 -c '
import json, os
print(json.dumps({"warehouse_id": os.environ["WH"],
                  "statement": os.environ["STMT"],
                  "wait_timeout": "50s"}))')
  if (( DRY_RUN )); then printf '   DRY RUN: sql: %s\n' "${statement:0:110}"; return 0; fi
  databricks api post /api/2.0/sql/statements --profile "$PROFILE" --json "$payload" \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
st = d.get("status", {})
state = st.get("state")
if state != "SUCCEEDED":
    msg = (st.get("error") or {}).get("message", "")
    print(f"   FAILED: {state}: {msg[:400]}")
    raise SystemExit(1)
rows = ((d.get("result") or {}).get("data_array") or [])
print(f"   {rows[0][0]}" if rows and rows[0] else "   ok")
'
}

table_exists() {
  # Cheap existence probe that does not need a running warehouse.
  databricks tables get "$1" --profile "$PROFILE" >/dev/null 2>&1
}

job_id() {
  # Resolve a bundle job's numeric ID by its logical resource name, so no ID is
  # hardcoded and a redeploy into a fresh workspace still works.
  # stderr is dropped only for this read-only summary: CLI v1.7.0 emits a stale
  # enum warning for the deliberate MINUTES trigger unit on every invocation, and
  # a failure here still surfaces as empty JSON below.
  (cd nemweb_foundation && databricks bundle summary -t dev --profile "$PROFILE" -o json 2>/dev/null) \
    | KEY="$1" python3 -c '
import json, os, sys
key = os.environ["KEY"]
jobs = (json.load(sys.stdin).get("resources") or {}).get("jobs") or {}
job = jobs.get(key) or {}
print(job.get("id") or "")
'
}

run_job_and_wait() {
  # Start a job without blocking, then poll. The blocking form of run-now can
  # outlast a long pipeline update, which is why --no-wait plus polling is used.
  local label="$1" key="$2" id run_id state
  id="$(job_id "$key")"
  [[ -n "$id" ]] || { echo "   could not resolve job id for $key" >&2; return 1; }
  info "$label (job $id)"
  if (( DRY_RUN )); then printf '   DRY RUN: run-now %s\n' "$id"; return 0; fi

  run_id=$(databricks jobs run-now "$id" --no-wait --profile "$PROFILE" -o json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
  info "run_id $run_id"

  while :; do
    state=$(databricks jobs get-run "$run_id" --profile "$PROFILE" -o json \
      | python3 -c '
import json, sys
d = json.load(sys.stdin)
s = d.get("status", {})
td = s.get("termination_details") or {}
print(s.get("state", ""), td.get("code", ""))
')
    case "$state" in
      TERMINATED*SUCCESS*) info "SUCCESS"; return 0 ;;
      TERMINATED*|SKIPPED*|INTERNAL_ERROR*)
        echo "   job $key finished $state" >&2
        databricks jobs get-run "$run_id" --profile "$PROFILE" -o json \
          | python3 -c '
import json, sys
for t in json.load(sys.stdin).get("tasks", []):
    ts = t.get("status") or {}
    td = ts.get("termination_details") or {}
    print("     ", t["task_key"], "->", ts.get("state"), td.get("code"),
          (td.get("message") or "")[:200])
' >&2
        return 1 ;;
    esac
    sleep 25
  done
}

# --- preflight -------------------------------------------------------------

log "Preflight"
info "profile:  $PROFILE"
info "catalog:  $CATALOG"
info "schemas:  $SCHEMA, $SERVING_SCHEMA"
info "app:      $APP_NAME"
info "lakebase: projects/$PROJECT/branches/$BRANCH"
info "stages:   $STAGES"
(( DRY_RUN )) && info "DRY RUN: nothing will be created or changed"

databricks auth describe --profile "$PROFILE" >/dev/null \
  || { echo "Profile '$PROFILE' is absent or unauthenticated." >&2; exit 2; }

# The catalog must already exist. A workspace with account-level Default Storage
# refuses catalog creation through the API and the SQL path alike, including with
# an explicit MANAGED LOCATION: "Please use the UI to create a catalog with
# Default Storage." Creating it is therefore a human, UI-only prerequisite.
databricks catalogs get "$CATALOG" --profile "$PROFILE" >/dev/null 2>&1 || {
  echo "Catalog '$CATALOG' does not exist." >&2
  echo "Create it in the Databricks UI first: a workspace with Default Storage" >&2
  echo "cannot create a catalog through the API or SQL." >&2
  exit 2
}
info "catalog resolved"

# The warehouse must be running for the schema and verification statements.
if ! (( DRY_RUN )); then
  state=$(databricks warehouses get "$WAREHOUSE" --profile "$PROFILE" -o json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("state",""))')
  if [[ "$state" != "RUNNING" ]]; then
    info "starting warehouse $WAREHOUSE (was $state)"
    databricks warehouses start "$WAREHOUSE" --profile "$PROFILE" --timeout 15m >/dev/null
  fi
  info "warehouse RUNNING"
fi

# --- stages ----------------------------------------------------------------

if has_stage schemas; then
  log "Schemas"
  for s in "$SCHEMA" "$SERVING_SCHEMA"; do
    info "$CATALOG.$s"
    sql "CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${s} COMMENT 'Agentic energy NEMWEB workshop'"
  done
fi

if has_stage foundation; then
  log "Foundation bundle"
  # scripts/deploy.sh is deliberately not used: it hardcodes --strict, and CLI
  # v1.7.0 emits a stale-enum warning for the deliberate five-minute
  # trigger.periodic.unit: MINUTES. The Jobs API accepts MINUTES and stores it
  # verbatim, so the YAML is correct and the warning is a tooling artefact.
  # Validating non-strict keeps the documented cadence intact instead of
  # weakening a real check to obtain a pass.
  run bash -c "cd nemweb_foundation && databricks bundle validate -t dev --profile '$PROFILE'"

  # On a cold schema the first deploy PARTLY FAILS by design: the Genie space and
  # dashboard cannot be created until the Gold tables and metric views exist.
  # Jobs, pipelines and the Volume are created in that same run, so the failure
  # is tolerated here and the deploy is repeated after the cold-start stage.
  if (( DRY_RUN )); then
    info "DRY RUN: bundle deploy -t dev (Genie/dashboard may fail on a cold schema)"
  elif (cd nemweb_foundation && databricks bundle deploy -t dev --profile "$PROFILE"); then
    info "deployed"
  else
    info "partial deploy (expected on a cold schema: Genie/dashboard need Gold tables)"
  fi
fi

if has_stage coldstart; then
  log "Cold start"
  # Strict order. The context job lands monthly MMSDM registration and
  # materialises bronze_nem_dudetail; the critical job's
  # silver_nem_facility_dimension depends on it and fails with
  # SOURCE_TABLE_NOT_MATERIALIZED if run first. This is source cadence
  # (registration is monthly, dispatch is five-minute), not a defect.
  if table_exists "${CATALOG}.${SCHEMA}.bronze_nem_dudetail"; then
    info "context already landed (bronze_nem_dudetail present); skipping"
  else
    run_job_and_wait "context job" nemweb_context_refresh
  fi

  if table_exists "${CATALOG}.${SCHEMA}.gold_nem_region_dispatch_5min"; then
    info "medallion already published (gold_nem_region_dispatch_5min present); skipping"
  else
    run_job_and_wait "critical refresh job" nemweb_refresh
  fi

  if table_exists "${CATALOG}.${SCHEMA}.nem_region_dispatch_metrics"; then
    info "metric views already present; skipping"
  else
    run_job_and_wait "semantics job" nemweb_semantics
  fi

  log "Foundation redeploy (Genie space and dashboard)"
  # Now that Gold tables and metric views exist, the resources that failed on the
  # cold deploy can be created.
  run bash -c "cd nemweb_foundation && databricks bundle deploy -t dev --profile '$PROFILE'"
fi

if has_stage serving; then
  log "App serving tables"
  # Publishes gold_nem_app_region_status and gold_nem_scada_generation_5min into
  # the serving schema. Both back the app's two uc_securable SELECT grants;
  # without them integration mode reports the reads as unavailable.
  run_job_and_wait "app-serving job" nemweb_app_serving
fi

if has_stage lakebase; then
  log "Lakebase branch"
  if (( DRY_RUN )); then
    info "DRY RUN: ensure projects/$PROJECT/branches/$BRANCH and its primary endpoint"
  elif databricks postgres get-branch "projects/$PROJECT/branches/$BRANCH" \
        --profile "$PROFILE" >/dev/null 2>&1; then
    info "branch $BRANCH already exists; leaving it untouched"
  else
    # Cloned from the project's default branch. --replace-existing is deliberately
    # NOT passed: replacing a branch would discard an attendee's investigations.
    parent=$(databricks postgres list-branches "projects/$PROJECT" --profile "$PROFILE" -o json \
      | python3 -c '
import json, sys
bs = json.load(sys.stdin)
default = next((b for b in bs if (b.get("status") or {}).get("default")), None)
print((default or bs[0])["branch_id"] if bs else "")
')
    [[ -n "$parent" ]] || { echo "   no parent branch found in projects/$PROJECT" >&2; exit 1; }
    info "creating $BRANCH from $parent"
    databricks postgres create-branch "projects/$PROJECT" "$BRANCH" \
      --json "{\"spec\": {\"source_branch\": \"projects/$PROJECT/branches/$parent\", \"no_expiry\": true}}" \
      --profile "$PROFILE" >/dev/null
    info "branch created"
  fi

  # A cloned branch inherits a primary read-write endpoint. Apply scale-to-zero
  # so an idle attendee branch does not hold compute: the binding limit is 20
  # concurrently active computes per project, not the 500 branches per project.
  if ! (( DRY_RUN )); then
    ep="projects/$PROJECT/branches/$BRANCH/endpoints/primary"
    if databricks postgres get-endpoint "$ep" --profile "$PROFILE" >/dev/null 2>&1; then
      databricks postgres update-endpoint "$ep" spec.suspension \
        --json '{"spec": {"suspend_timeout_duration": "300s"}}' \
        --profile "$PROFILE" >/dev/null
      info "primary endpoint scale-to-zero 300s"
    else
      databricks postgres create-endpoint "projects/$PROJECT/branches/$BRANCH" primary \
        --json '{"spec": {"type": "ENDPOINT_TYPE_READ_WRITE", "suspend_timeout_duration": "300s"}}' \
        --profile "$PROFILE" >/dev/null
      info "primary endpoint created with scale-to-zero 300s"
    fi
  fi
fi

if has_stage app; then
  log "App build and deploy"
  # Deploy BEFORE running the app locally. The app's service principal must be
  # the identity that first creates app_write on the branch, or the schema ends
  # up owned by a human identity and the deployed app fails with permission
  # denied (42501).
  run bash -c "cd nemweb_app && npm ci --include=dev"
  run bash -c "cd nemweb_app && npm run typecheck"
  run bash -c "cd nemweb_app && npm run test -- --run"
  run bash -c "cd nemweb_app && npm run build"
  run bash -c "cd nemweb_app && databricks bundle validate --strict -t dev --profile '$PROFILE'"
  run bash -c "cd nemweb_app && databricks bundle deploy -t dev --profile '$PROFILE'"
fi

if has_stage verify; then
  log "Verify"
  if (( DRY_RUN )); then
    info "DRY RUN: verify serving rows, app state, and paused schedules"
  else
    for t in gold_nem_app_region_status gold_nem_scada_generation_5min; do
      info "rows in $t:"
      sql "SELECT COUNT(*) FROM ${CATALOG}.${SERVING_SCHEMA}.${t}"
    done

    databricks apps get "$APP_NAME" --profile "$PROFILE" -o json | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("   app:    ", d.get("name"))
print("   url:    ", d.get("url"))
print("   status: ", (d.get("app_status") or {}).get("state"),
      "/ compute", (d.get("compute_status") or {}).get("state"))
'

    # Fail loudly if any schedule came unpaused. Cadence must stay off until the
    # snapshot, bundle, pipeline, SQL, Genie and dashboard gates have passed.
    info "schedule pause states:"
    (cd nemweb_foundation && databricks bundle summary -t dev --profile "$PROFILE" -o json 2>/dev/null) \
      | python3 -c '
import json, sys
jobs = (json.load(sys.stdin).get("resources") or {}).get("jobs") or {}
bad = []
for name, j in jobs.items():
    for kind in ("schedule", "trigger"):
        block = j.get(kind)
        if isinstance(block, dict) and "pause_status" in block:
            status = block["pause_status"]
            print(f"     {name}.{kind}: {status}")
            if status != "PAUSED":
                bad.append(f"{name}.{kind}")
if bad:
    print("   UNPAUSED SCHEDULE(S): " + ", ".join(bad))
    raise SystemExit(1)
'
  fi
fi

log "Done"
info "Schedules stay PAUSED and live NEMWEB stays disabled; both need a separate decision."
