# Agentic Energy on Databricks

A shared NEMWEB baseline for energy application labs:

**NEMWEB → Lakeflow → Delta serving tables → Lakebase synced tables → App**

One root bundle deploys the same source to `dev` and `lab`. The baseline includes regional price and demand, constraints and interconnectors, SCADA generation, registration enrichment, fuel charts, a generator map, and native investigation notes. Initial supply, ML, Genie, and lab solutions are subsequent work.

## Local setup

Install Python 3.10+, uv, Node.js 22+, and Databricks CLI 1.16.1 or newer.

```sh
make setup
make check
npm --prefix app run test:smoke
```

Browser smoke tests use installed Google Chrome locally. CI installs Chromium. For a fixture-only preview, run `VITE_DATA_MODE=mock npm --prefix app run build:client`, then `cd app && npx vite preview --config client/vite.config.ts`. The prepared fixture is explicitly non-live. Native writes require the deployed Lakebase application.

## Layout

- `databricks.yml`, `resources/`: deployment configuration and Lakebase sync templates.
- `src/agentic_energy/`: ingestion, Bronze, Silver, Gold, common helpers, and serving SQL.
- `app/`: React/Node application and its unit/browser tests.
- `tests/`: Python unit tests, integration contracts, and immutable fixtures.
- `scripts/`: setup, validation, landing entrypoint, and sync inspection.
- `docs/`: [architecture](docs/architecture.md), [data contracts](docs/data-contracts.md), and [operations](docs/operations.md).

## Deploy an isolated baseline

Choose a CLI profile explicitly. Configure private values in `.databricks/bundle/<target>/variable-overrides.json` or `BUNDLE_VAR_*` environment variables, as described in [operations](docs/operations.md).

```sh
make provision PROFILE=<chosen-profile> CATALOG=<existing-catalog> DEPLOYMENT_ID=<unique-id> TARGET=dev
make validate PROFILE=<chosen-profile> TARGET=dev
make deploy PROFILE=<chosen-profile> TARGET=dev
make refresh PROFILE=<chosen-profile> TARGET=dev
make publish PROFILE=<chosen-profile> TARGET=dev
# Create/refresh and verify the three Lakebase syncs, then deploy the app:
make app-deploy PROFILE=<chosen-profile> TARGET=dev
```

Both targets deploy with paused schedules. `lab` uses production deployment mode and requires an explicit runtime service principal. The warehouse serves publication jobs; the app reads only Lakebase. Existing deployments are separate from the new bundle state and are not deleted by this refactor.

The accepted baseline is tagged `baseline-v1` after isolated workspace rehearsal and review. Start each lab from that tag, keeping solutions on separate branches:

```sh
git switch -c lab/<lab-name> baseline-v1
```

Merging baseline maintenance does not deploy lab environments automatically. See [operations](docs/operations.md) for verification results and the release gate.

Original code is MIT licensed; adapted material has additional terms. Source attribution and data conditions are in [NOTICE.md](NOTICE.md) and [DATA_LICENSES.md](DATA_LICENSES.md).
