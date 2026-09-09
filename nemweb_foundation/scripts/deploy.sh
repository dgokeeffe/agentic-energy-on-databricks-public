#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

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
#
# Validation is deliberately NOT --strict.
#
# --strict promotes every warning to an error, and CLI v1.7.0 emits a warning
# that is provably wrong: `invalid value "MINUTES" for enum field. Valid values
# are [DAYS HOURS WEEKS]` for nemweb_refresh's trigger.periodic.unit. MINUTES is
# a valid value. The Python SDK on the same machine defines it
# (databricks/sdk/service/jobs.py, PeriodicTriggerConfigurationTimeUnit: DAYS,
# HOURS, MINUTES, WEEKS), the REST API reference lists it for
# PeriodicTriggerConfiguration.unit, and the deployed job reads back
# {"interval": 5, "unit": "MINUTES"} verbatim from /api/2.2/jobs/get. The CLI's
# own bundle schema is the stale artefact: it carries only [HOURS DAYS WEEKS] and
# the string MINUTES appears nowhere in `databricks bundle schema`.
#
# The five-minute cadence is load-bearing and evidenced in
# resources/nemweb_refresh.job.yml, so the correct response is to stop failing on
# a known-false warning rather than to widen the interval to satisfy the tooling.
# Real validation errors still fail this script and block the deploy.
#
# Revisit when the CLI schema catches up: restore --strict and delete this note.
PROFILE="${PROFILE:-DEFAULT}"

databricks bundle validate -t "$TARGET" --profile "$PROFILE"
databricks bundle deploy -t "$TARGET" --profile "$PROFILE"
