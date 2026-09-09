#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
TARGET="${1:-dev}"
case "$TARGET" in dev|workshop|live_evidence) ;; *) echo "usage: $0 {dev|workshop|live_evidence}" >&2; exit 2;; esac

: "${BUNDLE_VAR_catalog:?Set BUNDLE_VAR_catalog}"
: "${BUNDLE_VAR_participant_group:?Set BUNDLE_VAR_participant_group}"
: "${BUNDLE_VAR_facilitator_group:?Set BUNDLE_VAR_facilitator_group}"
: "${BUNDLE_VAR_warehouse_id:?Set BUNDLE_VAR_warehouse_id}"
if [ "$TARGET" = live_evidence ]; then
  for suffix in resource_prefix schema landing_schema landing_volume app_serving_schema; do
    eval "live=\${BUNDLE_VAR_live_evidence_${suffix}:-}"
    eval "dev=\${BUNDLE_VAR_${suffix}:-}"
    test -n "$live" || { echo "missing BUNDLE_VAR_live_evidence_${suffix}" >&2; exit 2; }
    test "$live" != "$dev" || { echo "live_evidence ${suffix} must differ from development" >&2; exit 2; }
  done
  # Direct BUNDLE_VAR_* environment values outrank target-level variable
  # mappings. Remove development values only after comparing them above, so the
  # live_evidence target resolves exclusively through live_evidence_* inputs.
  unset BUNDLE_VAR_resource_prefix BUNDLE_VAR_schema BUNDLE_VAR_landing_schema
  unset BUNDLE_VAR_landing_volume BUNDLE_VAR_app_serving_schema
  unset BUNDLE_VAR_nemweb_mode BUNDLE_VAR_allow_live_nemweb
fi
if [ "$TARGET" = "workshop" ]; then
  : "${BUNDLE_VAR_runtime_service_principal:?Set BUNDLE_VAR_runtime_service_principal}"
fi

databricks bundle validate --strict -t "$TARGET" --profile DEFAULT
databricks bundle deploy -t "$TARGET" --profile DEFAULT
