# Facilitator deployment and evidence gates

Facilitator-only. Participants do not deploy the foundation.

This is the operating procedure for the governed NEMWEB foundation. The
authoritative executable step is
[`../nemweb_foundation/scripts/deploy.sh`](../nemweb_foundation/scripts/deploy.sh);
this page is the gate sequence around it. Run the script rather than copying its
commands.

Every workspace-aware command selects its profile explicitly. Never rely on an
implicit or default profile. The name is workspace-specific: the examples below
use `daveok`, and `PROFILE` overrides it in the scripts and Makefile.

## Gate 1 — local and identity

Nothing touches a workspace until these pass.

```bash
git status --short
make validate-local
databricks auth describe --profile daveok
```

Stop if the profile is absent, unauthenticated, or points at an unexpected
workspace.

## Gate 2 — configuration and strict validation

Copy the placeholder file, then replace every placeholder with an approved
non-secret value. Keep `.env` local and uncommitted.

```bash
cp -f env.example .env
set -a; . ./.env; set +a
make bundle-validate PROFILE=daveok
```

`make bundle-validate` pre-checks every no-default variable by name and validates
both the foundation and ML bundles. Authentication belongs in the local CLI
configuration, never in `.env` or Git.

Validation does not authorise deployment.

## Gate 3 — controlled deployment, schedules paused

Requires explicit current human authorisation, recorded before you run it.

```bash
bash nemweb_foundation/scripts/deploy.sh dev
```

### Cold-workspace ordering, verified 2026-09-07

On an empty schema the first deployment **partly fails, and that is expected**.
The Genie space and dashboard cannot be created until the Gold tables and metric
views exist, so the deploy reports:

```text
cannot create resources.genie_spaces.nemweb_analyst:
  Table '<catalog>.<schema>.gold_nem_region_dispatch_5min' does not exist
```

Jobs, pipelines, and the landing Volume are created successfully in that same
run. Complete the cold start in this order, then redeploy:

| Step | Why |
| 1. Run the **context** job (`-context`) | Lands monthly MMSDM registration and materialises `bronze_nem_dudetail`. |
| 2. Run the **critical** job (`-refresh`) | Lands Current reports and publishes the five-minute medallion. |
| 3. Run the **semantics** job (`-semantics`) | Creates the metric views. |
| 4. Re-run `deploy.sh dev` | Creates the Genie space and dashboard. |

**The context job must precede the critical job on a cold schema.** The critical
DAG alone fails with `[SOURCE_TABLE_NOT_MATERIALIZED] … bronze_nem_dudetail`,
because `silver_nem_facility_dimension` needs the monthly registration data that
only the context job lands. This is source cadence, not a defect: registration is
monthly MMSDM, while the critical path is five-minute Current.

Use `--no-wait` when starting a job from the CLI and poll the run, since the
blocking form can exceed a long-running pipeline's duration.

If a previous deployment targeted a different workspace, clear the stale local
bundle state first. It is gitignored and holds resource IDs that no longer exist:

```bash
mv -f nemweb_foundation/.databricks/bundle/dev nemweb_foundation/.databricks/bundle/dev.stale-backup
```

Otherwise the deploy fails with `Unable to find dashboard [<old-id>]`.

The bundle uses the direct deployment engine, so there is no Terraform state. The
script validates and then deploys with the `daveok` profile.

After deployment, confirm before going further:

- both `nemweb_refresh` and `nemweb_context_refresh` are **PAUSED**;
- `allow_live_nemweb` is **false**;
- `nemweb_mode` is **snapshot**;
- the landing Volume exists and grants resolved.

Never unpause a schedule to debug it.

## Gate 4 — snapshot reconciliation

```bash
make foundation-snapshot
```

The validator lands the same versioned archives into two isolated roots, compares
every relative-path SHA-256, and reconciles parsed rows to the immutable manifest.
It does not contact a workspace.

Snapshot output carries `live_evidence: false`. It is never live proof.

## Gate 5 — data and analyst gates

Validate all canonical SQL before creating or updating any analyst asset.

```bash
uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_genie.py

uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_genie.py --execute \
  --profile daveok --warehouse-id "$BUNDLE_VAR_warehouse_id" \
  --catalog "$BUNDLE_VAR_catalog" --schema "$BUNDLE_VAR_schema"
```

Confirm metric-view reconciliation, zero natural-key duplicates, exactly one
effective run per region and interval, and that both intervention rows remain
governed.

## Gate 6 — live proof, separately authorised

Live mode needs its own approval, distinct from the deployment approval. Capture
each scheduled cycle by its **exact** pipeline update ID; never select "latest".

```bash
uv run --project nemweb_foundation python nemweb_foundation/scripts/capture_nemweb_evidence.py \
  --profile daveok \
  --warehouse-id "$BUNDLE_VAR_warehouse_id" \
  --catalog "$BUNDLE_VAR_catalog" \
  --schema "$BUNDLE_VAR_schema" \
  --pipeline-id "$NEMWEB_PIPELINE_ID" \
  --pipeline-update-id "$NEMWEB_UPDATE_ID" \
  --orchestration-run-id "$NEMWEB_JOB_RUN_ID" \
  --output-json /tmp/nemweb-evidence.json \
  --output-markdown /tmp/nemweb-evidence.md
```

Later cycles reuse the same paths and add `--append`. After at least three
consecutive cycles:

```bash
uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_live.py /tmp/nemweb-evidence.json
```

In snapshot mode the capture script refuses by design, reporting that live
evidence requires `nemweb.source_mode=live`. That refusal is correct behaviour,
not a failure to work around.

Do not write a dated PASS evidence file until the validator accepts at least three
consecutive cycles and an independent review finds no unsupported claim. Copy only
reviewed, non-sensitive output. Never include tokens, private workspace URLs, or
tenant identifiers.

## Rollback

Redeploy the last reviewed commit against the same resources and use selective,
non-full pipeline updates. A full refresh is not routine recovery.

For Lakebase, preserve the CDF destination and committed LSN. Disabling CDF,
deleting a synced table, dropping a schema or table, resetting a branch, or
deleting a project each require a separate human decision.

## Stop conditions

Stop, and use a labelled prepared substitute, when:

- a required preflight item in [`../PRE-REQUISITES.md`](../PRE-REQUISITES.md) is
  unverified;
- the profile, workspace, identity, target resources, or permissions differ from
  the approved setup;
- snapshot data is about to be described as live;
- an exact pipeline update cannot be identified;
- a Lakeflow expectation metric is missing or failed; or
- the live source is ahead of Bronze.

Never weaken a check, invent source rows, use a full refresh as routine recovery,
or unpause a schedule to debug it.
