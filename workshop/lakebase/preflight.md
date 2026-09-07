# Facilitator Lakebase preflight

Use only the explicit `daveok` profile. Record resource names, states, and command exit codes, but never hosts, tokens, workspace URLs, tenant IDs, or service-principal IDs.

1. Confirm Databricks CLI 1.0 or later and Python SDK 0.81 or later.
2. Run `databricks postgres -h` and `databricks postgres create-synced-table -h` with `--profile daveok` where accepted.
3. Confirm Lakebase Autoscaling and PostgreSQL 17. Do not use retired Provisioned Lakebase.
4. Confirm the LTAP Direct Writes Beta preview. If unavailable, record the ordinary initial-load fallback; synced tables remain supported.
5. Confirm the Lakebase Change Data Feed preview and `create-cdf-config` command.
6. Use a destination catalog with explicit managed storage that is not reachable only through a private endpoint. Default-storage catalogs are unsupported for CDF.
7. Confirm Unity Catalog, SQL warehouse, Apps, Lakeflow, and Postgres permissions separately.
8. Check every proposed run-specific name for collision before creation. Never reuse an unrelated resource.
9. Deploy the app before schema initialisation so its service principal creates and owns `app_write`.
10. Leave recurring schedules paused. Do not run destructive refresh or cleanup.
