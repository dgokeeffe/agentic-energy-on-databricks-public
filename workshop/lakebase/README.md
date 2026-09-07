# Lakebase Autoscaling and CDF starter

This directory contains prepared contracts and dry-run tools for participant issues #13, #19, and #20. Fixtures are labelled non-live. Participants change application or pipeline behaviour; they do not create a Lakebase project, branch, database, synced table, grant, or CDF feed.

## Data ownership

| Object | Writer | Reader |
|---|---|---|
| `gold_nem_app_region_status` regular Delta serving source | Lakehouse publication job | Triggered synced-table pipeline |
| `app_read.nem_region_status_synced` | Managed sync | App, read-only |
| `app_write.investigations` | App | Lakebase CDF |
| `lb_investigations_history` | Lakebase CDF | Lakeflow, immutable |
| `silver_nem_investigations_current` | Lakeflow | Governed analytics |

The serving row repeats market-wide constraint and AEMO source-sign interconnector summaries for each region. There is no governed interconnector-to-region mapping, regional allocation, or inferred flow direction. Never sum the repeated values across regions.

## Participant ticket entry points

| Issue | Start with | Named deterministic checks |
|---|---|---|
| #13 native investigation writes | `migrations/001_app_write_investigations.sql`, `nemweb_app/server/db/investigations.ts` | `tests/test_migrations.py`, `nemweb_app/server/db/investigations.test.ts` |
| #19 Triggered synced read | `synced-table/create-synced-table.json.template`, `scripts/verify-synced-table.py`, `nemweb_foundation/sql/app_serving/gold_nem_app_region_status.sql` | `tests/test_synced_table_contract.py`, `nemweb_foundation/tests/nemweb/test_app_region_status_contract.py` |
| #20 Lakebase CDF current state | `nemweb_foundation/agentic_energy/lakebase_cdf/`, `nemweb_foundation/agentic_energy/nemweb/pipeline/lakebase_investigations.py` | `tests/test_cdf_reducer.py`, `nemweb_foundation/tests/test_lakebase_artifacts.py` |

## Facilitator-only integration

Lakebase CDF is a schema-level Public Preview. Current Databricks CLI releases expose `databricks postgres create-cdf-config`; a facilitator may use it only after the workspace preview, PostgreSQL version, destination storage, and permissions pass [`preflight.md`](preflight.md). The history table must not have Delta CDF, row filters, or column masks. LTAP Direct Writes is a Beta acceleration for initial loads on PostgreSQL 17. Triggered sync remains supported when that preview is unavailable.

The checked-in scripts are dry-run or offline verification tools:

```bash
PROFILE=daveok bash workshop/lakebase/scripts/discover.sh
python3 workshop/lakebase/scripts/render-synced-table-command.py \
  --resources /path/to/non-secret-resources.json --profile daveok
python3 workshop/lakebase/scripts/verify-synced-table.py source.json synced.json
python3 workshop/lakebase/scripts/verify-lakebase-cdf.py \
  workshop/lakebase/fixtures/investigation-cdf.jsonl
uv run --extra test python -m pytest workshop/lakebase/tests -q
```

Changing placeholders to real names, applying SQL, creating a feed, or triggering a sync is facilitator-only. Hosts, credentials, workspace URLs, tokens, tenant IDs, and service-principal IDs stay outside Git.

## Rollback and non-destructive reset

Keep recurring schedules paused. To reset prepared rows, rerun the lakehouse app-serving publication job, trigger the existing synced-table pipeline, remove investigations through the authenticated app API so CDF retains delete history, then rerun the current-state pipeline. Reconcile source and synced keys after each step. This sequence was exercised for the integration insert/update/delete test and does not delete the Lakebase project, branch, database, schemas, tables, CDF feed, or audit history.

For code rollback, deploy the last reviewed commit against the same run-specific resources and use selective, non-full pipeline updates. Preserve the CDF destination and committed LSN. Disabling CDF, deleting a synced table, dropping a schema/table, resetting a branch, or deleting a project requires a separate human decision and is never part of an automated workshop target.
