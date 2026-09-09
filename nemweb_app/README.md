# NEM regional operations AppKit starter

This is an AppKit 0.57.0 TypeScript and React scaffold generated with the
manifest-derived `analytics`, `lakebase`, and required `server` plugins. The
Analytics resource key is `sql-warehouse`; the Lakebase Autoscaling resource
key is `postgres`. The scaffold command used `--run none`.

Local participant commands use the Vite-only prepared mock mode and do not initialise AppKit server resources or contact Databricks.
The deployed build defaults to integration mode. Both use the same
`RegionStatusRepository` and `RegionStatus` domain contract. Set
`VITE_DATA_MODE=mock` for local fixture work. Integration mode uses the
run-specific regular Delta tables named in the reviewed
`config/queries/latest_region_status.sql` and
`config/queries/latest_fuel_generation.sql`; callers cannot choose another object.
Those two SQL files are the only warehouse read paths, and there is no custom
warehouse proxy endpoint.

Real warehouse, Lakebase project/branch/database, endpoint, host, and workspace
values belong in ignored `.env` files or bundle variables. Do not add them to
Git. Investigation identity comes from the platform-provided
`x-forwarded-user` request context and is never accepted from request JSON.
Every Postgres value is a bind parameter. Integration mode is supported only behind the Databricks Apps proxy: the server rejects trusted identity when `DATABRICKS_APP_NAME` is absent, and direct local integration access is not an authentication boundary.

## Participant ticket entry points

Issue numbers below are for this repository. They were renumbered when the
exercises were migrated from the private `agentic-energy-on-databricks` repository,
which shares no Git history with this one. Check `gh issue list --label
workshop-ready` rather than trusting a number quoted in prose.

| Issue                     | Start with                                                                                                                    | Named deterministic checks                                                                   |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| #7 attribution freshness  | `client/src/components/SourceFreshness.tsx`, `config/queries/latest_fuel_generation.sql`                                      | `RegionalOperationsShell.test.tsx`, `fuelCapture.test.ts`                                    |
| value capture             | `config/queries/latest_fuel_generation.sql`, `client/src/domain/fuelCapture.ts`, `client/src/components/FuelValueCapture.tsx` | `fuelCapture.test.ts`, `RegionalOperationsShell.test.tsx`                                    |
| investigation journal     | `server/db/schema.ts`, `server/db/investigations.ts`, `InvestigationPanel.tsx`                                                | `server/db/investigations.test.ts`, `workshop/lakebase/tests/test_migrations.py`             |
| governed Genie            | `nemweb_foundation/genie/nemweb_space.json`, `server/server.ts`                                                               | `nemweb_foundation/tests/nemweb/test_genie_assets.py`; add app tests with the implementation |
| integrated journey        | the rows above plus `nemweb_ml/sql/gold_nem_predictions.sql`                                                                   | `tests/smoke.spec.ts` and the suites above                                                   |

The last three rows have no issue in this repository. They existed as advanced,
not-yet-rehearsed tickets in the private repository and were not migrated; the
files remain the correct entry points if a facilitator raises them here.

```bash
npm ci --include=dev
npm run typegen
npm run typecheck
npm run test -- --run
npm run build
npm run smoke:install
npm run test:smoke
```

The fixture and screenshots are prepared, non-live evidence. The screen includes
per-fuel capture bars, a region control, compact section navigation, and a
side-panel investigation journal.

Market-wide binding-constraint and AEMO source-sign interconnector totals are
repeated on regional rows. There is no governed regional allocation or inferred
flow direction, so never sum these values across regions.

## Purpose

The screen answers **"where did the value go?"** for a portfolio analyst or asset
performance team: how much of the regional price each fuel captured, what the
negative-price intervals cost, and why the figure changes when AEMO re-runs a
dispatch interval. The rationale, the market context, and the discarded
alternatives are in
[`miniwiki/decisions/app-value-capture-redesign.md`](../miniwiki/decisions/app-value-capture-redesign.md).

Capture rate is the volume-weighted price a fuel received divided by the region's
time-weighted price. `client/src/domain/fuelCapture.ts` withholds it rather than
printing a misleading number in three cases: zero energy, a regional
time-weighted price at or below zero (dividing inverts the sign and shows loss as
outperformance), and net consumption (a battery buying cheaply is a good outcome
that the ratio would score as the worst on the page).

### Boundaries stated on screen

- **Curtailment is not derivable.** AEMO Current publishes no five-minute
  availability, so only output that ran and the price it earned can be shown.
  A capture screen invites the curtailment reading, so the denial is on the page
  and asserted in `tests/test_repository_layout.py`.
- **Revenue is indicative energy value, not settlement.** Five-minute SCADA output
  at the regional reference price, excluding FCAS, loss factors, contracts, and
  settlement adjustment.
- Not for bid or offer decisions, live market operation, or availability
  inference.

## Theme

Adapted from [Open Electricity](https://github.com/opennem/openelectricity)
(MIT, © 2023-2026 Open Electricity): the warm-neutral palette, the
fuel-technology colour system, and the 10px-root rem scale. Attribution is in the
app footer. Open Electricity self-hosts DM Sans, Space Grotesk, and DM Mono; this
app ships **no font binaries and makes no third-party font request**, so the
stacks fall back to system faces.

The palette is **light only**. AppKit ships
`@media (prefers-color-scheme: dark) { :root:not(.light) { … } }`, which outranks a
bare `:root` and rendered the theme as near-black with unreadable text for any
reviewer whose OS was in dark mode. `client/index.html` sets `class="light"` to
opt out, `index.css` repeats the tokens at matching specificity as a fallback, and
`tests/smoke.spec.ts` asserts the result under an emulated dark colour scheme.

The fuel tokens are a display vocabulary, not a data contract. AEMO's
`CO2E_ENERGY_SOURCE` cannot distinguish CCGT from OCGT, so all gas maps to one
token instead of guessing turbine technology, and unmapped fuels become
`unknown` rather than being force-fitted to the nearest colour.

The previous AGL-inspired blue theme was retired with this redesign, which also
removes the trademark-adjacent risk it carried.

## Frontend trade-offs and follow-up

The redesign replaced the AppKit `LineChart` with CSS capture bars, which removed
the framework's ECharts runtime from the initial bundle. The main JavaScript asset
measured approximately **479 kB uncompressed and 141 kB gzip**, down from 1,106 kB
and 357 kB. Re-measure before reintroducing a charting component.

**Open dependency.** Fuel capture needs `SELECT` on
`gold_nem_scada_generation_5min` in the app serving schema, declared as a second
`uc_securable` in `databricks.yml`. Until a facilitator publishes that table and
grants it, integration mode reports the generation read as unavailable and the
value-capture section degrades while price and freshness reporting continue.
Fuel capture is currently proven only against the prepared local fixture.

Investigation creation is not yet idempotent across an uncertain network retry.
The investigation journal's database/API contract owns that problem; this UI
prevents no server-side duplicate by itself.
