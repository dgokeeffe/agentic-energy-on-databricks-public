# Retire an isolated workshop environment

Reset is the non-destructive normal refresh in `RUNBOOK.md`. Permanent retirement
is a separate facilitator operation. No deletion command in this document was
executed as part of the rehearsal. Command shapes were checked against CLI 1.16.1;
verify them again with `--help` before a later retirement.

First stop scheduling and new attendee work. Export any wanted native
investigations and retain run evidence privately. Inspect the bundle summary
(after all bundle commands finish), target overrides, and `lakebase.json` to
write an exact resource inventory. Confirm the app, every job and pipeline,
warehouse, two regular schemas, Lakebase catalogs and project all belong to the
approved deployment ID. A matching name alone is insufficient if ownership or
branch bindings disagree. Check both dev and lab; a target that was only
provisioned has no deployed jobs or pipeline to delete.

The inventory must explicitly exclude `baseline0911`, its schemas, branches,
app and all other pre-existing deployments. Obtain approval for that concrete
inventory before permanent deletion. Keep `main` and `baseline-v1` unchanged.

For temporary retirement, stop only the named workshop app; schedules are already
paused, SQL warehouses auto-stop, and Lakebase endpoints suspend after five idle
minutes. This retains the environment for review:

```sh
databricks apps stop <workshop-app-name> --profile <profile>
```

After approval for permanent retirement, execute the applicable steps in order,
substituting only identifiers from that reviewed inventory:

1. Delete the stopped workshop app with
   `databricks apps delete <workshop-app-name> --profile <profile>`.
2. Delete each of its three synced tables with
   `databricks postgres delete-synced-table synced_tables/<lakebase-catalog>.app_read.<table> --profile <profile>`.
   Wait for each operation to finish. Inspect its managed pipeline disposition;
   do not identify a managed pipeline by guessing from its display name.
3. Delete the bundle's four jobs using
   `databricks jobs delete <job-id> --profile <profile>`, its one authored pipeline
   using `databricks pipelines delete <pipeline-id> --profile <profile>`, and its
   SQL warehouse using `databricks warehouses delete <warehouse-id> --profile <profile>`.
   None of these IDs should come from another environment or a name-only search.
4. Unregister each workshop Lakebase catalog using
   `databricks postgres delete-catalog catalogs/<lakebase-catalog> --profile <profile>`.
   Delete only the dedicated workshop project using
   `databricks postgres delete-project projects/energy-<deployment-id> --profile <profile>`.
   Project deletion removes all branches and their native data; it is not a
   per-attendee reset. Do not do this if a project contains unapproved branches.
5. After retaining any required immutable source archives, delete the approved
   regular pipeline and serving schemas using
   `databricks schemas delete <catalog>.<schema> --force --profile <profile>`.
   This is destructive and includes the landing Volume and table history.
   The baseline Volume's bundle `prevent_destroy` guard must never be disabled
   merely to make an indiscriminate `bundle destroy` succeed.
6. Have the identity owner remove the dedicated runtime principal only after
   checking it has no remaining dependents or grants outside this environment.
   Keep the parent UC catalog, shared groups and deploying user intact.

Re-read every approved identifier after deletion and record its not-found result.
Retain the old bundle state and evidence as an archive, and label the deployment
retired so nobody deploys into stale bindings. A future workshop uses a new
identifier and fresh private configuration. Removing local overrides or a Git
branch does not delete workspace resources.
