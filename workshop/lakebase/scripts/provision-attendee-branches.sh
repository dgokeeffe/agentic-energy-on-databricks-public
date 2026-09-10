#!/usr/bin/env bash
# Create one Lakebase branch per attendee from a seeded parent branch.
#
# Facilitator-only. Creates resources, so it requires explicit authorisation in
# the current task. Prints resource names, states, and exit codes only; never
# hosts, tokens, workspace URLs, tenant IDs, or service-principal IDs.
#
# Usage:
#   PROFILE=DEFAULT PROJECT_ID=<project> PARENT_BRANCH=<branch-id> \
#     bash workshop/lakebase/scripts/provision-attendee-branches.sh dok ajb kt
#
#   DRY_RUN=1 ... to print the planned commands without creating anything.
set -euo pipefail

# An explicit profile is required so no command can run against an implicit
# default workspace. Which profile is the operator's choice: pinning one name
# here would hardcode a personal workspace into a public repository.
: "${PROFILE:?Set PROFILE to your Databricks CLI profile name, e.g. PROFILE=DEFAULT}"

: "${PROJECT_ID:?Set PROJECT_ID to the Lakebase project ID, without the projects/ prefix}"
: "${PARENT_BRANCH:?Set PARENT_BRANCH to the seeded parent branch ID, e.g. workshop-base}"

DRY_RUN="${DRY_RUN:-0}"

if [[ $# -lt 1 ]]; then
  echo "Give at least one attendee slug. Example: ... dok ajb kt" >&2
  exit 2
fi

# Intersection of the App name rule (lowercase alphanumerics and hyphens, 2-30
# chars) and the branch ID rule (1-63 chars, start with a lowercase letter).
# Capped at 26 so "<prefix>-<slug>" stays inside the 30-character App limit.
SLUG_RE='^[a-z][a-z0-9-]{0,25}$'
for slug in "$@"; do
  if [[ ! "$slug" =~ $SLUG_RE ]]; then
    echo "Invalid attendee slug: '$slug'" >&2
    echo "Use lowercase letters, numbers, and hyphens, starting with a letter, 26 characters or fewer." >&2
    exit 2
  fi
done

# The binding limit is 20 concurrently active computes per project, not the 500
# branches per project. Each attendee branch runs its own compute.
# https://docs.databricks.com/aws/en/oltp/projects/manage-projects
if [[ $# -ge 20 ]]; then
  echo "WARNING: $# attendees requested. The documented limit is 20 concurrently" >&2
  echo "active computes per project, and the default branch is exempt. Beyond it," >&2
  echo "computes stay suspended and connections error. Request a limit increase or" >&2
  echo "shard attendees across a second project before the workshop." >&2
fi

echo "Profile:        $PROFILE"
echo "Project:        projects/$PROJECT_ID"
echo "Parent branch:  $PARENT_BRANCH"
echo "Attendees:      $*"
echo "Dry run:        $DRY_RUN"
echo

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRY RUN: %s\n' "$*"
  else
    "$@"
  fi
}

# Fail fast if the parent branch is absent, rather than creating orphan branches.
if [[ "$DRY_RUN" != "1" ]]; then
  databricks postgres get-branch \
    "projects/$PROJECT_ID/branches/$PARENT_BRANCH" \
    --profile "$PROFILE" >/dev/null
  echo "Parent branch resolved."
  echo
fi

for slug in "$@"; do
  branch_id="dev-${slug}"
  branch_path="projects/$PROJECT_ID/branches/$branch_id"

  echo "--- $slug -> $branch_path"

  # --replace-existing makes reprovisioning idempotent, so a partly completed
  # run can be repeated safely.
  run databricks postgres create-branch "projects/$PROJECT_ID" "$branch_id" \
    --replace-existing \
    --json "{\"spec\": {\"source_branch\": \"projects/$PROJECT_ID/branches/$PARENT_BRANCH\", \"no_expiry\": true}}" \
    --profile "$PROFILE"

  echo "Branch ready. The attendee agent creates its primary endpoint with scale-to-zero."
done

echo
echo "Done. Give each attendee only their own slug:"
for slug in "$@"; do
  echo "  --var attendee_slug=$slug"
done
echo
echo "Attendees deploy their app BEFORE running anything locally, so the app's"
echo "service principal creates and owns app_write on their own branch."
