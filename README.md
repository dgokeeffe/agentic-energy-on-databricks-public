# Agentic Energy on Databricks

A metadata-driven energy data foundation and workshop exercise for Databricks.
The repository contains a deterministic local Bronze → Silver → Quarantine →
Gold ETL runner, an installable Python package, and a direct-engine Databricks
Asset Bundle for an optional serverless deployment.

The repository is designed to be useful for workshop participants without
requiring access to a particular tenant, workspace, account, or private
operator configuration.

## Local quick start

Requires Python 3.10+ and `uv`.

```bash
uv run --extra test python -m pytest
uv run python -m agentic_energy.cli --output output
```

The local fixture run requires no Databricks workspace, credentials, network,
or live source access. It produces deterministic JSONL artifacts under
`output/`:

- `bronze/` — immutable raw records and lineage
- `silver/` — typed, timezone-normalized, deduplicated records
- `quarantine/` — rejected records with reason codes
- `gold/` — market/weather projection
- `manifest.json` — counts, source IDs, metadata hash, and reconciliation evidence

For the layer schemas, the per-record lineage of every fixture row, quarantine
reason codes, and the reconciliation equations, see
[`docs/data-lineage.md`](docs/data-lineage.md).

The optional live command requires explicit source-use and network approval:

```bash
uv run python -m agentic_energy.cli \
  --metadata agentic_energy/resources/metadata/sources.live.json \
  --mode live \
  --output output/live
```

## Participant Beads

Workshop work is tracked with Beads. Bootstrap the participant issue graph
from a clean clone:

```bash
scripts/bootstrap-participant-beads.sh
bd ready
```

The public participant graph contains workshop tasks and bounded seeded defects.
Organizer-only solution notes, tenant preflight evidence, and private deployment
records are intentionally not part of this repository. The organizer can set
`BEADS_DOLT_REMOTE` during bootstrap to seed and synchronize a shared public
Dolt remote; otherwise the script uses the repository's configured origin.

## Databricks deployment

The framework is a normal installable Python project. The DAB deploys the
wheel as one serverless Python Job using the Databricks direct deployment
engine. The core ETL path does not require a Lakeflow Declarative Pipeline.

```bash
uv build --wheel --out-dir dist
./scripts/deploy.sh dev
```

Deployment requires an authorized workspace, a pre-created Unity Catalog
catalog/schema/Volume, and configured service-principal/group variables. See
[`docs/deployment.md`](docs/deployment.md) for the deployment contract and
facilitator process.

## Architecture

- `agentic_energy/` — packaged metadata-driven acquisition and ETL framework
- `resources/` — DAB resources and idempotent Lakebase schema artifact
- `tests/` — deterministic local contract tests
- `docs/` — participant architecture, acceptance, and deployment guidance
  ([`data-lineage.md`](docs/data-lineage.md) documents the layer contracts)
- `.beads/` — public participant Beads bootstrap/configuration only

The current package supports the deterministic market/weather MVP. Broader
source/parser registry generalization and an optional Databricks App control
plane are follow-on workshop extensions.

## License

This repository is distributed under the
[Agentic Energy Workshop Public Evaluation License](LICENSE). It is intended
for educational, workshop, research, and evaluation use; production or
commercial use requires separate permission.
