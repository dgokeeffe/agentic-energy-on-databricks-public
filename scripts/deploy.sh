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

: "${DATABRICKS_HOST:?Set DATABRICKS_HOST to the selected workspace URL}"
: "${DATABRICKS_BUNDLE_VAR_catalog:?Set DATABRICKS_BUNDLE_VAR_catalog}"
: "${DATABRICKS_BUNDLE_VAR_schema:?Set DATABRICKS_BUNDLE_VAR_schema}"
: "${DATABRICKS_BUNDLE_VAR_landing_volume:?Set DATABRICKS_BUNDLE_VAR_landing_volume}"
: "${DATABRICKS_BUNDLE_VAR_runtime_service_principal:?Set DATABRICKS_BUNDLE_VAR_runtime_service_principal}"
: "${DATABRICKS_BUNDLE_VAR_participant_group:?Set DATABRICKS_BUNDLE_VAR_participant_group}"
: "${DATABRICKS_BUNDLE_VAR_facilitator_group:?Set DATABRICKS_BUNDLE_VAR_facilitator_group}"

# The bundle declares engine: direct. Keep validation and deployment together so
# participants do not need to understand Terraform state or workspace uploads.
databricks bundle validate --strict -t "$TARGET"
databricks bundle deploy -t "$TARGET"
