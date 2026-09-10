# Governed NEMWEB analytics on Databricks

This repository contains a governed Australian Energy Market Operator (AEMO)
NEMWEB workflow, an AppKit operations application, a leakage-safe ML starter,
and Lakebase contracts.

The primary runtime is a parameterised Databricks Asset Bundle:

```text
restricted Current/MMSDM landing Volume
  → Lakeflow Bronze (append-only source versions)
  → correction-aware Silver
  → five-minute Gold
  → metric views → Genie → AI/BI dashboard
```

Curated Gold subjects include regional dispatch price and demand, unit and
facility output, SCADA generation by region and fuel, binding dispatch
constraints, and interconnector flows. AEMO Current does not publish
five-minute unit availability. Near-real-time unit output is therefore SCADA
`actual_generation_mw`; authoritative target and availability come from the
daily Next_Day_Dispatch product at T+1.

## Repository layout

```text
nemweb_foundation/   governed NEMWEB implementation, contracts, and tests
nemweb_app/          AppKit regional-operations application
nemweb_ml/           leakage-safe ML and MLflow starter
workshop/lakebase/   Lakebase CDF and migration contracts
scripts/             local utility scripts
miniwiki/            optional Markdown notes
```

## Setup

Requires Python 3.10+, `uv`, Node.js, and npm.

```bash
make setup
```

Authentication is not automated. Configure the Databricks CLI separately when
workspace validation is required.

## Local development

Fast workspace-free checks:

```bash
make validate-fast
```

The complete local build and application smoke-test gate is available when
needed:

```bash
make validate-local
```

Useful focused commands:

```bash
make test
make foundation-test
make ml-test
make lakebase-test
make app-install
make app-test
```

The app can run locally against mock data:

```bash
make app-dev-mock
```

## Databricks validation

Workspace commands require an explicitly named CLI profile. Choose a bundle
target; there is no `.env`. `dev` and `live_evidence` create the SQL warehouse,
UC schemas, MLflow experiment and registered model from the authenticated
identity. The app still needs `--var attendee_slug=...` and
`--var lakebase_project_id=...`.

```bash
make bundle-validate PROFILE=<your-profile>
```

The bundles contain paused schedules. Do not enable schedules or live NEMWEB
access without confirming the target, identity, configuration, and required
approval. Snapshot data is prepared evidence and must not be represented as live
evidence.

The authoritative NEMWEB scripts are under
`nemweb_foundation/scripts/`, including snapshot, evidence, landing, Genie, and
live-cycle validation utilities. They are ordinary executable programs; no
agent skill or prompt pack is required to use them.

## Data contracts

- Market intervals use fixed AEST (UTC+10, without daylight saving).
- Processing, publication, landing, and lineage timestamps are UTC instants.
- Bronze retains source corrections; Silver selects the latest valid correction.
- Gold retains intervention rows and ordinary analysis uses `is_effective_run`.
- Snapshot and prepared fixtures are non-live evidence.
- AEMO data attribution and adapted-source notices are in
  [`DATA_LICENSES.md`](DATA_LICENSES.md) and [`NOTICE.md`](NOTICE.md).

## Validation scripts

The implementation is tested with pytest, the AppKit test/typecheck/build
commands, and the focused NEMWEB snapshot and API checks. Keep credentials,
private workspace URLs, tenant identifiers, and generated deployment state out
of Git.
