# NEM regional operations AppKit starter

This is an AppKit 0.57.0 TypeScript and React scaffold generated with the
manifest-derived `analytics`, `lakebase`, and required `server` plugins. The
Analytics resource key is `sql-warehouse`; the Lakebase Autoscaling resource
key is `postgres`. The scaffold command used `--run none`.

Local participant commands use the Vite-only prepared mock mode and do not initialise AppKit server resources or contact Databricks.
The deployed build defaults to integration mode. Both use the same
`RegionStatusRepository` and `RegionStatus` domain contract. Set
`VITE_DATA_MODE=mock` for local fixture work. Integration mode uses the
run-specific regular Delta table named in the reviewed
`config/queries/latest_region_status.sql`; callers cannot choose another object.
That SQL file is the only warehouse read path, and there is no custom warehouse
proxy endpoint.

Real warehouse, Lakebase project/branch/database, endpoint, host, and workspace
values belong in ignored `.env` files or bundle variables. Do not add them to
Git. Investigation identity comes from the platform-provided
`x-forwarded-user` request context and is never accepted from request JSON.
Every Postgres value is a bind parameter. Integration mode is supported only behind the Databricks Apps proxy: the server rejects trusted identity when `DATABRICKS_APP_NAME` is absent, and direct local integration access is not an authentication boundary.

## Participant ticket entry points

| Issue                     | Start with                                                                                     | Named deterministic checks                                                                   |
| ------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| #12 regional operations   | `config/queries/latest_region_status.sql`, `client/src/components/RegionalOperationsShell.tsx` | `RegionalOperationsShell.test.tsx`, `regionStatusRepository.test.ts`                         |
| #13 investigation journal | `server/db/schema.ts`, `server/db/investigations.ts`, `InvestigationPanel.tsx`                 | `server/db/investigations.test.ts`, `workshop/lakebase/tests/test_migrations.py`             |
| #14 governed Genie        | `nemweb_foundation/genie/nemweb_space.json`, `server/server.ts`                                | `nemweb_foundation/tests/nemweb/test_genie_assets.py`; add app tests with the implementation |
| #18 integrated journey    | the #12–#14 files plus `nemweb_ml/sql/gold_nem_predictions.sql`                                | `tests/smoke.spec.ts` and the ticket-specific suites above                                   |

```bash
npm ci --include=dev
npm run typegen
npm run typecheck
npm run test -- --run
npm run build
npm run smoke:install
npm run test:smoke
```

The fixture and screenshots are prepared, non-live evidence. Market-wide
binding-constraint and AEMO source-sign interconnector totals are repeated on
regional rows. There is no governed regional allocation or inferred flow
direction, so never sum these values across regions.
