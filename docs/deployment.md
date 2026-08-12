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

**Working inside a CoDA container (Databricks App terminal / Omnigent runner)?
Skip that step.** Auth is already brokered there: a fresh OAuth bearer is minted
per CLI invocation, no PAT is stored, and `databricks auth login` cannot complete
(its OAuth redirect targets a loopback port no outside browser can reach). Run
`databricks current-user me` to confirm, then deploy. The deploying identity is
the app's service principal unless a PAT was injected — which changes who needs
the Unity Catalog grants below. Full detail, including the two auth errors that
look like missing credentials:
[`.claude/skills/deploying-from-coda/SKILL.md`](../.claude/skills/deploying-from-coda/SKILL.md).

Set the required bundle variables in the shell or CI secret store. The
Databricks CLI reads bundle variables from `BUNDLE_VAR_<name>` — the
`DATABRICKS_` prefix is **not** recognised and leaves every variable unassigned:

`scripts/deploy.sh` resolves `DATABRICKS_HOST` from the authenticated CLI when it
is not already exported, so only the bundle variables are mandatory:

```bash
export DATABRICKS_HOST="https://<workspace-host>"   # optional; auto-resolved
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

## Pushing Git branches from a CoDA container

Databricks auth is brokered in a CoDA container, but **Git push auth is not.**
`GH_TOKEN` is held by the runner supervisor and allow-listed into a filtered
environment for the *initial clone only*; the helper is injected as throwaway
`git -c credential.helper=...` flags that deliberately never reach the cloned
remote. So a clone succeeds and a later push fails:

```text
fatal: could not read Username for 'https://github.com': No such device or address
```

This is expected, not a broken container. Do **not** try to recover the token
from `/proc/<pid>/environ`.

The supported source is the **`coda-omnigent` Databricks secret scope**, readable
with the already-brokered CLI:

```bash
databricks secrets list-scopes
databricks secrets list-secrets coda-omnigent   # key: dgokeeffe-github-token
```

Secret values come back base64-encoded. Decode in memory and hand the token to
Git through an ephemeral `GIT_ASKPASS` helper so it never enters argv, the remote
URL, `.git/config`, or the shell history:

```bash
TOK=$(databricks secrets get-secret coda-omnigent dgokeeffe-github-token \
  | python3 -c 'import sys,json,base64; print(base64.b64decode(json.load(sys.stdin)["value"]).decode())')
ASKPASS=$(mktemp) && chmod 700 "$ASKPASS"
printf '#!/bin/sh\ncase "$1" in *Username*) echo <github-user>;; *) printf "%%s" "$GH_PUSH_TOKEN";; esac\n' > "$ASKPASS"
GH_PUSH_TOKEN="$TOK" GIT_ASKPASS="$ASKPASS" GIT_TERMINAL_PROMPT=0 \
  git push -u origin <branch>
rm -f "$ASKPASS"
```

Rules when using it:

- **Never commit, `echo`, or log the value.** Print only length or a short prefix
  if you must confirm retrieval, and pipe push output through a redaction filter.
- Do not write it into `.git/config`, `~/.git-credentials`, or a `credential.helper`.
- Remove the askpass helper immediately; do not leave it in the workspace.
- Verify afterwards that nothing leaked: `git config --get-all credential.helper`
  should be empty and `.git/config` should contain no token material.

`gh auth login` is the alternative — the `gh` wrapper on `PATH` is pre-tuned for
it (`-h github.com -p https -w --skip-ssh-key`) and gives a browser device-code
flow, after which `gh auth setup-git` makes push work for the session.

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

Each deploying identity needs `WRITE_VOLUME` on the landing Volume:

```bash
scripts/grant-workshop-access.sh <principal> [<principal> ...]   # deployers
scripts/grant-workshop-access.sh --readers <participant-group>    # read-only
```

The script grants the whole `USE_CATALOG` → `USE_SCHEMA` → `READ/WRITE_VOLUME`
chain and verifies it, because a missing *parent* grant surfaces at run time as a
permission error on the Volume path and reads like a Volume-grant problem.

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
