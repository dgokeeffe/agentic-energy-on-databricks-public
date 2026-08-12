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
: "${BUNDLE_VAR_catalog:?Set BUNDLE_VAR_catalog}"
: "${BUNDLE_VAR_schema:?Set BUNDLE_VAR_schema}"
: "${BUNDLE_VAR_landing_volume:?Set BUNDLE_VAR_landing_volume}"
: "${BUNDLE_VAR_participant_group:?Set BUNDLE_VAR_participant_group}"
: "${BUNDLE_VAR_facilitator_group:?Set BUNDLE_VAR_facilitator_group}"

if [ "$TARGET" = "workshop" ]; then
  : "${BUNDLE_VAR_runtime_service_principal:?Set BUNDLE_VAR_runtime_service_principal for the workshop target}"
fi

# The bundle declares engine: direct. Keep validation and deployment together so
# participants do not need to understand Terraform state or workspace uploads.
databricks bundle validate --strict -t "$TARGET"
databricks bundle deploy -t "$TARGET"
