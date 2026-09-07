# Deployment

This repository uses a Databricks Asset Bundle with the **direct deployment
engine**. The bundle does not use Terraform state and does not require
participants to upload files manually to the workspace. The selected workspace
is supplied through the standard `DATABRICKS_HOST` authentication environment;
Databricks does not allow bundle variables in authentication fields.

The primary deployed system is the governed NEMWEB workflow: a managed landing
Volume, bounded wheel lander, serverless Lakeflow pipeline, paused five-minute
critical orchestration, daily context orchestration, semantic SQL job, Genie
space and AI/BI dashboard. `docs/nemweb-operations.md` is the canonical NEMWEB
operator runbook. The old JSONL runner remains local-fixture compatibility only.

## Prerequisites

- Databricks CLI 1.9.0 or later (`databricks version`)
- `uv`
- An authenticated Databricks CLI session for the selected workspace
- Permission to create/update the bundle resources
- A pre-created Unity Catalog catalog and schema for the target; the bundle
  creates and owns the managed landing Volume
- A service principal that can be granted write access to the managed landing Volume
- A participant group with read/run access and a facilitator group with job-management access

Authenticate outside the repository. Do not put tokens in `.env` or Git:

```bash
databricks auth login --host https://<workspace-host>
```

Set the required bundle variables in the shell or CI secret store:

```bash
export DATABRICKS_HOST="https://<workspace-host>"   # optional; auto-resolved
export BUNDLE_VAR_catalog="<catalog>"
export BUNDLE_VAR_schema="<schema>"
export BUNDLE_VAR_landing_volume="<landing-volume-name>"
export BUNDLE_VAR_participant_group="<participant-group>"
export BUNDLE_VAR_facilitator_group="<facilitator-group>"

# workshop target only — dev runs as the deploying identity
export BUNDLE_VAR_runtime_service_principal="<etl-service-principal-application-id>"
```

`.env.example` documents the names but is intentionally not loaded
automatically.

## Git collaboration

Use the repository's normal GitHub authentication and branch/PR workflow. Do not
put tokens in repository files, remotes, shell history, or issue notes. Coda,
CI, and other hosted environments must supply Git and Databricks credentials
through their own approved secret or identity mechanism.

## Local verification

Run the same checks used before deployment:

```bash
uv run --extra test python -m pytest
rm -rf dist && uv build --wheel --out-dir dist
```

The local default is deterministic fixture mode and does not require a
workspace, network, or credentials.

## Many developers at once

`dev` is a per-developer target, not a shared one. `mode: development` namespaces
every deployment by the deploying identity:

- the job is named `[dev <identity>] [dev] Agentic Energy ETL`
- bundle files and deployment state live under
  `/Workspace/Users/<identity>/.bundle/agentic-energy/dev`

So N developers can run `./nemweb_foundation/scripts/deploy.sh dev` simultaneously and get N
independent jobs. Three rules keep that true:

1. **`dev` must not pin `run_as`.** Binding a service principal into `run_as`
   requires the `servicePrincipal.user` role on it, so a pinned SP makes the
   target deployable by exactly one identity — everyone else gets
   `Cannot bind the service principal provided in 'run_as' field ... (403
   PERMISSION_DENIED)` from `jobs/create`. Only the shared `workshop` target
   pins the ETL SP, and only a facilitator deploys that.
2. **Never share a working directory between identities.** The CLI caches
   deployment state (bundle lineage and created resource IDs) in local
   `.databricks/`. Two identities deploying from the *same* directory makes the
   second one adopt and rename the first one's job instead of creating its own,
   and the first then loses `CAN_MANAGE` on it. One clone per developer; if a
   directory is ever copied between people, delete `.databricks/` first. The
   directory self-ignores (`.databricks/.gitignore` contains `*`), so it is
   never committed or synced.
3. **Outputs are keyed by `{{job.run_id}}`.** The landing Volume is shared, and
   run IDs are workspace-unique, so concurrent runs from different identities
   cannot overwrite each other's evidence.

Each deploying identity needs `WRITE VOLUME` on the landing Volume. After the
bundle has created the managed Volume, use the checked-in, idempotent grant
helper (the catalog, schema, Volume and warehouse values may instead come from
the matching `BUNDLE_VAR_*` environment variables):

```bash
nemweb_foundation/scripts/grant-workshop-access.py \
  --catalog <catalog> --schema <schema> --volume <landing-volume> \
  --warehouse-id <warehouse-id> <principal> [<principal> ...]   # deployers

nemweb_foundation/scripts/grant-workshop-access.py --readers \
  --catalog <catalog> --schema <schema> --volume <landing-volume> \
  --warehouse-id <warehouse-id> <participant-group>              # read-only
```

The helper validates identifiers and principals, uses `--profile daveok` for
every SQL Statement Execution API call, grants the whole `USE CATALOG` →
`USE SCHEMA` → `READ/WRITE VOLUME` chain, polls every statement to terminal
`SUCCEEDED`, and verifies each grant. It accepts no token or workspace URL.
Use `--dry-run` to inspect the quoted SQL without making workspace calls. A
missing *parent* grant surfaces at run time as a permission error on the Volume
path and reads like a Volume-grant problem.

Two traps when granting to a fleet:

- **Service principals are not members of `account users`.** A catalog grant to
  `account users` does not cover app or job service principals; name them
  explicitly or put them in an account-level group.
- **Unity Catalog cannot grant to a workspace-local group.** Creating one
  through the workspace SCIM API succeeds, and then every grant fails with
  `Could not find principal with name <group>`. Use an account-level group.

The per-developer jobs are disposable. The durable evidence of a run is the
immutable manifest under the Volume, not the job or its run history.

## Deploy to development

```bash
./nemweb_foundation/scripts/deploy.sh dev
```

The script performs strict bundle validation, builds the wheel through the
bundle artifact definition, and deploys with the direct engine. The bundle
creates/updates the managed NEMWEB landing Volume, bounded lander, serverless
Lakeflow pipeline, paused critical and context jobs, semantic SQL job, dashboard
and Genie space. Keep schedules paused and validate snapshot mode first:

```bash
(cd nemweb_foundation && databricks bundle run nemweb_refresh -t dev --profile daveok)
```

Raw ZIPs, checksum-addressed parsed JSONL and durable manifests live under the
mode-scoped sibling roots
`/Volumes/<catalog>/<schema>/<landing_volume>/snapshot/` and
`/Volumes/<catalog>/<schema>/<landing_volume>/live/`. The per-mode marker remains
inside each sibling. A legacy marker/data layout at the Volume parent is ignored
and is neither deleted nor migrated. Live mode requires the separate
deployment-controlled `allow_live_nemweb=true` approval described in
`docs/nemweb-operations.md`; participants cannot override lander mode.

## Workshop deployment

Only the facilitator should deploy the shared workshop target:

```bash
./nemweb_foundation/scripts/deploy.sh workshop
```

Use the same Git commit and generated wheel that passed development
verification. Confirm the following before unpausing or starting the schedule:

1. The target catalog, schema, and Volume are correct.
2. Participant roles can read governed outputs but cannot mutate them.
3. The runner's output path is writable by the job identity.
4. Fixture-mode reconciliation passes.
5. Live NEMWEB use has explicit source-term and network approval.
6. Lakebase migrations/control-plane connectivity have been verified, if that
   extension is enabled.

Live mode is not enabled by the initial bundle: snapshot mode and a false live
approval gate are the defaults. Enabling live requires both reviewed bundle
variables and a human facilitator deployment gate; it is not an ordinary
participant run parameter.

## Promotion and rollback

Promote the same reviewed commit/artifact from `dev` to `workshop`; do not
rebuild a different wheel for the shared environment. Keep production/workshop
deployment human-gated.

Rollback code by redeploying a previously accepted commit. Do not use
`bundle destroy` as a rollback mechanism, and do not full-refresh stateful data
without explicit approval. Bronze and run manifests are immutable evidence;
repair downstream projections through a controlled rerun or migration.

## Bundle layout

```text
nemweb_foundation/databricks.yml                         # direct engine, targets, wheel artifact
nemweb_foundation/resources/agentic_energy_job.job.yml   # generic serverless ETL Job
nemweb_foundation/scripts/deploy.sh                      # validate + deploy wrapper
nemweb_foundation/agentic_energy/                        # installable Python package
nemweb_foundation/resources/lakebase/control_plane.sql   # separate idempotent control-plane SQL
```

Lakebase SQL is kept as a versioned, idempotent migration artifact rather than
being recreated during every bundle deployment. The metadata framework can run
entirely from packaged repository metadata in fixture mode; a later control
plane integration can pass an immutable Lakebase metadata snapshot path and ID
to the same runner contract.
