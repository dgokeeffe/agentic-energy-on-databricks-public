#!/usr/bin/env bash
# Register a Databricks identity as a Postgres role on a Lakebase instance.
#
# Two independent things must both be true before an identity can connect:
#
#   1. workspace ACL   — CAN_USE on the database instance, so it may mint a
#                        credential at all
#   2. Postgres role   — a role of the same name, registered with the right
#                        identity_type, so the gateway will accept that
#                        credential's OAuth token
#
# The trap: `CREATE ROLE "<identity>" WITH LOGIN` in psql looks like it works and
# creates a role with rolcanlogin=true, but the roles API reports it as
# identity_type PG_ONLY — a plain Postgres role with no link to a Databricks
# identity. OAuth login then fails with a message that points at the wrong thing:
#
#     password authentication failed for user '<identity>'
#
# There is no password involved. The role must be created through
# /api/2.0/database/instances/<instance>/roles with an identity_type, which is
# what this script does. A PG_ONLY role of the same name blocks creation
# ("Requested role conflicts with existing role") and must be deleted first.
#
# Credentials are short-lived OAuth tokens (~1h) from
# `databricks database generate-database-credential`; there is no stored password
# to rotate or leak.
#
# Idempotent: an already-correct role is left alone.
#
# Usage:
#   scripts/lakebase_register_identity.sh <instance> <identity> [USER|SERVICE_PRINCIPAL|GROUP] [membership]
#
#   identity   — user email, service principal APPLICATION ID, or group name
#   membership — DATABRICKS_SUPERUSER (default) or omit for no membership role
set -euo pipefail

INSTANCE="${1:?usage: $0 <instance> <identity> [identity-type] [membership-role]}"
IDENTITY="${2:?usage: $0 <instance> <identity> [identity-type] [membership-role]}"
IDENTITY_TYPE="${3:-SERVICE_PRINCIPAL}"
MEMBERSHIP="${4:-DATABRICKS_SUPERUSER}"

ROLES_API="/api/2.0/database/instances/$INSTANCE/roles"

existing_type() {
  databricks api get "$ROLES_API" -o json 2>/dev/null | python3 -c "
import json,sys
for r in json.load(sys.stdin).get('database_instance_roles', []):
    if r.get('name') == '$IDENTITY':
        print(r.get('identity_type', ''))
        break
"
}

CURRENT="$(existing_type)"
case "$CURRENT" in
  "$IDENTITY_TYPE")
    echo "role $IDENTITY already registered as $IDENTITY_TYPE — nothing to do"
    ;;
  PG_ONLY)
    echo "role $IDENTITY exists as PG_ONLY (cannot authenticate via OAuth) — replacing"
    databricks api delete "$ROLES_API/$IDENTITY" >/dev/null
    CURRENT=""
    ;;
  "") ;;
  *)
    echo "role $IDENTITY is registered as $CURRENT, not $IDENTITY_TYPE" >&2
    echo "delete it first: databricks api delete $ROLES_API/$IDENTITY" >&2
    exit 1
    ;;
esac

if [ -z "$CURRENT" ]; then
  echo "registering $IDENTITY as $IDENTITY_TYPE (membership: ${MEMBERSHIP:-none})"
  BODY="{\"name\":\"$IDENTITY\",\"identity_type\":\"$IDENTITY_TYPE\""
  [ -n "$MEMBERSHIP" ] && BODY="$BODY,\"membership_role\":\"$MEMBERSHIP\""
  BODY="$BODY}"
  databricks api post "$ROLES_API" --json "$BODY" >/dev/null
fi

# Half two: without CAN_USE the identity cannot mint a credential, and the
# failure again surfaces as a Postgres auth error rather than a permission error.
echo "granting CAN_USE on instance $INSTANCE to $IDENTITY"
case "$IDENTITY_TYPE" in
  USER)               PRINCIPAL_KEY="user_name" ;;
  GROUP)              PRINCIPAL_KEY="group_name" ;;
  SERVICE_PRINCIPAL)  PRINCIPAL_KEY="service_principal_name" ;;
  *) echo "unknown identity type $IDENTITY_TYPE" >&2; exit 2 ;;
esac
databricks api patch "/api/2.0/permissions/database-instances/$INSTANCE" \
  --json "{\"access_control_list\":[{\"$PRINCIPAL_KEY\":\"$IDENTITY\",\"permission_level\":\"CAN_USE\"}]}" \
  >/dev/null

echo
echo "registered roles on $INSTANCE:"
databricks api get "$ROLES_API" -o json | python3 -c "
import json,sys
for r in json.load(sys.stdin).get('database_instance_roles', []):
    print(f\"  {r.get('name')}  {r.get('identity_type')}  {r.get('membership_role') or ''}\")
"
