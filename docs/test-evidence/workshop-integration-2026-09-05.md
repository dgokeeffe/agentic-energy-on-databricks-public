# Workshop integration evidence — 5 September 2026

## Result

The snapshot vertical slice completed from NEMWEB landing through Bronze, Silver, Gold, a regular Delta serving table, Triggered Lakebase sync, a deployed Databricks App, app-owned investigation writes, Lakebase CDF history, and Lakeflow current state. Insert, update, delete, and unchanged reruns were tested. The historical corpus was not sufficient for responsible ML training, so the MLflow starter was validated without training, model registration, an alias change, batch output, or Model Serving.

All data in this run is snapshot or integration-test data. It is not live NEM evidence.

## Source and repository state

- Private base: `5fa19ea29e433e3f12410af6eab67fbbbbe402d6` (`origin/main`).
- Public comparison: `dgokeeffe/agentic-energy-on-databricks-public@4b664ce`, including `6be7faa` and `ec87239`.
- Working branch: `feat/participant-foundation-app-ml-ltap`.
- Final adjudicated implementation commit: `79ea95dee757e95dfc28151fe713b3796c7eabaa`; later documentation-only commits add the index and adjudication note.
- Pull request: https://github.com/dgokeeffe/agentic-energy-on-databricks/pull/23.
- The public `nemweb-e2e-2026-09-03.md` and JSON retain their historical identity. They prove the public deployment, not this packaged run.

The tracked facilitator implementation moved to `nemweb_foundation/`. Twenty-five Bronze and Silver datasets enable row tracking and Delta Change Data Feed. The critical selection includes `silver_nem_facility_dimension`. The new quality check fails when registration context is expected but all regions or all fuels are `UNKNOWN`.

## Resource names

Run identifier `d4` was derived from the authenticated `daveok` operator and the UTC start date.

Created for this goal:

- Unity Catalog schemas `daveok.agentic_energy_workshop_d4` and `daveok.agentic_energy_workshop_d4_serving`;
- managed Volume `agentic-energy-workshop-d4-landing`;
- bundle root `agentic-energy-workshop-d4-clean` and run-prefixed jobs, pipeline, dashboard, and Genie assets;
- Lakebase Autoscaling project and 48-hour development branch `agentic-energy-workshop-d4`;
- databases `agentic_energy_workshop_d4` and `agentic_energy_workshop_d4_app`;
- registered Lakebase catalog `agentic-energy-workshop-d4-app`;
- Triggered synced table `app_read.nem_region_status_synced`;
- Databricks App `agentic-energy-workshop-d4`;
- CDF destination schema `agentic_energy_workshop_d4_cdf` in an operator-owned catalog with explicit managed storage;
- Lakebase CDF configuration `agentic_energy_workshop_d4` for `app_write` only;
- current-state pipeline `agentic-energy-workshop-d4-cdf-current`.

The Lakebase endpoint uses PostgreSQL 17, 0.5–1.0 CU, a 300-second suspend timeout, and scale-to-zero. Resources remain available for inspection.

## Local and static validation

| Command | Exit | Outcome |
|---|---:|---|
| `make validate-local` | 0 | A clean branch-only worktree passed miniwiki, links, safety, 255 Python tests, snapshot, modern APIs, three wheels, AppKit install/typegen/lint/typecheck/unit/build, and Playwright after the security fix pass. |
| `uv run --extra test python -m pytest` | 0 | 255 branch-only tests passed. |
| `uv run --project nemweb_ml python -m pytest nemweb_ml/tests -q` | 0 | Eleven ML contract tests passed. |
| root, foundation, and ML `uv build --wheel` | 0 | All wheels built. |
| `validate_nemweb_snapshot.py` | 0 | Six archives, 34 files, 103 parsed rows, deterministic path hashes, and `live_evidence=false`. |
| `check_modern_pipeline_apis.py` | 0 | Thirty-three pipeline sources passed in the final clean-worktree `make validate-local` run. |
| foundation strict bundle validation with `--profile daveok` | 0 | Snapshot target and clean run-specific bundle validated. |
| ML strict bundle validation with `--profile daveok` | 0 | Serverless job shells validated. |
| online AppKit type generation with `--wait --no-cache` | 0 | One query described against the isolated Gold table; generated result columns replaced the degraded offline type. |
| AppKit lint, AST lint, unit tests, typecheck, build, and prepared Playwright smoke | 0 | Nine unit tests and one Playwright test passed. |
| `databricks apps validate --profile daveok` | 0 | All AppKit validation checks passed before deployment. |
| `validate_nemweb_genie.py --execute ... --profile daveok` | 0 | Six benchmark and six dashboard SQL statements reached `SUCCEEDED`. |
| `git diff --check` | 0 | No whitespace errors at the checked points. |

The AppKit template is version 0.57.0 from the live CLI manifest. Production `npm audit --omit=dev` reports 17 findings (11 high and six moderate), mostly through the manifest-selected AppKit packages. This is a production dependency risk, not a development-only result. No automatic major AppKit upgrade was applied because it would override the generated version. Production use is deferred until a fresh manifest scaffold or separately reviewed dependency upgrade clears the audit.

## Foundation pipeline

The first selected deployment reused ignored state from the former folder and transiently rebound an existing NEMWEB pipeline and four jobs. Exact update `3ee4b343-14a2-4652-a5f7-603cf390fc81` was cancelled with `full_refresh=false`. After explicit approval, the original definitions, live-mode setting, names, and paused schedules were restored from `origin/main` without running them. Read-only inspection confirmed the original pipeline again targets `daveok.nemweb_dev_daveok` and both original schedules are paused.

A clean bundle root then created new resource identities. Its first context update failed because the earlier cancelled attempt had created the original event-log table in the isolated schema. The event log was renamed rather than dropped.

Successful isolated runs:

- context orchestration `278704230113511`, exact pipeline update `b71bb1b3-bb5d-4c95-be65-f32530ba8926`, `COMPLETED`;
- critical orchestration `108991901734295`, exact selective update `447189da-e3fb-4d00-a319-eb24be50e313`, `COMPLETED`;
- semantic/metric-view job `931446123028290`, `SUCCESS`;
- app serving publication jobs `661191659414351`, guarded rerun `136001824536635`, and final key-overlap-guard run `1057976167103079`, `SUCCESS`;
- deterministic-key selective update `8ebaf442-195b-4b78-b17c-63593627f29c`, `COMPLETED`.

Every update used snapshot mode and `full_refresh=false`. The two recurring jobs remain `PAUSED`.

### Foundation reconciliation

| Object | Rows | Duplicate natural keys |
|---|---:|---:|
| Bronze DU detail | 28 | not applicable |
| Bronze DU allocation | 19 | not applicable |
| Bronze generating units | 14 | not applicable |
| Silver facility dimension | 14 | 0 |
| Gold regional dispatch | 4 | 0 |
| Gold unit dispatch | 28 | 0 |
| Gold SCADA region/fuel | 22 | 0 |
| Gold binding constraints | 2 | 0 |
| Gold interconnector flows | 2 | 0 |
| Gold app region status | 2 | 0 |

All 14 facility rows have a known region; 13 have a known fuel. Unknown-region ratio is 0.00%, and unknown-fuel ratio is 7.14%. Eleven critical expectation records were emitted for the exact critical update, with zero failed records. Bronze, Silver, and Gold watermarks match for regional dispatch, unit SCADA, binding constraints, and interconnector flows. The Gold app table contains two effective NSW1 snapshot intervals.

Semantic SQL, metric views, dashboard SQL, and Genie benchmark SQL passed. The deployed dashboard is active and its serialised definition resolves the run-specific Genie space.

## AppKit deployment and smoke tests

Initial deployment attempts exposed two recoverable issues:

1. the workspace npm proxy repeatedly timed out on Playwright, which was unnecessarily present in the runtime dependency installation;
2. the client used a build-time serving-table fallback and the App service principal lacked explicit Unity Catalog access.

Playwright is now installed only by the local pinned `smoke:install` script. The runtime install uses the manifest-selected application packages. Analytics reads a fixed, reviewed SQL identifier for the regular Delta serving table, so a caller cannot choose another object. The app service principal received only `USE CATALOG`, `USE SCHEMA`, and `SELECT` for that serving table; its earlier SELECT and USE SCHEMA privileges on the pipeline-owned schema were revoked. Final app deployment `01f1a8fd18ac1570812809f44884ff8f` reached `SUCCEEDED`, and the app state is `RUNNING`.

The app service principal created and owns `app_write`; it owns `app_write.investigations`, whose replica identity is `FULL`. Postgres grant checks on `app_read.nem_region_status_synced` returned `can_select=true`, `can_update=false`, and `can_delete=false`.

Authenticated app checks returned:

- HTTP 200 and two rows from `/api/region-status`, proving an app read through the synced Postgres table;
- HTTP 201 for an investigation insert, HTTP 200 for its optimistic version-one-to-version-two update, and HTTP 204 for delete;
- an empty investigation list after delete;
- deployed integration UI smoke: HTTP 200, message `Databricks Analytics integration`, and two rendered regional rows.

Trusted operator identity came from the Databricks Apps proxy. The request body did not carry operator identity.

## Triggered synced table and LTAP

The direct Triggered sync against the pipeline materialised view failed because write-time CDF is unsupported on materialised views. No existing table was deleted. A lakehouse-owned publication job now MERGEs the app projection into a regular Delta table with row tracking, write-time CDF, a deterministic `serving_key`, and prepared-data table properties. A second run-owned database allowed the required target name to be retained without deleting the failed first synced-table attempt.

Successful Triggered sync evidence:

- initial update `50a8e000-5e9c-475f-b410-de6bf077016a`: `COMPLETED`, source two rows, synced two rows, missing 0, extra 0;
- insert update `169afafe-b89b-44a8-ac2f-1b7bc510110c`: one integration row appeared with price 261.0;
- update `96e4e41c-117f-4fdb-9ae8-c6abebed68b4`: the same row changed to 271.0;
- delete `dbd468af-9d84-49e5-8efe-eb6c8a1ffa51`: the integration row disappeared;
- unchanged reruns `eb1dc221-4518-40a4-8cf0-4f675071d3af`, `e433146d-1626-46f9-9930-6a7d2f720959`, and final key-overlap-guard sync `e2aa2f05-0dac-46e0-9402-3d9b7e355eb0`: `COMPLETED`; final reconciliation remained source 2, synced 2, missing 0, extra 0.

LTAP Direct Writes is Beta and requires a workspace preview. The initial sync exposed no event or status field proving Direct Writes use, so no acceleration claim is made. The ordinary Triggered initial-load path is the recorded fallback.

## Lakebase CDF and Lakeflow current state

CDF is configured for `app_write` only. Status is `CDF_STATE_STREAMING`; the final observed committed LSN is `0/289F720`. The app transaction produced this ordered audit history:

| `_sort_by` | Change | Version | State |
|---:|---|---:|---|
| 0 | `insert` | 1 | open |
| 1 | `update_preimage` | 1 | open |
| 2 | `update_postimage` | 2 | reviewing |
| 3 | `delete` | 2 | reviewing |

The update pair shares one transaction and LSN. `_pg_change_type`, `_pg_lsn`, `_pg_xid`, `_timestamp`, and `_sort_by` are present. The generated history table has no Delta CDF property, row filter, or column mask.

Current-state pipeline repair cast CDF's timestamp-without-time-zone metadata to UTC `TIMESTAMP`, avoiding an unsupported target table feature while preserving the field. It also normalises numeric and slash-separated hexadecimal LSNs before tie-breaking, matching the offline reducer. Update `bc2f40d5-0ea1-4354-bbb5-c7e265a67427` published version two as the current row. Update `508efa37-bb1e-4ca5-9386-b5cec08ffdfa` removed it after the delete while leaving all four history events. Unchanged rerun `88459b16-4bed-4c5d-be97-f910bbeb0e34` and final normalisation update `78a7e49c-3478-4bbf-9fef-70c6a0fd9dc5` completed with current state empty.

## ML and MLOps

The public `feat/nem-history-analytics` branch provides backfill code but not a checked-in, attributed, interval-complete training corpus with established class balance. The six-archive workshop snapshot is explicitly too small. ML execution therefore stopped at the required data gate.

The repository still provides serverless training and batch-scoring jobs, MLflow experiment and Unity Catalog registry configuration, chronological split, leakage and schema checks, candidate alias logic, and the Gold prediction contract. Eleven tests and strict bundle validation passed. No model was trained or registered, no `@challenger` or `@prod` alias changed, no prediction table was populated, and no Model Serving endpoint was created.

## Reviewer findings

The first independent security/data review found no critical or high defect. It confirmed parameterised Postgres access, least privilege, CDF replay handling, and no committed secrets. The forwarded identity remains trustworthy only because the Databricks Apps proxy injects it; `DATABRICKS_APP_NAME` is an unconfigured-runtime guard, not an authentication boundary.

A follow-up review raised four blockers. The client-controlled Analytics identifier was replaced with fixed reviewed SQL; both Analytics and synced reads now use the regular Delta serving publication; the publication job now fails on an empty source or when fewer than half of existing serving keys remain and gives participants `CAN_VIEW` only; and Spark now normalises numeric or hexadecimal LSNs before ordering. Production dependency audit findings were reclassified accurately. The security/data re-review returned `PASS` with no blocker after these fixes. The final verification adjudicator also returned `FINAL PASS`: every goal phase is met, with the ordinary Triggered initial-load fallback and the ML data-gate stop recorded. Merge remains a human decision.

## Failures and disposition

- A full bundle deploy proposed destructive Volume/dashboard recreation; it was refused. The Volume was created explicitly, and selected non-destructive bundle resources were deployed.
- Ignored old bundle state transiently changed pre-existing definitions. The run was cancelled, and the original resources were restored after explicit approval.
- The isolated event-log name collided with an artefact from the cancelled attempt. A new event-log name fixed the run without deletion.
- Wall-clock benchmark filters returned no rows for historical snapshot data. Benchmarks and dashboard queries now use a latest-data-relative window while displaying freshness separately.
- Triggered sync could not use CDF from a materialised view. The regular Delta serving publication job fixed the source contract.
- App npm installation timed out on Playwright. Playwright moved to a local-only, pinned smoke installation.
- App analytics initially used a build-time placeholder and lacked Unity Catalog grants. A fixed reviewed query against the regular serving table and narrow grants fixed both without a client-controlled identifier.
- The app-serving delete mirror lacked source guards and was participant-runnable. Empty/shrink assertions and participant `CAN_VIEW` fixed the hazard; non-destructive reset steps are documented.
- The CDF current-state target required the `timestampNtz` table feature. Casting the preserved CDF timestamp to UTC `TIMESTAMP` fixed publication; normalised LSN ordering keeps Spark and offline reducers consistent.
- An unqualified push selected the public remote and was blocked by GitHub push protection before any public change. The explicit private `origin` push succeeded.

## Final state and limitations

- Run-specific recurring jobs: `PAUSED`.
- Original NEMWEB recurring jobs: restored and `PAUSED`.
- Main, synced-table, and CDF pipelines: `IDLE` after terminal updates.
- Databricks App: `RUNNING`.
- Lakebase compute: scale-to-zero configured; resources retained for inspection.
- Pull request: open and not merged.
- Issues #3, #4, #11, #21, and #22 received non-sensitive comments. No participant issue received `workshop-ready`.

Remaining limitations are the unverified LTAP Direct Writes preview/acceleration, insufficient ML history, manifest-selected AppKit dependency audit findings, and the unused failed first synced-table resource retained because deletion was not authorised. No existing non-workshop resource was deleted. Existing NEMWEB definitions were transiently changed by the first deployment and then restored to their original names, schema, live-mode setting, and paused schedules under explicit approval.
