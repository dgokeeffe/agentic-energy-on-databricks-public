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

## Working with it

Lakebase Autoscaling: **projects** contain copy-on-write **branches**, each with
its own compute endpoint and scale-to-zero. One script drives all of it:

```bash
scripts/lakebase.py up                        # project + production branch + schema
scripts/lakebase.py branch                    # a branch named after you, TTL 7d
scripts/lakebase.py role <sp-application-id>  # let a job identity connect
scripts/lakebase.py verify --branch <b>       # connect + round-trip a row
scripts/lakebase.py psql   --branch <b>       # interactive session
scripts/lakebase.py list
scripts/lakebase.py down --branch <b> --yes
```

It carries a PEP 723 header, so `uv run` supplies `psycopg` in an ephemeral
environment; the wheel's runtime dependencies are untouched.

> The retired **Provisioned** tier (`databricks database`, instances, `CU_1`) must
> not be used — it is being migrated away, and its CLI group is absent from newer
> CLIs. Lakebase Autoscaling needs Databricks CLI >= 0.294.0; the script probes
> for a CLI that has the `postgres` group rather than trusting `PATH` order,
> because an older binary fails with `unknown command "postgres"`, which says
> nothing about versions.

## A branch per developer

A branch is copy-on-write off its parent, created in about four seconds, and
shares storage until it diverges. That makes it the right unit of isolation for
concurrent work: each developer gets a real Postgres database with the schema
already applied, writes their own `source_metadata` rows without colliding, and
throws it away when done. Verified: a row written in a developer branch is not
visible in `production`.

Branches require an expiration policy — the API rejects one with neither `ttl`
nor `no_expiry`. The default here is a 7-day TTL, so abandoned branches are
garbage-collected instead of accumulating cost. Maximum is 30 days.

**A project allows 10 unarchived branches.** Beyond that, give each developer
their own project (`--project agentic-energy-<name>`; the workspace limit is
1000) and let branches serve their features and CI runs.

## Connecting

OAuth only. There is no Postgres password in this project: it is created with
native password login disabled, the Postgres role name *is* the Databricks
identity, and the credential is a bearer token minted per connection with a ~1
hour life. Nothing is stored in a file, env var, secret scope or connection
string. The token travels in the libpq password field because that is the only
slot the wire protocol offers a bearer credential.

Letting an identity in takes **two** steps, and skipping either produces an error
that blames the wrong thing:

1. **Register the role** — `scripts/lakebase.py role <principal>` creates it
   through the roles API with an `identity_type` and
   `auth_method: LAKEBASE_OAUTH_V1`. Creating it in SQL instead
   (`CREATE ROLE "<id>" WITH LOGIN`) appears to work and sets `rolcanlogin`, but
   the role has no link to a Databricks identity and can never satisfy an OAuth
   login. It fails as `password authentication failed for user '<id>'` — with no
   password involved.
2. **Grant the schema** — the same command then grants `USAGE` on the schema plus
   table and sequence privileges, including `ALTER DEFAULT PRIVILEGES` so tables
   added by a later migration stay writable. Without this the connection succeeds
   and every statement fails with `permission denied for schema agentic_energy`,
   which looks nothing like an auth problem.

Roles live on a branch and are inherited by branches created from it, so
registering on `production` before branching covers later branches. For a service
principal the principal is its **application ID**, which is also the Postgres role
name and the `sub` claim of the token it mints.

Verified end to end on this pattern: both a user and a service principal
connected to `production` and to a developer branch, wrote a row, and read it back
attributed to the right identity.
