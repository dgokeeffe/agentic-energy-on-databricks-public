# Lakebase control-plane schema

`control_plane.sql` is an idempotent schema artifact for an organizer-provisioned
Lakebase project. It is not executed by local fixture tests and is not recreated
by every DAB deployment.

Before use, the facilitator must choose and document the target project, branch,
database, schema, catalog, Volume, service principal, and permission grants in
private deployment configuration. Do not commit workspace URLs, profiles,
OAuth tokens, passwords, or tenant-specific identifiers here.

The schema contains:

- `source_metadata` — active source contracts and registered adapter/worker keys
- `metadata_versions` — immutable snapshots for reproducible runs
- `pipeline_runs` — dispatcher-level run state and aggregate counts
- `pipeline_run_sources` — per-source worker status and reconciliation evidence

The dispatcher and optional Databricks App are follow-on control-plane work. The
core local and serverless fixture path continues to use versioned repository
metadata until that integration is explicitly enabled.

## Applying it

The schema is applied by a standalone script, not by `bundle deploy` — migrations
are reviewed artifacts, not a side effect of shipping code:

```bash
scripts/lakebase_migrate.py <instance-name>          # apply (idempotent)
scripts/lakebase_migrate.py <instance-name> --check  # verify only
```

The script carries a PEP 723 header, so `uv run` supplies `psycopg` in an
ephemeral environment. It is not a dependency of the wheel, and the ETL runtime
stays dependency-free.

## Connecting

Authentication is OAuth, never a stored password: the Postgres role name *is* the
Databricks identity, and the password is a ~1 hour token from
`databricks database generate-database-credential`. There is no secret to rotate.

An identity needs **both** halves before it can connect, and both failures look
identical from Postgres (`password authentication failed for user '<identity>'`,
despite no password being involved):

1. `CAN_USE` on the database instance, so it can mint a credential; and
2. a role registered through the instance's roles API with an `identity_type`.

Creating the role by hand in SQL is the trap. `CREATE ROLE "<identity>" WITH
LOGIN` succeeds and sets `rolcanlogin`, but registers as `identity_type:
PG_ONLY` — a plain Postgres role with no link to a Databricks identity, which can
never satisfy an OAuth login. It also then blocks correct registration
("Requested role conflicts with existing role"). Use:

```bash
scripts/lakebase_register_identity.sh <instance> <identity> [USER|SERVICE_PRINCIPAL|GROUP]
```

For a service principal the identity is its **application ID**, which is also the
Postgres role name and the `sub` claim of the credential it mints.
