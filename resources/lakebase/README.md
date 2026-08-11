# Persistent Lakebase control plane

The workshop control plane is provisioned in the dedicated Lakebase project:

```text
Project:  agentic-energy-workshop
Branch:   production
Database: databricks-postgres
Schema:   agentic_energy
Profile:  daveok
```

The schema contains:

- `source_metadata` — active source contracts and registered worker/parser keys
- `metadata_versions` — immutable snapshots for reproducible runs (the seed
  snapshot `seed-20260810-113532` is populated)
- `pipeline_runs` — dispatcher-level run state and aggregate counts
- `pipeline_run_sources` — per-source worker status and reconciliation evidence

The canonical schema and seed rows are in
[`control_plane.sql`](control_plane.sql). It is safe to re-run: tables use
`IF NOT EXISTS` and source metadata uses an idempotent upsert.

The Lakebase project is persistent infrastructure and is not recreated by local
pytest runs. The serverless dispatcher still needs to be deployed and wired to
these tables; until then the local CLI continues to use JSON metadata files.

Do not put OAuth tokens, passwords, or workspace-specific secrets in this
repository. Generate short-lived database credentials through the Databricks
CLI or SDK at run time.
