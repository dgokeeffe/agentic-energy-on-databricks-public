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
