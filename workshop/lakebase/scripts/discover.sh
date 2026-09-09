#!/usr/bin/env bash
set -euo pipefail
# An explicit profile is required so no command can run against an implicit
# default workspace. Which profile is the operator's choice: pinning one name
# here would hardcode a personal workspace into a public repository.
: "${PROFILE:?Set PROFILE to your Databricks CLI profile name, e.g. PROFILE=DEFAULT}"

databricks auth describe --profile "$PROFILE"
databricks postgres -h
databricks postgres create-synced-table -h
databricks postgres create-cdf-config -h
databricks apps manifest --profile "$PROFILE"

echo "Read-only discovery complete. No resources were created or changed."
