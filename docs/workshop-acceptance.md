# Agentic Energy Data Workshop — acceptance contract

## Purpose

The workshop uses real NEMWEB market data to teach two different skills on the
same governed foundation:

1. **Business value discovery:** turn energy-market data into a metric view, a
   scoped Genie Agent, a Genie One analysis, and one approved MCP with a recorded
   access boundary.
2. **Metadata-driven engineering:** maintain one ingestion pipeline through
   Silver while adding or changing sources through metadata rather than source-
   specific orchestration code.

Both tracks consume the same run, source lineage, freshness markers, and data
quality evidence. Neither track creates a parallel data store. Section one begins
in Omnigent for both tracks: product participants research NEMWEB and refine an
evidence-backed Beads requirement with their paired engineering group before
implementation starts.

## Shared foundation outcome

The scored baseline is the deterministic local profile. It reads versioned
metadata from the repository, validates before side effects, runs checked-in
fixtures through the generic worker, and publishes Bronze, Quarantine, Silver,
Gold, lineage, freshness, and manifest evidence.

A live NEMWEB path may extend that baseline within its documented network and
size bounds. A Databricks deployment may instead read a versioned Lakebase
metadata snapshot, run the same generic contract on serverless compute, and
expose governed Silver/Gold data to Genie One—but only after the workspace,
identity, storage, connector, and permission preflights pass. Neither extension
is required to score the core exercise.

The common acceptance gate is a reconciled run manifest or equivalent evidence
bundle. Per source, it must show:

```text
source definitions read = source definitions selected
Bronze input rows       = accepted rows + quarantined rows
accepted rows           = Silver rows + rows removed by declared deduplication
Silver keys             = unique by declared natural key
Silver timestamps       = normalized using declared source timezone
identical replay        = unchanged output keys and layer counts
run status              = success only after all selected sources complete
```

If the current local manifest does not yet emit every named counter, attach the
focused deterministic test output that proves the missing equation. Do not mark
the deployment extension complete from fixture evidence alone.

## Track A — business value discovery

### Stage A1: Brief

Participants begin in Omnigent with their paired engineering group and choose an
energy-market decision, not a technology feature. Before engineering dispatches,
they turn the research into an approved Beads requirement. The brief must state:

- the audience and decision owner;
- the operational or commercial question;
- the expected value if the question is answered;
- the NEMWEB fields and time grain needed;
- the measures and dimensions the metric view must expose;
- the intended Genie Agent scope and MCP access boundary; and
- the evidence that would change the decision.

**Output:** a one-page question brief with a measurable value hypothesis.

### Stage A2: Research

During section one, participants research NEMWEB in Omnigent and attach the
baseline, freshness, uncertainty, and evidence to the Beads requirement. During
section two, they create a metric view, ground a Genie Agent in it, use the agent
in Genie One, and add one approved MCP. They record:

- source references, the Genie Agent scope, and the MCP access boundary;
- metric definitions and assumptions;
- time-window and region choices;
- data freshness and known gaps; and
- competing explanations or missing context.

**Output:** an approved Beads requirement plus a research log with citations,
source freshness, and unresolved questions. It is not sufficient to provide an
uncited answer or a chart without an interpretation.

### Stage A3: Analysis

Participants use Genie One through the scoped Genie Agent, metric view, and
approved MCP, or the prepared fallback transcript, to analyse NEMWEB-derived
tables. They then build an AI/BI dashboard or Databricks App from the metric view,
create Genie Agent benchmark cases, and try a Genie One skill. Analysis should
include:

- the query or analytical method;
- the observed pattern and its uncertainty;
- comparison against a baseline or alternative explanation;
- the business implication; and
- a recommended next action or experiment.

**Output:** a dashboard or app showing owner, source, and freshness; Genie Agent
benchmark cases; a recorded Genie One skill result, refusal, or fallback; and a
short decision-ready analysis with links to the research evidence.

### Business scoring signals

| Signal | Evidence |
|---|---|
| Value | Question is tied to a real decision and measurable benefit |
| Research quality | Sources, assumptions, gaps, the metric definitions, and the scoped agent are recorded |
| Analytical reasoning | Pattern is tested against a baseline; correlation is not presented as causation |
| Governance | Answers retain source, freshness, the Genie Agent scope, and the MCP access boundary; live identity propagation is claimed only after preflight |
| Actionability | Recommendation has an owner, next step, and measurable follow-up |

## Track B — metadata-driven engineering

### Stage B1: Understand the contract

Participants inspect the source metadata, the NEMWEB file shape, and the shared
Bronze/Silver invariants. They must identify the source's event timestamp,
timezone, natural key, watermark, parser, quality rules, and provenance before
changing code.

### Stage B2: Add or change metadata

Participants add a source or change source behaviour in versioned repository
metadata, or in Lakebase metadata when that deployment path has passed preflight. They
must not add a new source-specific pipeline, task graph, or hard-coded branch.
The metadata change must include:

- source identity and version;
- acquisition URL or fixture pattern;
- format and compression;
- parser and schema reference;
- timestamp and timezone;
- natural key and watermark;
- quality and quarantine policy;
- target/source provenance; and
- the generic worker/job contract to invoke.

### Stage B3: Run and reconcile

The generic local runner reads and validates versioned metadata for the selected
source set. When the Databricks extension is preflighted, the single dispatcher
reads active Lakebase metadata, creates a versioned snapshot, and invokes the
generic serverless worker. Both paths emit the same Bronze/Silver contract for
every source. Participants
verify row accounting, deduplication, timezone conversion, quarantine, replay,
and idempotency.

### Stage B4: Extend safely

The engineering challenge is passed only when a new source can be added through
metadata plus a registered adapter/parser, without modifying orchestration.
Tests must prove both the new source and the unchanged behavior of existing
sources.

### Engineering scoring signals

| Signal | Evidence |
|---|---|
| Single-pipeline discipline | No per-source workflow or orchestration branch is introduced |
| Metadata completeness | Contract validates and version compatibility is explicit |
| Data correctness | Natural keys, watermarks, timezone, quality, and quarantine reconcile |
| Operational safety | Idempotent retries, bounded inputs, no secret leakage, clear failures |
| Evidence | Run manifest includes metadata version, code/parser version, counts, watermark, freshness, and failure reason |

## Technical architecture invariant

In the target Databricks architecture, Lakebase is the **control plane** for
source metadata. It is not the Bronze landing area and it is not a substitute
for governed Delta tables. The scored baseline uses the versioned repository
metadata with the same source-independent contract.

```text
Lakebase metadata
       │
       ▼
One serverless metadata dispatcher
       │  validates + snapshots metadata
       ├── generic serverless acquisition worker(s)
       └── one generic Bronze → Silver refinement path
                    │
                    ▼
          UC Bronze / Quarantine / Silver
                    │
                    ▼
          Gold projections → Genie One
```

The maintained unit is the dispatcher plus the generic worker/refinement
implementation. Sources are data, not code. A `for_each` task or a Jobs API
invocation may create parallel serverless executions, but every execution uses
the same worker contract and carries the same `run_id` and `metadata_snapshot_id`.

Lakeflow or other declarative refinement may consume the immutable metadata
snapshot written to UC. It should not make an untracked direct call to Lakebase
during planning; the snapshot makes a run reproducible and gives Silver a stable
contract even if metadata changes mid-run.

## Non-goals

- No source-specific pipeline per NEMWEB report.
- No writes back to NEMWEB, SharePoint, or Confluence.
- No copying unrestricted SharePoint or Confluence content into Gold.
- No claim that Genie One can access arbitrary SharePoint or Confluence content
  without the selected connector, identity, and permission preflight.
- No requirement to configure both document systems during the workshop. Select
  one approved source before the day; use a curated cited fallback if it fails.
- No production SLA or automated business decision.
