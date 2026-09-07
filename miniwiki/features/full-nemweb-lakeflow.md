# Full NEMWEB Lakeflow pipeline

## Intent

Bring the working NEMWEB ingestion and medallion capability from
`~/Repos/australian-energy-nemweb-analytics` into this repository so workshop
participants can use governed Gold data without needing a coding-agent workflow.
The implementation may use dedicated NEMWEB Databricks resources.

The primary value is fresh, understandable market data. Metric views, Genie and
AI/BI dashboards consume that data, but must not distract from making the core
five-minute path reliable. The executable lead-agent brief is
[`../../goal.md`](../../goal.md).

## Finish criterion

The NEMWEB pipeline migration is finished when the main analyst-facing Gold
subjects below are populated from live NEMWEB and continue to incorporate each
new available dispatch interval on a five-minute operating cadence:

1. regional dispatch price and demand;
2. unit/facility dispatch and availability;
3. SCADA generation enriched with region and fuel type;
4. binding dispatch constraints; and
5. interconnector flows.

Completion evidence must show more than a configured schedule. For at least
three consecutive five-minute cycles, record the source interval watermark,
Bronze ingestion time, Gold publication time, row counts, duplicate-key result,
data-quality result, and pipeline/job outcome for each applicable subject. A
source that publishes no changed row in a cycle should still show a successful
freshness check rather than fabricated data.

Bids, registration/facility dimensions, market notices, trading/settlement and
other slower-changing NEMWEB subjects remain important analyst context. They
must refresh at their source-appropriate cadence, but they are not all expected
to produce a new row every five minutes.

This criterion applies to the ingestion and Gold-data milestone. The semantic,
Genie and dashboard work follows from the proven Gold contracts and is tracked
below so the workshop path remains coherent.

## Scope and boundaries

- Adapt relevant source code directly from the reference repository, preserving
  applicable licence and attribution notices.
- Port source files, tests and resource definitions deliberately; do not copy
  generated wheels, `.databricks` state, logs, coverage output or built assets.
- Use modern `pyspark.pipelines` APIs. Migrate remaining legacy `dp.read` or DLT
  forms instead of extending them.
- Support both a deterministic, versioned workshop snapshot and live NEMWEB.
- Use the explicit Databricks profile `daveok` for workspace-aware validation.
- The NEMWEB delivery includes medallion data, metric views, semantic metadata,
  Genie instructions/examples/evaluation and AI/BI dashboards. ML forecasting
  and the custom application are outside this migration.
- Non-NEMWEB sources such as BOM, ABS, CER and OpenElectricity are not part of
  the critical ingestion path unless a separately recorded analyst requirement
  needs them.

## Ordered work

Tasks are ordered by dependency and by the five-minute Gold finish criterion.
A later task must not be used to hide missing evidence from an earlier one.

### 1. Migration manifest and provenance

- Enumerate every reference NEMWEB lander, parser, schema, Bronze, Silver, Gold,
  check and test file.
- Classify each as critical five-minute path, slower analyst context, disabled or
  generated artifact.
- Map the selected files and dependencies to destination paths in this bundle.
- Record licence/NOTICE and AEMO attribution requirements.
- Identify and replace legacy API usage and known disabled-table failure modes.

**Exit evidence:** reviewed file/table manifest with no unexplained dependency.

### 2. Bundle and landing foundation

- Add parameterised catalog, schema and UC Volume configuration.
- Add the NEMWEB file lander and Lakeflow pipeline resources to the existing
  Declarative Automation Bundle.
- Preserve single-writer/idempotent landing behavior, bounded polling, archive
  lookback configuration and correction/supersession handling.
- Add a triggered or continuously orchestrated path capable of a five-minute
  end-to-end cycle; do not rely on the deprecated pipeline continuous setting.

**Exit evidence:** strict bundle validation succeeds and resource dependencies
resolve without deploying generated artifacts.

### 3. Deterministic snapshot path

- Check in or generate a small attributed NEMWEB snapshot covering every
  critical report family and important malformed/correction cases.
- Make the same parser and medallion transformations runnable against snapshot
  and live landing modes.
- Add tests for ZIP/CSV sections, report versions, schema drift, duplicate files,
  corrections, malformed rows, timezones and natural keys.

**Exit evidence:** repeatable tests produce identical critical Gold results.

### 4. Critical Bronze ingestion

Land and type the report families required for regional dispatch prices/demand,
unit dispatch, SCADA generation, constraints, interconnectors and facility
classification. Retain source file, report/version and ingestion metadata.

**Exit evidence:** incremental/idempotent Bronze tables reconcile to landed
records and expose schema drift rather than silently losing columns.

### 5. Critical Silver contracts

- Deduplicate using report-specific natural keys and latest valid correction.
- Normalize types, units, intervention flags and NEM market-time semantics.
- Join registration/facility dimensions without losing unknown DUIDs.
- Quarantine or report invalid data with measurable expectations.

**Exit evidence:** contract tests cover duplicates, corrections, missing joins,
negative prices, nulls, interventions and interval boundaries.

### 6. Five-minute Gold subjects

Publish narrow analyst-facing Gold tables or views for the five critical
subjects in the finish criterion. Preserve dispatch interval, region, DUID or
interconnector identifiers and other dimensions needed by filters; do not expose
only 30-minute/daily aggregates. Keep derived 30-minute and daily products as
additional views.

**Exit evidence:** Gold contracts, comments and reconciliation tests pass on the
snapshot path.

### 7. Five-minute live proof

- Facilitators validate from `nemweb_foundation/` with `databricks bundle validate --strict -t dev --profile daveok`.
- Exercise the lander, pipeline dependencies, retries and correction path in the
  selected workspace environment.
- Capture at least three consecutive cycles using the finish-criterion evidence.
- Verify actual source-to-Gold watermarks and queryable rows, not merely green
  resource status.

**Exit evidence:** the finish criterion is demonstrated for every applicable
critical Gold subject, with residual source-publication lag stated explicitly.

### 8. Broader NEMWEB analyst context

Port and validate the useful slower-changing NEMWEB domains, including bids,
registration/facilities, trading/settlement and market notices. Add other
reference NEMWEB domains only when their source and dependencies are working and
an analyst question justifies them.

**Exit evidence:** each included table has a source contract, expected cadence,
quality checks and an analyst-facing purpose.

### 9. Governed semantic layer

Add concise Gold comments, relationships and metric views for prices, demand,
generation, constraints, interconnector flow and bid context. Define units,
signs, dispatch versus settlement grain, intervention handling, timezone and
freshness in the assets themselves.

**Exit evidence:** representative metric-view SQL returns reconciled results and
all dashboard/Genie queries use governed definitions.

### 10. Genie and AI/BI workflow

- Curate a small set of Gold/metric views for the analyst rather than exposing
  the entire medallion model.
- Add Genie instructions, SQL expressions, example SQL and benchmark questions.
- Add automated answer/SQL checks for common workshop questions.
- Build an AI/BI dashboard from tested SQL and link the Genie experience.

**Exit evidence:** benchmark questions produce correct, explainable SQL/results,
and dashboard queries are tested against the target schema before publication.

## Current evidence and risks

Repository implementation is now present for the bounded lander/parser,
append-only Bronze, correction-aware Silver, all five five-minute Gold subjects,
daily T+1 target/availability, slower bids/trading/settlement context, metric
views, Genie benchmarks and the linked AI/BI dashboard. Pipeline sources use
modern `pyspark.pipelines`; disabled reference libraries were not claimed as
working. The versioned snapshot includes two consecutive synthetic five-minute
intervals and attributed MMSDM registration excerpts, but remains explicitly
not live evidence.

Operations tooling now records the exact pipeline update ID, nested pipeline
exceptions, live source-listing publication, raw checksum, medallion watermarks
and counts, Gold lag, duplicate keys, expectation metrics and job outcomes for
each subject/cycle. It fails closed when quality metrics are absent and permits
a no-new-source cycle only when the current listing is unchanged and Bronze is
fresh. This prevents a configured schedule or green resource state from being
used as cadence proof.

## Completion handoff — 5 September 2026

The workspace, semantic, dashboard, Genie, and live cadence gates are complete.
A dedicated `live_evidence` target uses `daveok.agentic_energy_workshop_d4_live`
for independent tables and checkpoints while reading the run-owned Volume's
`live/` sibling. Live context run `461147691889245` materialised registration
and other dependencies without a full refresh. The accepted scheduled runs were
`565631466192420`, `486920185849915`, and `932668204944509`; their starts are
approximately 300 seconds apart, and all lander, exact pipeline update, quality,
duplicate-key, watermark, and orchestration checks passed.

The authoritative evidence is
[`../../docs/test-evidence/nemweb-e2e-2026-09-05.md`](../../docs/test-evidence/nemweb-e2e-2026-09-05.md).
`validate_nemweb_live.py` accepted three cycles and 15 critical-subject rows.
Both the ordinary development schedule and the live-evidence schedule are
paused. AEMO Current still does not contain unit target or availability:
`gold_nem_unit_dispatch_5min` exposes SCADA actual MW, while
`gold_nem_unit_dispatch_availability_t1` remains the separately labelled daily
T+1 product. Market notices remain omitted because the source is unstructured
text and still lacks the parser and fixture proof required here.

Next: a human reviews PR #23 and the disclosed AppKit dependency audit findings.
Do not merge or unpause either schedule as part of this handoff.
