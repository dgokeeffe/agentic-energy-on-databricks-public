# Workshop integration evidence — 4 September 2026

> Superseded by the completed follow-up in [workshop-integration-2026-09-05.md](workshop-integration-2026-09-05.md). This file preserves the interim stop and repair decision.

## Result

Repository, AppKit, ML, and offline Lakebase checks passed. The Databricks vertical slice stopped during the first context pipeline update because ignored bundle deployment state from the former foundation directory had followed the source tree into `nemweb_foundation/`. The selected deployment then reused the pre-existing NEMWEB pipeline identity, which this task explicitly prohibited. The update was cancelled without a full refresh. No further Databricks mutation was attempted.

This file does not claim that the new foundation, app, synced table, CDF feed, Lakeflow current-state table, or ML jobs completed an integrated run.

## Source state

- Private base: `5fa19ea29e433e3f12410af6eab67fbbbbe402d6` (`origin/main`).
- Public comparison: `dgokeeffe/agentic-energy-on-databricks-public@4b664ce`, including the `6be7faa` cold-deploy row-tracking change.
- Implementation commits:
  - `177e021` — participant foundation, row tracking/CDF, app serving table, quality check, and historical evidence;
  - `8085582` — shared GitHub issue lifecycle;
  - `94084fa` — AppKit, ML, and Lakebase starters;
  - `0b43c49` — run-specific bundle deployment state.
- The public files `nemweb-e2e-2026-09-03.md` and `nemweb-e2e-evidence.json` retain their historical identity under `docs/test-evidence/`. They prove the public deployment, not this repackaged foundation.

## Public-to-foundation reconciliation

The tracked facilitator implementation moved to `nemweb_foundation/`. Twenty-five Bronze and Silver declarations now enable `delta.enableRowTracking` and `delta.enableChangeDataFeed`. The five-minute selection includes `silver_nem_facility_dimension`. `quality.py`, the evidence reader, and semantic SQL reject an apparently healthy result when all regions or all fuels are `UNKNOWN` while registration context is expected. Existing parser, correction, intervention, fixed-AEST market time, UTC processing time, lineage, and Gold tests remain green.

## Proposed and created names

The run identifier `d4` was derived from the authenticated `daveok` operator and 4 September 2026 UTC. Collision checks passed before creation.

Created only for this run:

- schema `daveok.agentic_energy_workshop_d4`;
- managed Volume `agentic-energy-workshop-d4-landing` in that schema;
- Lakebase Autoscaling project, development branch, and database named `agentic-energy-workshop-d4`;
- CDF destination schema `agentic_energy_workshop_d4_cdf` in an operator-owned catalog with explicit managed storage.

The Lakebase development endpoint uses PostgreSQL 17, 0.5–1.0 CU, a 300-second suspend timeout, and a 48-hour branch TTL. The resources remain available for inspection. Nothing was deleted.

## Validation commands

| Command | Exit | Outcome |
|---|---:|---|
| `python3 scripts/validate-miniwiki.py` | 0 | Ten miniwiki pages and relative links passed. |
| `python3 scripts/validate-markdown-links.py` | 0 | Ninety-six tracked Markdown files passed before this evidence page was added. |
| `python3 scripts/validate-repository-safety.py` | 0 | Repository safety scan passed. |
| `uv run --extra test python -m pytest` | 0 | 252 tests passed after the resource-prefix repair. |
| `uv run --project nemweb_foundation --extra test python -m pytest` | 0 | Foundation suite passed in the complete root run; focused rerun reported 252 tests. |
| `uv run --project nemweb_ml python -m pytest nemweb_ml/tests -q` | 0 | Eleven tests passed. |
| root, foundation, and ML `uv build --wheel` | 0 | All three wheels built. |
| `uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_snapshot.py` | 0 | Six archives, 34 files, 103 parsed rows, deterministic SHA-256 maps, and `live_evidence=false`. |
| `python3 nemweb_foundation/scripts/check_modern_pipeline_apis.py` | 0 | Thirty-three pipeline sources passed. |
| foundation `databricks bundle validate --strict -t dev --profile daveok` | 0 | Strict validation passed with snapshot mode and explicit local variables. |
| ML `databricks bundle validate --strict -t dev --profile daveok` | 0 | Strict validation passed; no job ran. |
| AppKit `npm run typecheck`, `npm run lint`, `npm run lint:ast-grep`, `npm test`, and `npm run build` | 0 | Type check and both linters passed; nine tests passed; client and server built. |
| `npx playwright test` | 0 | One prepared-data smoke test passed with selectors matching the rendered UI. |
| `databricks apps validate --profile daveok` with local bundle variables | 0 | All AppKit validation checks passed. |
| `git diff --check` | 0 | No whitespace errors before evidence authoring. |

AppKit 0.57.0 was scaffolded from the live manifest with `analytics`, `lakebase`, and required `server` plugins, using `--run none`. Type generation produced the checked-in query registry. The integration query result remained degraded until a successful deployed table describe could run; no hand-written result type replaced it.

## Foundation snapshot and context result

The local deterministic snapshot passed as recorded above. The isolated context lander task completed successfully and wrote the registration raw archive, parsed registration checksum directory, and a run manifest beneath the new snapshot Volume.

Context orchestration run `707928059480319` started with `nemweb_mode=snapshot` and `allow_live_nemweb=false`. Its lander task succeeded. Exact pipeline update `3ee4b343-14a2-4652-a5f7-603cf390fc81` was identified by creation time and job cause. Inspection showed that the pipeline identity had historical updates predating this goal, so the orchestration and exact update were cancelled. The update reported `full_refresh=false` and terminal state `CANCELED`.

Because publication did not complete, registration Bronze counts, facility-dimension region/fuel ratios, duplicate checks, expectations, Gold subjects, and source/Bronze/Silver/Gold watermarks were not claimed.

## App result

Mock and integration modes share `RegionStatus` and repository contracts. The app renders loading, empty, error, partial, stale, and populated states, shows units/source/freshness, and labels constraint and interconnector values as market-wide with AEMO source sign and no inferred regional allocation. Investigation SQL uses bind parameters and trusted forwarded identity. Local build, unit tests, smoke test, and `apps validate` passed.

App deployment did not run after the Databricks stop condition. No app service principal or application-owned `app_write` schema was created, and no integration UI smoke test was claimed.

## Synced table and LTAP result

The Lakebase project and branch are isolated and PostgreSQL 17 passed. `databricks postgres create-synced-table -h` confirmed the current Autoscaling API. LTAP Direct Writes requires the workspace Beta preview; its enabled state was not available through the checked CLI surface, so no acceleration claim was made.

The source serving table was not published because the context pipeline stopped. Therefore no Triggered synced table, initial load, incremental insert/update/delete reconciliation, sync status, or app read was created or claimed. The checked-in renderer and verifiers remain dry-run/offline tools.

## Lakebase CDF and Lakeflow result

The CLI exposes the Beta `create-cdf-config` and list operations, the new Lakebase project runs PostgreSQL 17, and the dedicated destination uses explicit managed storage. Live CDF setup still requires the app service principal to create and own `app_write.investigations` first. The app was not deployed after the stop condition, so the source table, CDF configuration, committed LSN, insert/update/delete history, and live Lakeflow current-state reconciliation do not exist.

Offline fixtures prove insert, matched update preimage/postimage, delete, duplicate replay, integer or PostgreSQL LSN ordering, and schema re-snapshot behaviour. The Lakeflow source preserves `_pg_change_type`, `_pg_lsn`, `_pg_xid`, `_timestamp`, and `_sort_by`, and does not enable Delta CDF, a row filter, or a column mask on generated history.

## ML and MLOps result

The public `feat/nem-history-analytics` branch supplies backfill code, but this task did not establish a checked-in, attributed training corpus with complete chronological intervals and acceptable class balance. The six-archive workshop snapshot is explicitly too small. Training, MLflow execution, Unity Catalog model registration, `@challenger`, and batch scoring therefore stopped by design. No `@prod` alias or Model Serving endpoint was created.

The checked-in starter still proves chronological split, leakage, schema, stale/missing feature, idempotent score-key, registry URI, candidate alias, and batch-output contracts with prepared fixtures.

## Failures and repairs

1. The first full bundle deployment refused a destructive Volume/dashboard plan; no automatic approval was used.
2. A selected deployment then revealed that ignored `.databricks` state had moved with the renamed directory and rebound the new source to an existing pipeline identity.
3. The exact update was cancelled. No destructive or full refresh ran.
4. The ignored `nemweb_foundation/.databricks/` directory was removed locally so it cannot be reused in a later run. A fresh clone is unaffected because deployment state is ignored.
5. Further Databricks mutation stopped. Restoring or replacing the pre-existing pipeline needs a separate operator decision because this goal did not authorise another change to it.
6. An unqualified follow-up `git push` selected the configured public remote and was rejected by GitHub push protection before changing that repository. Retrying with the explicit private `origin` remote succeeded.

## Reviewer findings

The independent security/data reviewer found no critical or high defect. One medium finding noted that `x-forwarded-user` is trustworthy only behind the Databricks Apps proxy. The app now requires the platform-injected `DATABRICKS_APP_NAME` before accepting forwarded identity, documents that direct local integration is not an authentication boundary, and tests forged-header rejection without that runtime marker.

The reviewer also raised four low findings. Update pairing now balances preimages and postimages by row key and transaction rather than assuming a shared LSN, with a differing-LSN test. Client-facing database failures now use generic messages, and update/delete route IDs are validated as UUIDs. CDF metadata remains in the Silver current-state product deliberately because the issue requires `_pg_change_type`, `_pg_lsn`, `_pg_xid`, `_timestamp`, and `_sort_by` to be preserved; the application does not expose those fields.

The final verification adjudicator found no remaining repository blocker and accepted the repository deliverables as a partial result. It confirmed that PR #23 may close repository-only issue #4, but must only advance #3, #11, #21, and #22. It rejected any full integration claim until a new pipeline identity, synced-table/CDF reconciliation, deployed app smoke test, and operator decision about the modified pre-existing pipeline are available.

## Schedules and pull request

Read-only inspection found both run-specific recurring jobs `PAUSED`; lander and semantic jobs have no schedule. The two visible pipeline definitions were `IDLE` after cancellation. Pull request: https://github.com/dgokeeffe/agentic-energy-on-databricks/pull/23. It uses `Closes #4` and advances #3, #11, #21, and #22 without claiming their incomplete workspace checks.

## Remaining platform limitations

- The pre-existing pipeline identity collision prevents further Databricks deployment in this goal without a new, independently confirmed deployment state and an operator decision about the modified existing resources.
- App deployment, Triggered sync, LTAP Direct Writes confirmation, CDF, live investigation changes, Lakeflow current state, and SQL reconciliation remain unproven.
- Historical training data provenance and interval completeness remain insufficient for ML execution.
