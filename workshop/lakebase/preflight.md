# Facilitator Lakebase preflight

Use only the explicit `DEFAULT` profile. Record resource names, states, and command exit codes, but never hosts, tokens, workspace URLs, tenant IDs, or service-principal IDs.

1. Confirm Databricks CLI 1.0 or later and Python SDK 0.81 or later.
2. Run `databricks postgres -h` and `databricks postgres create-synced-table -h` with `--profile DEFAULT` where accepted.
3. Confirm Lakebase Autoscaling and PostgreSQL 17. Do not use retired Provisioned Lakebase.
4. Confirm the LTAP Direct Writes Beta preview. If unavailable, record the ordinary initial-load fallback; synced tables remain supported.
5. Confirm the Lakebase Change Data Feed preview and `create-cdf-config` command.
6. Use a destination catalog with explicit managed storage that is not reachable only through a private endpoint. Default-storage catalogs are unsupported for CDF.
7. Confirm Unity Catalog, SQL warehouse, Apps, Lakeflow, and Postgres permissions separately.
8. Check every proposed run-specific name for collision before creation. Never reuse an unrelated resource.
9. For Track C endpoint bootstrap, record the facilitator approval and add the
   approved participant group to the Lakebase project with temporary `CAN_MANAGE`.
   This is project-wide rather than branch-scoped; do not grant it to the App's
   service principal:

   ```bash
   databricks permissions update database-projects "$BUNDLE_VAR_lakebase_project_id" \
     --json '{"access_control_list": [{"group_name": "<approved-participant-group>", "permission_level": "CAN_MANAGE"}]}' \
     --profile DEFAULT
   ```

   Attendee agents use the endpoint helper only. After every endpoint is ready,
   revoke the temporary group permission through the Lakebase project
   permissions UI, preserving the facilitator/admin access.
10. Deploy the app before schema initialisation so its service principal creates and owns `app_write`.
11. Leave recurring schedules paused. Do not run destructive refresh or cleanup.
