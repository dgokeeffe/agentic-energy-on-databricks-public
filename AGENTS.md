# Repository instructions

Use the root `databricks.yml`; there are no nested bundles. Keep package identity `agentic-energy-on-databricks` and imports under `agentic_energy`.

Load the Databricks core skill and matching product skills before Databricks work. Require an explicitly selected CLI profile on every authenticated command. Private workspace values belong in ignored `.databricks/bundle/<target>/variable-overrides.json` or environment variables.

Ownership boundaries:
- Ingestion owns immutable archives and append-only landing records.
- One authored serverless pipeline owns Bronze streaming tables, correction-aware Silver MVs, and Gold MVs. Only dataset-definition files are pipeline libraries. Helpers are normal imports; shared temporary views are declared once.
- Serving SQL alone writes regular Delta sources. Use additive, repeatable publication with CDF and stable keys.
- Postgres CLI manages synced tables. Do not introduce deprecated bundle synced-table resources.
- App reads `app_read` through the three fixed API routes and owns native investigations in `app_write`. Never add warehouse reads to the app.

Run `make check`, browser smoke tests for UI changes, and `make validate PROFILE=... TARGET=...` for both configured targets. Local tests do not prove deployed Spark execution or Lakebase readiness. State verification limits accurately.

Preserve fixed AEST market time, UTC processing time, correction ordering, intervention selection, signed battery output, fuel attribution, and independent panel failures. Do not implement initial supply, lab solutions, ML, Genie, or investigation CDC on the baseline.

Do not destroy existing workspace resources as part of repository maintenance. Keep publication, sync verification, and app deployment explicit. Release tags and merges require the reviewed revision and a successful isolated rehearsal; never mark an untested deployment verified.
