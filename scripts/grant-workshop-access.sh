#!/usr/bin/env bash
# Facilitator step: grant principals the Unity Catalog access the ETL needs.
#
# The landing Volume is deliberately not bundle-managed (see docs/deployment.md),
# so grants are provisioned separately from `bundle deploy`. Every identity that
# deploys the dev target runs the job as itself, so each one needs WRITE_VOLUME.
#
# Volume access needs the whole chain: USE_CATALOG on the catalog, USE_SCHEMA on
# the schema, then READ/WRITE_VOLUME on the Volume. Missing a parent grant fails
# at run time with a permission error on the Volume path, which reads like a
# Volume-grant problem and is not one.
#
# Two things that look like they should work and do not:
#   * Service principals are NOT members of `account users`. A catalog grant to
#     `account users` does not cover app/job service principals; they must be
#     named explicitly (directly, or via an account-level group).
#   * Unity Catalog cannot grant to a *workspace-local* group. Creating one via
#     the workspace SCIM API succeeds and then every grant fails with
#     "Could not find principal with name <group>". Use an account-level group,
#     or pass the principals directly as this script allows.
#
# Idempotent: re-running makes no further change.
#
# Usage:
#   scripts/grant-workshop-access.sh [--readers] <principal> [<principal> ...]
#
#   default    — USE_CATALOG + USE_SCHEMA + READ_VOLUME + WRITE_VOLUME, for
#                identities that deploy and run the job
#   --readers  — USE_CATALOG + USE_SCHEMA + READ_VOLUME, for participants who
#                may inspect governed output but not mutate it
#
# A principal is an account group name, a user email, or a service principal
# application ID. To grant every CoDA app service principal in a fleet:
#
#   scripts/grant-workshop-access.sh \
#     $(databricks apps list -o json \
#       | python3 -c 'import json,sys;print(" ".join(a["service_principal_client_id"] for a in json.load(sys.stdin) if a["name"].startswith("coda")))')
#
# Reads the same BUNDLE_VAR_* variables as scripts/deploy.sh:
#   set -a; . ./.env; set +a
set -euo pipefail

VOLUME_PRIVS='"READ_VOLUME","WRITE_VOLUME"'
if [ "${1:-}" = "--readers" ]; then
  VOLUME_PRIVS='"READ_VOLUME"'
  shift
fi

if [ "$#" -eq 0 ]; then
  echo "usage: $0 [--readers] <principal> [<principal> ...]" >&2
  exit 2
fi

: "${BUNDLE_VAR_catalog:?Set BUNDLE_VAR_catalog}"
: "${BUNDLE_VAR_schema:?Set BUNDLE_VAR_schema}"
: "${BUNDLE_VAR_landing_volume:?Set BUNDLE_VAR_landing_volume}"

CATALOG="$BUNDLE_VAR_catalog"
SCHEMA="$CATALOG.$BUNDLE_VAR_schema"
VOLUME="$SCHEMA.$BUNDLE_VAR_landing_volume"

# One request per securable carrying every principal, so a fleet costs three
# calls rather than three per identity.
changes() {
  local privs="$1" first=1
  printf '{"changes":['
  for p in "$@"; do
    [ "$p" = "$privs" ] && continue
    [ $first -eq 1 ] || printf ','
    first=0
    printf '{"principal":"%s","add":[%s]}' "$p" "$privs"
  done
  printf ']}'
}

apply() {
  local kind="$1" name="$2" privs="$3"; shift 3
  echo "granting [$privs] on $kind $name to $# principal(s)"
  databricks grants update "$kind" "$name" --json "$(changes "$privs" "$@")" >/dev/null
}

apply catalog "$CATALOG" '"USE_CATALOG"' "$@"
apply schema "$SCHEMA" '"USE_SCHEMA"' "$@"
apply volume "$VOLUME" "$VOLUME_PRIVS" "$@"

echo
echo "verifying effective grants:"
python3 - "$CATALOG" "$SCHEMA" "$VOLUME" "$@" <<'PY'
import json
import subprocess
import sys

catalog, schema, volume, *principals = sys.argv[1:]
wanted = {
    ("catalog", catalog): {"USE_CATALOG"},
    ("schema", schema): {"USE_SCHEMA"},
    ("volume", volume): {"READ_VOLUME"},
}
missing = []
for (kind, name), required in wanted.items():
    out = subprocess.run(
        ["databricks", "grants", "get", kind, name, "-o", "json"],
        capture_output=True, text=True, check=True,
    ).stdout
    held = {
        a["principal"]: set(a["privileges"])
        for a in json.loads(out).get("privilege_assignments", [])
    }
    ok = [p for p in principals if required <= held.get(p, set())]
    print(f"  {kind} {name}: {len(ok)}/{len(principals)} principals hold {sorted(required)}")
    missing += [(kind, name, p) for p in principals if p not in ok]

if missing:
    print("\nMISSING:", file=sys.stderr)
    for kind, name, p in missing:
        print(f"  {p} on {kind} {name}", file=sys.stderr)
    sys.exit(1)
print("\nall principals have the full catalog -> schema -> volume chain")
PY
