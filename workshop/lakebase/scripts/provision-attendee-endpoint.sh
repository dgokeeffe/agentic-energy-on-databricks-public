#!/usr/bin/env bash
# Create or configure the read-write endpoint for one attendee branch.
#
# The facilitator creates the branch and grants the approved participant group
# temporary CAN_MANAGE on the Lakebase project. This script deliberately does
# not create, replace, reset, or delete branches. It only ensures the named
# attendee branch has its primary endpoint with scale-to-zero enabled.
#
# Usage:
#   PROFILE=DEFAULT PROJECT_ID=<project> ATTENDEE_SLUG=<slug> \
#     bash workshop/lakebase/scripts/provision-attendee-endpoint.sh
#
#   DRY_RUN=1 ... to print the planned commands without creating anything.
set -euo pipefail

# An explicit profile is required so no command can run against an implicit
# default workspace. Which profile is the operator's choice: pinning one name
# here would hardcode a personal workspace into a public repository.
: "${PROFILE:?Set PROFILE to your Databricks CLI profile name, e.g. PROFILE=DEFAULT}"

: "${PROJECT_ID:?Set PROJECT_ID to the Lakebase project ID, without the projects/ prefix}"
: "${ATTENDEE_SLUG:?Set ATTENDEE_SLUG to your assigned attendee slug}"

DRY_RUN="${DRY_RUN:-0}"
ENDPOINT_ID="${ENDPOINT_ID:-primary}"
# Keep workshop branches cheap while allowing an app to wake the compute on demand.
# Databricks accepts suspension timeouts from 60 seconds through 7 days.
SUSPEND_TIMEOUT="300s"

SLUG_RE='^[a-z][a-z0-9-]{0,25}$'
if [[ ! "$ATTENDEE_SLUG" =~ $SLUG_RE ]]; then
  echo "Invalid attendee slug: '$ATTENDEE_SLUG'" >&2
  echo "Use your assigned lowercase slug, starting with a letter, 26 characters or fewer." >&2
  exit 2
fi

BRANCH_ID="dev-${ATTENDEE_SLUG}"
BRANCH_PATH="projects/$PROJECT_ID/branches/$BRANCH_ID"
ENDPOINT_PATH="$BRANCH_PATH/endpoints/$ENDPOINT_ID"

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRY RUN: %s\n' "$*"
  else
    "$@"
  fi
}

echo "Profile:        $PROFILE"
echo "Project:        projects/$PROJECT_ID"
echo "Branch:         $BRANCH_PATH"
echo "Endpoint:       $ENDPOINT_PATH"
echo "Scale-to-zero:  $SUSPEND_TIMEOUT"
echo "Dry run:        $DRY_RUN"
echo

# Resolve the branch first so a typo cannot create an endpoint on another path.
if [[ "$DRY_RUN" != "1" ]]; then
  databricks postgres get-branch "$BRANCH_PATH" --profile "$PROFILE" >/dev/null
fi

if [[ "$DRY_RUN" == "1" ]]; then
  printf 'DRY RUN: ensure endpoint %s with scale-to-zero=%s\n' \
    "$ENDPOINT_PATH" "$SUSPEND_TIMEOUT"
elif databricks postgres get-endpoint "$ENDPOINT_PATH" \
    --profile "$PROFILE" >/dev/null 2>&1; then
  echo "Endpoint $ENDPOINT_ID already present; applying scale-to-zero."
  run databricks postgres update-endpoint "$ENDPOINT_PATH" spec.suspension \
    --json "{\"spec\": {\"suspend_timeout_duration\": \"$SUSPEND_TIMEOUT\"}}" \
    --profile "$PROFILE"
else
  run databricks postgres create-endpoint "$BRANCH_PATH" "$ENDPOINT_ID" \
    --json "{\"spec\": {\"type\": \"ENDPOINT_TYPE_READ_WRITE\", \"suspend_timeout_duration\": \"$SUSPEND_TIMEOUT\"}}" \
    --profile "$PROFILE"
fi

echo
echo "Endpoint ready for $BRANCH_ID. Deploy the app only with the same attendee slug."
