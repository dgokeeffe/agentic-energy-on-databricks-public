#!/usr/bin/env bash
set -euo pipefail
: "${PROFILE:?Set PROFILE=daveok explicitly}"
if [[ "$PROFILE" != "daveok" ]]; then
  echo "PROFILE=daveok is required" >&2
  exit 2
fi

databricks auth describe --profile "$PROFILE"
databricks postgres -h
databricks postgres create-synced-table -h
databricks postgres create-cdf-config -h
databricks apps manifest --profile "$PROFILE"

echo "Read-only discovery complete. No resources were created or changed."
