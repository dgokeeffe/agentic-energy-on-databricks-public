# Deployment

This repository uses a Databricks Asset Bundle with the **direct deployment
engine**. The bundle does not use Terraform state and does not require
participants to upload files manually to the workspace. The selected workspace
is supplied through the standard `DATABRICKS_HOST` authentication environment;
Databricks does not allow bundle variables in authentication fields.

The deployed unit is a packaged Python wheel running as one serverless Jobs
workflow. The wheel contains the metadata-driven Bronze/Silver/Quarantine/Gold
runner and the deterministic fixture metadata. The job writes each run to a
Unity Catalog Volume under a run-specific directory.

## Prerequisites

- Databricks CLI 1.9.0 or later (`databricks version`)
- `uv`
- An authenticated Databricks CLI session for the selected workspace
- Permission to create/update the bundle job
- A pre-created Unity Catalog catalog, schema, and landing Volume for the target
- A service principal with write access to the landing Volume
- A participant group with read/run access and a facilitator group with job-management access

Authenticate outside the repository. Do not put tokens in `.env` or Git:

```bash
databricks auth login --host https://<workspace-host>
```

Set the required bundle variables in the shell or CI secret store. The
Databricks CLI reads bundle variables from `BUNDLE_VAR_<name>` — the
`DATABRICKS_` prefix is **not** recognised and leaves every variable unassigned:

```bash
export DATABRICKS_HOST="https://<workspace-host>"
export BUNDLE_VAR_catalog="<catalog>"
export BUNDLE_VAR_schema="<schema>"
export BUNDLE_VAR_landing_volume="agentic_energy_landing"
export BUNDLE_VAR_participant_group="<participant-group>"
export BUNDLE_VAR_facilitator_group="<facilitator-group>"

# workshop target only — dev runs as the deploying identity
export BUNDLE_VAR_runtime_service_principal="<etl-service-principal-application-id>"
```

`.env.example` documents the names but is intentionally not loaded
automatically.

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

So N developers can run `./scripts/deploy.sh dev` simultaneously and get N
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

Each deploying identity needs `WRITE VOLUME` on the landing Volume. Grant it to
a group containing the developers (or their service principals) rather than
per-identity.

The per-developer jobs are disposable. The durable evidence of a run is the
immutable manifest under the Volume, not the job or its run history.

## Deploy to development

```bash
./scripts/deploy.sh dev
```

The script performs strict bundle validation, builds the wheel through the
bundle artifact definition, and deploys with the direct engine. The bundle
creates/updates:

- one serverless Python wheel Job; and
- a paused 30-minute schedule.

The landing Volume is deliberately **not** bundle-managed. It is persistent
infrastructure and must be provisioned once by the facilitator or platform
owner. This prevents a changed Volume variable or an accidental bundle destroy
from deleting run evidence.

The bundle also configures the ETL service principal and participant/facilitator
job permissions. Volume grants must be provisioned separately: the service
principal writes, while participants receive read access only.

The schedule is intentionally paused. A participant or facilitator starts a
run explicitly after checking the target and permissions:

```bash
databricks bundle run agentic_energy_etl -t dev
```

Inspect the run output under:

```text
/Volumes/<catalog>/<schema>/<landing_volume>/<target>/runs/<job-run-id>/
```

The output includes Bronze, Silver, Quarantine, Gold, and `manifest.json`.
The manifest records the external job run ID when the job is launched by
Databricks.

The job accepts a metadata contract as a job parameter. With no override it
uses the fixture contract packaged in the wheel. To run an immutable contract
snapshot staged in a Volume, pass its path and snapshot ID without rebuilding
the wheel:

```bash
databricks bundle run agentic_energy_etl -t dev --params \
  metadata_path=/Volumes/<catalog>/<schema>/<volume>/metadata/snapshot.json,\
  metadata_snapshot_id=snapshot-20260810
```

The metadata file remains the input contract. For a Volume snapshot, stage it
using the same contract-root layout as the wheel:

```text
<landing-volume>/metadata/snapshot.json
<landing-volume>/fixtures/<source-files>
```

The framework resolves `fixture_path` values from the contract root (the parent
of the metadata directory), while rejecting paths outside that root. The same
runner can therefore consume packaged fixtures, Volume-staged inputs, or a
later Lakebase snapshot materialized by a dispatcher.

## Workshop deployment

Only the facilitator should deploy the shared workshop target:

```bash
./scripts/deploy.sh workshop
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

Live mode is not enabled by the initial bundle. The deployed Job hard-codes
fixture mode. Live mode requires a reviewed bundle change and a human
facilitator deployment gate; it is not an ordinary participant run parameter.

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
databricks.yml                         # direct engine, targets, wheel artifact
resources/agentic_energy_job.job.yml   # generic serverless ETL Job
scripts/deploy.sh                      # validate + deploy wrapper
agentic_energy/                         # installable Python package
resources/lakebase/control_plane.sql    # separate idempotent control-plane SQL
```

Lakebase SQL is kept as a versioned, idempotent migration artifact rather than
being recreated during every bundle deployment. The metadata framework can run
entirely from packaged repository metadata in fixture mode; a later control
plane integration can pass an immutable Lakebase metadata snapshot path and ID
to the same runner contract.
