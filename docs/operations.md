# Operations and release

## Configure an isolated target

Run `databricks auth profiles` and choose a profile explicitly. Every authenticated command below requires `--profile`; Make targets require `PROFILE` and reject an empty value. Nothing selects DEFAULT automatically.

Provision the necessary project, dedicated branch/endpoint and Lakebase catalog with:

```sh
make provision PROFILE=<profile> CATALOG=<catalog> DEPLOYMENT_ID=<unique-id> TARGET=lab
```

The idempotent command creates a dedicated runtime service principal for `lab`, grants it USE CATALOG, and writes the private bundle values automatically. It never deletes or replaces existing resources. Run with `TARGET=dev` to create a separate development branch in the same project. Small endpoints autoscale from 0.5 to 1 CU and suspend after five idle minutes. The platform's production seed branch is not used by either app target.

Alternatively, keep private values in the ignored `.databricks/bundle/dev/variable-overrides.json` (or `lab/`):

```json
{
  "catalog": "<existing-catalog>",
  "deployment_id": "<unique-lowercase-id>",
  "schema_suffix": "<unique_sql_suffix>",
  "lakebase_project_id": "<existing-project-id>",
  "postgres_branch_id": "<dedicated-branch-id>",
  "runtime_service_principal": "<required-for-lab>"
}
```

Use a deployment ID of at most 18 lowercase letters, digits or hyphens, starting with a letter. Schema suffixes use letters, digits and underscores. Supply a unique suffix per developer or facilitator-managed lab. Branch selection is explicit; never silently reuse production. `postgres_database_id` defaults to resource ID `databricks-postgres`; its Postgres database name is `databricks_postgres`.

The deploying identity needs permission to create schemas in the catalog and create/manage the bundle resources. The lab runtime principal needs USE CATALOG; the bundle grants USE SCHEMA, CREATE TABLE, CREATE MATERIALIZED VIEW on its pipeline schema, CREATE TABLE/USE SCHEMA on its serving schema, and landing Volume access. The deployer must be allowed to run as that principal. Grant catalog access through the catalog owner. Schema/Volume grants and job permissions must resolve to valid account/workspace identities. New service-principal role grants can take several minutes to propagate to jobs and pipelines; a temporary run-as denial after provisioning is not a YAML syntax error. Configure `participant_group` and `facilitator_group` for the workspace when the default groups do not apply.

The baseline defaults to synthetic snapshot input. To use live NEMWEB, explicitly configure `nemweb_mode=live` and `allow_live_nemweb=true` in a fresh isolated schema/landing setup. Do not switch an established schema between modes: Bronze append history and serving keys are not a mode migration mechanism.

## Deploy, publish, sync, run

1. Run `make setup`, `make check`, and `npm --prefix app run test:smoke`.
2. Run `make validate PROFILE=<profile> TARGET=<dev|lab>` for each configured target. This checks required isolation values and invokes strict authenticated bundle validation.
3. Run `make deploy PROFILE=<profile> TARGET=<target>`. It builds the app and wheel, uploads source/build artifacts, and creates the resources with the app stopped. Both targets' schedules remain paused.
4. Run `make refresh PROFILE=<profile> TARGET=<target>`. This lands registration, regional context, and critical feeds before the full pipeline update. The independently runnable `nemweb_lander` job accepts `critical`, `regional`, or `context` scope. The `nemweb_context_refresh` job refreshes registration Bronze only; follow it with a full refresh when dependent Gold must change.
5. Run `make publish PROFILE=<profile> TARGET=<target>`. Three sequential SQL tasks merge regular Delta sources. No absent rows are deleted; source corrections update matching keys. Publication is repeatable. Run it only after a successful pipeline update.
6. Create the three Lakebase syncs using the supported Postgres CLI flow below. Confirm successful sync status and reconcile source/synced exports. After later publications, explicitly refresh each TRIGGERED sync's managed pipeline and repeat verification.
7. Obtain the app's `service_principal_client_id` from `databricks apps get <app-name> --profile <profile>`. As the Lakebase owner, apply `resources/lakebase/grants.sql` using psql with `--set=app_principal=<client-id>` on the chosen branch/database. This grants SELECT only on the three synced tables.
8. Run `make app-deploy PROFILE=<profile> TARGET=<target>`. It validates, builds, syncs, and starts the app separately. On startup the app creates its native investigation schema. Deploy before authenticated local development so the app principal owns that schema.
9. Inspect `databricks apps get <app-name> --profile <profile>` and the application logs. Confirm all three API reads succeed, the map/fuel panels render, and an investigation can be created, updated, and deleted by its owner.

If a later `make deploy` stops an existing app because `lifecycle.started` is false, repeat the explicit app-deploy step. This is deliberate separation of infrastructure and app runtime.

## Supported sync commands

First inspect `databricks postgres create-synced-table --help` and `get-synced-table --help` for the installed CLI. The chosen Postgres database must already be registered as a Lakebase Unity Catalog catalog. The sync operator needs source USE CATALOG/SCHEMA and SELECT, plus CREATE TABLE in a regular UC storage schema.

```sh
python3 scripts/lakebase-sync.py render \
  --profile <profile> --lakebase-catalog <registered-lakebase-catalog> \
  --catalog <regular-uc-catalog> --serving-schema <serving-schema> \
  --storage-schema <pipeline-schema> \
  --branch projects/<project>/branches/<branch>
```

This writes ignored JSON requests to `.databricks/sync/` and prints reviewable CLI argument arrays. Execute each as a `databricks postgres create-synced-table <lakebase-catalog>.app_read.<table> --json @<request-file> --profile <profile>` command. Requests use TRIGGERED policy, stable primary keys, CDF-enabled regular Delta sources, and a regular UC catalog for pipeline metadata. Do not use the Lakebase catalog as the pipeline storage catalog.

```sh
python3 scripts/lakebase-sync.py status \
  --profile <profile> --lakebase-catalog <registered-lakebase-catalog>
```

Status inspection alone does not prove data parity. Confirm the sync is ready and its managed pipeline update succeeded. Use the managed pipeline ID returned by the service with `databricks pipelines start-update <pipeline-id> --profile <profile>` for subsequent TRIGGERED refreshes; inspect that update before continuing.

Export the same bounded window, columns, and ordering from each regular Delta source and its Postgres synced table. Preserve timezone offsets in timestamp exports. Compare all three pairs:

```sh
python3 scripts/verify-sync.py source-region.json synced-region.json --keys serving_key
python3 scripts/verify-sync.py source-fuel.json synced-fuel.json --keys interval_end region_id fuel_type
python3 scripts/verify-sync.py source-unit.json synced-unit.json --keys interval_end duid
```

The verifier rejects empty exports, duplicate/null keys, missing columns, and value mismatches. Timestamp offsets normalize to UTC and equivalent numeric encodings compare equally. Keep export files and run evidence outside Git. Include current publication timestamps and the verified time window in rehearsal evidence; snapshot interval age is expected and must not be labelled live.

## CI and release gate

PRs run Python tests and app typecheck, lint, unit tests, build, and browser smoke tests. Authenticated validation is manually dispatched in the configured GitHub `dev` environment. Deployment is manually dispatched against `dev` or `lab`, with strict validation before the chosen deploy/refresh/publish/app step. Configure GitHub environment OAuth secrets `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, and environment variables matching the workflow's `BUNDLE_VAR_*` mappings. The workflow writes only an explicitly named `ci` profile. Protect the `lab` environment with the team's review requirements.

No merge triggers fleet deployment. Before merging this refactor into `main`, review the diff and rehearse the full path in one isolated lab: validate both configured targets, run refresh and repeat publication, verify stable keys and additive history, confirm all three syncs and API/client contracts, and test native investigation ownership and version conflicts. Record job/update IDs, sync status, bounded parity results, app revision, and any limitations.

Only after that review and rehearsal should a maintainer merge the accepted revision and create the agreed release tag. No baseline tag has been assigned by this repository change. Labs start from that accepted revision; solutions remain separate branches. Existing deployed resources are neither deleted nor adopted by this new bundle.

## Workspace authoring and deployment

The root `databricks.yml` is the bundle entrypoint, including `resources/*.yml`. Each typed resource file contains one resource under `resources.<type>.<key>`; shared configuration belongs in ordinary `.yml` files. Paths in resource files are relative to that file, so pipeline libraries and scripts start with `../src/` and `../scripts/`. Dataset files import `agentic_energy` from the pipeline's `../src` root; helpers are not pipeline libraries.

The CLI version constraint is 1.16.1 or newer, and CI installs the rehearsed 1.16.1 version. Check the CLI version shown in the workspace Deploy dialog before using the direct engine. A workspace Git folder recognizes the bundle by its root `databricks.yml`. Workspace deployment requires serverless compute and can target only that same workspace. Supply the same private target variables in the workspace checkout; ignored local override files are not carried through Git.

App lockfiles use public registry tarball URLs; package versions and integrity hashes remain pinned. Avoid committing internal npm proxy URLs that workspace app installers cannot reach.

`make deploy` builds the Node application locally as a preflight check, lets the bundle build its Python wheel with `uv`, then grants the lab runtime read access to uploaded source and artifacts. Databricks Apps also runs `npm run build` remotely during the separate app deployment, so shared preview fixtures live under client source and remain available when tests are excluded from sync. Clicking Deploy in the workspace does not run the Makefile's permission hook. Before using the UI, verify its wheel-build environment and arrange equivalent runtime source permissions, then perform the separate app deployment. Do not infer UI support or failure from the local Node build alone. The Makefile/CI path is verified independently; workspace UI deployment still needs its own rehearsal.

Keep cron expressions under job `schedule`, with explicit `PAUSED` status. Scope `run_as` to jobs and pipelines: a bundle-wide runtime identity conflicts with the app's deployment ownership. The app owns its native Postgres writes under its own service principal.

The current upstream `lakeflow-pipelines` init template specializes the default template for workspace authoring: one serverless pipeline and a transformations directory. The baseline extends that source separation with Bronze, Silver, Gold, and shared modules inside its retained Python package. Separate medallion directories do not require separate pipelines.

References checked during this refactor:
- [Workspace bundle requirements](https://docs.databricks.com/aws/en/dev-tools/bundles/workspace)
- [Workspace deployment and source linking](https://docs.databricks.com/aws/en/dev-tools/bundles/workspace-deploy)
- [Workspace authoring and editing limitations](https://docs.databricks.com/aws/en/dev-tools/bundles/workspace-author)
- [Upstream Lakeflow template](https://github.com/databricks/cli/tree/main/libs/template/templates/lakeflow-pipelines)

After successful publication, `make publish` grants the selected operator SELECT on exactly the three serving source tables. A different sync operator needs equivalent source SELECT access plus the documented target-schema privileges. The grants are additive and do not change table ownership.

For full-row parity, export Delta timestamps with all six fractional digits (for example, Spark `to_json` with `timestampFormat=yyyy-MM-dd HH:mm:ss.SSSSSSXXX` and `timeZone=UTC`). The SQL Statement API default timestamp rendering can truncate to milliseconds; do not round the Postgres export to conceal a mismatch. Preserve nulls and Boolean types in both exports.

## Snapshot rehearsal

The default application snapshot is `v2`: it aligns the synthetic regional dispatch and SCADA examples on two five-minute intervals on 1 July 2026. Registration retains the original row-preserving AEMO excerpt. The older `v1` fixtures remain unchanged for parser regression tests. Neither snapshot is live-market evidence; the regional fixture covers NSW only. Snapshot URLs are converted to public report paths before immutable archive landing. Each job task attempt has a distinct run ID so serverless retries preserve, rather than overwrite, earlier failure manifests.

## Baseline rehearsal results

The isolated snapshot rehearsal passed strict CLI validation for both targets, the complete medallion update, and two successful publication runs. All three CDF-enabled serving tables matched their synced Postgres tables across every exported column: 2 regional rows, 22 fuel rows, and 28 unit rows. Each sync reached `SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE`.

The deployed app returned those same row counts from its three authenticated APIs. Native investigation create, list, update, stale-version rejection, and deletion passed under the authenticated operator identity; the temporary check record was removed. Local verification passed 163 Python tests, 102 application tests, typecheck, lint, build, and 5 browser smoke tests. The browser suite uses prepared API responses; deployed API and native-write checks are separate evidence.

Job IDs, pipeline updates, full-row exports, app deployment ID, and verification responses are kept in ignored `.databricks/bundle/lab/`. The fixture is non-live and has NSW regional coverage. Workspace UI deployment has not been exercised. Two requests to Logfood Genie timed out; the workspace guidance above is based on the cited public documentation and upstream CLI templates.
