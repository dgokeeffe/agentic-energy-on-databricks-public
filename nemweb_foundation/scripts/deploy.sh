#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
TARGET="${1:-dev}"
PROFILE="${PROFILE:-${2:-}}"
case "$TARGET" in dev|workshop|live_evidence) ;; *) echo "usage: $0 {dev|workshop|live_evidence}" >&2; exit 2;; esac
: "${PROFILE:?Set PROFILE=<cli-profile>}"

# Choose a target. No .env. The workshop service principal is a --var because
# it is a workspace identity the bundle cannot invent.
extra=()
if [ "$TARGET" = "workshop" ]; then
  : "${RUNTIME_SERVICE_PRINCIPAL:?Set RUNTIME_SERVICE_PRINCIPAL=<application-id>}"
  extra+=(--var "runtime_service_principal=${RUNTIME_SERVICE_PRINCIPAL}")
fi

databricks bundle validate --strict -t "$TARGET" --profile "$PROFILE" "${extra[@]}"
databricks bundle deploy -t "$TARGET" --profile "$PROFILE" "${extra[@]}"
