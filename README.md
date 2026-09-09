# Governed NEMWEB analytics on Databricks

This repository delivers a governed Australian Energy Market Operator (AEMO)
NEMWEB workflow and a cross-track workshop for analysts and engineers. Workshop
participants start with [`QUICKSTART.md`](QUICKSTART.md); facilitators first
complete [`PRE-REQUISITES.md`](PRE-REQUISITES.md). The participant path works
in Omni Sandbox without a local issue database or tracker CLI.

The implementation's primary runtime is a parameterised Databricks Declarative
Automation Bundle:

```text
restricted Current/MMSDM landing Volume
  → Lakeflow Bronze (append-only source versions)
  → correction-aware Silver
  → five-minute Gold
  → metric views → Genie → AI/BI dashboard
```

The curated Gold subjects are regional dispatch price and demand, unit/facility
actual output, SCADA generation by region and fuel, binding dispatch constraints
and interconnector flows. AEMO Current does **not** publish five-minute unit
availability. The near-real-time unit product is therefore SCADA
`actual_generation_mw`; authoritative target and availability are published
separately from Next_Day_Dispatch at T+1.

A deterministic, versioned and attributed snapshot supports local checks and
reliable demonstrations. Snapshot rows are never live evidence.

## Workshop layout

The workshop uses a hybrid layout that keeps one shared foundation and
one role for each track:

```text
QUICKSTART.md                 participant entry point
PRE-REQUISITES.md             administrator, facilitator, and participant checks
foundation/                   facilitator operations guidance
nemweb_foundation/            governed NEMWEB implementation and contracts
nemweb_app/                   AppKit regional-operations starter
nemweb_ml/                    leakage-safe ML and MLflow starter
workshop/lakebase/            offline LTAP and CDF contracts
.agents/skills/               shared GitHub-issue lifecycle
presentations/                facilitator agenda and deck
```

Facilitator operations guidance is in
[`foundation/`](foundation/Instructions.md). Each cross-functional pair selects
one `workshop-ready` GitHub issue, inspects the governed contracts in
[`nemweb_foundation/`](nemweb_foundation/README.md), and follows the shared
[issue lifecycle](.agents/skills/issue-navigator/SKILL.md). Participants may
inspect the foundation, app, ML, and Lakebase starters, but must not deploy,
provision, change grants, run jobs, enable live data, or change schedules.
Use the current files linked from `QUICKSTART.md` for participant work.

## Local validation and snapshot

Requires Python 3.10+ and `uv`.

```bash
python3 scripts/validate-miniwiki.py
uv run --extra test python -m pytest
rm -rf dist && uv build --wheel --out-dir dist
(
  cd nemweb_foundation
  uv run python scripts/validate_nemweb_snapshot.py
  python3 scripts/check_modern_pipeline_apis.py
  rm -rf dist && uv build --wheel --out-dir dist
)
git diff --check
```

The snapshot validator lands the same six versioned archives into two isolated
roots and compares every relative-path SHA-256. It also reconciles parsed rows
to the immutable manifest. It does not contact or mutate a Databricks
workspace.

## Databricks resources

## Governed foundation

The implementation and operational tools are in
[`nemweb_foundation/`](nemweb_foundation/README.md). Participants inspect its
contracts and tests; deployment and workspace operations remain facilitator-only.

The bundle contains:

- Unity Catalog Volume `nemweb_landing`;
- limited `nemweb_lander` Job;
- serverless `nemweb` Lakeflow pipeline;
- paused five-minute `nemweb_refresh` orchestration;
- paused daily `nemweb_context_refresh` orchestration;
- manual semantic/metric-view SQL Job;
- bundle-managed NEMWEB Genie space and AI/BI dashboard.

Schedules deploy paused. Do not unpause them until snapshot, bundle, pipeline,
SQL, Genie and dashboard gates have passed. Every workspace-aware command must
use the explicitly selected `DEFAULT` profile.

Bundle value placeholders are in [`env.example`](env.example). Facilitators
follow [`PRE-REQUISITES.md`](PRE-REQUISITES.md), copy it to the ignored `.env`
file with `cp -f env.example .env`, replace every placeholder with an approved
non-secret value, and explicitly select `--profile DEFAULT` for validation.
Never rely on an implicit Databricks profile.

Facilitators follow the numbered stages in
[`foundation/Instructions.md`](foundation/Instructions.md). Deployment,
controlled operation, rollback, live SQL validation, and the final three-cycle
evidence gate are in
[`foundation/deployment-gates.md`](foundation/deployment-gates.md). The
authoritative implementation and its bundle are in
[`nemweb_foundation/`](nemweb_foundation/README.md).

## Five-minute evidence

A green resource is not cadence proof. For each scheduled cycle, capture the
exact pipeline update ID and query source, Bronze, Silver and Gold watermarks:

```bash
uv run --project nemweb_foundation python nemweb_foundation/scripts/capture_nemweb_evidence.py \
  --profile DEFAULT \
  --warehouse-id "$BUNDLE_VAR_warehouse_id" \
  --catalog "$BUNDLE_VAR_catalog" \
  --schema "$BUNDLE_VAR_schema" \
  --pipeline-id "$NEMWEB_PIPELINE_ID" \
  --pipeline-update-id "$NEMWEB_UPDATE_ID" \
  --orchestration-run-id "$NEMWEB_JOB_RUN_ID" \
  --output-json /tmp/nemweb-evidence.json \
  --output-markdown /tmp/nemweb-evidence.md
```

Subsequent cycle captures use the same paths and add `--append`. The tool
polls that exact update, extracts underlying pipeline exceptions, checks live
NEMWEB listings, and fails closed on duplicate keys or missing/failed Lakeflow
expectation metrics. After at least three consecutive cycles:

```bash
uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_live.py /tmp/nemweb-evidence.json
```

Copy reviewed, non-sensitive output into a dated
`docs/test-evidence/nemweb-e2e-YYYY-MM-DD.md`. Never include tokens, private
workspace URLs or tenant identifiers.

## Analyst workflow

The semantic layer defines units, AEST interval-ending timestamps, source sign,
freshness, dispatch-versus-settlement grain and intervention handling. Both
intervention rows remain governed, while default metric, Genie and dashboard
queries use `is_effective_run`. Validate all canonical SQL before creating or
updating analyst assets:

```bash
uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_genie.py
uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_genie.py --execute \
  --profile DEFAULT --warehouse-id "$BUNDLE_VAR_warehouse_id" \
  --catalog "$BUNDLE_VAR_catalog" --schema "$BUNDLE_VAR_schema"
```

## Local JSONL compatibility runner

The original market/weather JSONL implementation is retained only for focused
compatibility and fixture tests. It is not the primary runtime and is not a
competing production path. Facilitators only can run it with:

```bash
uv run --project nemweb_foundation agentic-energy-local-fixture --output output/local-fixture
```



## Workshop continuity and licence

Participants start at [`QUICKSTART.md`](QUICKSTART.md) and choose one
self-contained track. Facilitators complete
[`PRE-REQUISITES.md`](PRE-REQUISITES.md) and use
[`foundation/deployment-gates.md`](foundation/deployment-gates.md).
Read the repository-owned
[miniwiki skill](.agents/skills/miniwiki/SKILL.md) and
[`miniwiki/now.md`](miniwiki/now.md), then validate miniwiki links before a
handoff. The skill travels with a fresh clone and requires no machine-level
installation. AEMO data attribution and adapted-source notices are in
[`DATA_LICENSES.md`](DATA_LICENSES.md) and [`NOTICE.md`](NOTICE.md). Repository
use is governed by [`LICENSE`](LICENSE); production or commercial use requires
separate permission.
