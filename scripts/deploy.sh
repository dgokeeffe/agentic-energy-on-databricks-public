#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-dev}"

case "$TARGET" in
  dev|workshop) ;;
  *)
    echo "usage: $0 {dev|workshop}" >&2
    exit 2
    ;;
esac

# The bundle cannot interpolate auth fields, so the workspace comes from the
# environment. Prefer an explicit DATABRICKS_HOST, but fall back to whatever the
# already-authenticated CLI resolves: inside a CoDA container (Databricks App
# terminal / Omnigent runner) auth is brokered per-invocation and DATABRICKS_HOST
# is deliberately NOT exported, so demanding it turned a working deploy into a
# fake "no credentials" dead end. `auth describe` is the supported read of the
# resolved host; it works for a PAT, a profile, or the brokered token alike.
if [ -z "${DATABRICKS_HOST:-}" ]; then
  DATABRICKS_HOST=$(databricks auth describe --output json 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("details",{}).get("host",""))' \
    2>/dev/null) || DATABRICKS_HOST=""
  export DATABRICKS_HOST
  [ -n "$DATABRICKS_HOST" ] && echo "==> Resolved DATABRICKS_HOST from the authenticated CLI: $DATABRICKS_HOST"
fi
: "${DATABRICKS_HOST:?Set DATABRICKS_HOST to the selected workspace URL (or authenticate the databricks CLI first)}"
# The Databricks CLI resolves bundle variables from BUNDLE_VAR_<name>, not
# DATABRICKS_BUNDLE_VAR_<name>. Using the wrong prefix makes every variable
# read as unassigned and fails validation before the workspace is contacted.
: "${BUNDLE_VAR_catalog:?Set BUNDLE_VAR_catalog}"
: "${BUNDLE_VAR_schema:?Set BUNDLE_VAR_schema}"
: "${BUNDLE_VAR_landing_volume:?Set BUNDLE_VAR_landing_volume}"
: "${BUNDLE_VAR_participant_group:?Set BUNDLE_VAR_participant_group}"
: "${BUNDLE_VAR_facilitator_group:?Set BUNDLE_VAR_facilitator_group}"

# Only the shared workshop target pins run_as to the ETL service principal. dev
# runs as the deploying identity so any number of developers can deploy their
# own copy without holding the servicePrincipal.user role on a shared SP.
if [ "$TARGET" = "workshop" ]; then
  : "${BUNDLE_VAR_runtime_service_principal:?Set BUNDLE_VAR_runtime_service_principal for the workshop target}"
fi

# The bundle declares engine: direct. Keep validation and deployment together so
# participants do not need to understand Terraform state or workspace uploads.
databricks bundle validate --strict -t "$TARGET"
databricks bundle deploy -t "$TARGET"
