# Goal: complete the NEMWEB Lakeflow and analyst workflow end to end

## Mission

Act as the lead coding agent and execute the NEMWEB migration described in
[`miniwiki/features/full-nemweb-lakeflow.md`](miniwiki/features/full-nemweb-lakeflow.md)
from repository discovery through tested Databricks operation.

Adapt the relevant implementation directly from:

```text
/Users/david.okeeffe/Repos/australian-energy-nemweb-analytics
```

into:

```text
/Users/david.okeeffe/Repos/agentic-energy-challenge
```

The result must give workshop users governed NEMWEB data, metric definitions,
Genie guidance and an AI/BI dashboard without requiring them to use a coding
agent or the separate omnigent workflow.

Do not stop at scaffolding, copied files, a successful bundle validation, or a
green pipeline status. Work through the evidence required by the completion
criteria below.

## Authoritative completion criteria

This goal is complete only when all required repository deliverables are present
and the live NEMWEB path has demonstrated that newly available dispatch data
reaches the main analyst-facing Gold subjects on a five-minute operating
cadence.

The critical Gold subjects are:

1. regional dispatch price and demand;
2. unit/facility dispatch and availability;
3. SCADA generation enriched with region and fuel type;
4. binding dispatch constraints; and
5. interconnector flows.

At least three consecutive five-minute cycles must be evidenced. For each
applicable subject and cycle, capture:

- newest available NEMWEB source interval;
- Bronze ingestion timestamp or watermark;
- Gold publication timestamp or watermark;
- source-to-Gold lag;
- landed, Bronze, Silver and Gold row counts;
- duplicate-natural-key result;
- data-quality/expectation result; and
- lander, pipeline and orchestration outcome.

A cycle in which AEMO publishes no changed row is valid only when the source
watermark and freshness check prove that there was nothing new to ingest. Never
fabricate rows to make a cadence check pass. Report source publication lag
separately from the pipeline's five-minute processing cadence.

The goal also requires the semantic and workshop assets listed below to exist
and be validated before the final live proof. The five-minute Gold proof is the
final closure gate.

## Fixed decisions

Treat these as decided unless direct repository evidence makes one impossible:

- A dedicated NEMWEB Lakeflow implementation is allowed in this repository.
- Replace the current local JSONL pipeline as the primary runtime rather than
  preserving it as a competing production path.
- Retain a deterministic, versioned and attributed NEMWEB snapshot mode for
  local tests and reliable workshop demonstrations.
- Support live NEMWEB Current reports. Current/archive history and longer MMSDM
  backfill may be added, but historical breadth must not delay the live critical
  path.
- Adapt source code directly where useful, preserving applicable copyright,
  NOTICE and attribution requirements.
- Copy source, tests and resource definitions deliberately. Do not copy
  generated wheels, `.databricks` deployment state, logs, coverage output,
  caches, compiled frontend assets or credentials.
- Use modern `pyspark.pipelines` APIs. Migrate legacy `import dlt`, `dp.read`,
  `dlt.read`, `LIVE.*` and other legacy forms rather than extending them.
- Use the explicitly selected Databricks CLI profile `daveok` for every
  workspace-aware command. Never rely on an implicit/default profile.
- Include governed Gold assets, metric views, table/column semantics, Genie
  instructions and examples, benchmark/evaluation questions, and an AI/BI
  dashboard linked to the Genie experience.
- ML forecasting and the custom application from the reference repository are
  outside scope.
- BOM, ABS, CER, OpenElectricity and other non-NEMWEB feeds are outside the
  critical path unless a recorded analyst requirement proves they are needed.

## Required repository deliverables

1. A reviewed source-to-destination migration manifest covering the NEMWEB
   lander, parser, schemas, transformations, checks, tests and bundle resources.
2. Licence, NOTICE and AEMO attribution updates required by directly adapted
   source or checked-in sample data.
3. Parameterised Declarative Automation Bundle resources for the NEMWEB landing
   Volume, file lander, Lakeflow pipeline, five-minute orchestration and analyst
   assets.
4. A safe, idempotent NEMWEB ZIP/CSV lander that handles report sections,
   versions, duplicate files, corrections/supersessions, bounded polling and
   observable failures.
5. A deterministic snapshot containing the critical report families and useful
   malformed, duplicate, correction and schema-drift cases.
6. Bronze tables retaining source file, report, version, event time and
   ingestion metadata.
7. Silver contracts with report-specific natural keys, latest-correction
   semantics, type/unit/time normalization, dimension joins and measurable
   quality handling.
8. Five-minute-grain Gold tables or views for all critical subjects. Do not
   expose only 30-minute and daily aggregates; those may be additional products.
9. Source-appropriate Gold or curated context for slower domains such as bids,
   registration/facilities, trading/settlement and market notices where the
   reference implementation is working and useful to analysts.
10. Unity Catalog comments, relationships and metric views defining units,
    signs, dispatch versus settlement grain, intervention treatment, market
    timezone and freshness.
11. Genie instructions, reusable SQL expressions, example SQL and benchmark
    questions over a deliberately small curated set of Gold/metric assets.
12. Automated checks for the important benchmark questions and generated SQL or
    reconciled query results.
13. An AI/BI dashboard whose SQL is tested against the target schema before the
    dashboard is created or updated, with the Genie experience linked.
14. Focused unit/integration tests, strict bundle validation and dated end-to-end
    evidence under `docs/test-evidence/`.
15. Updated README/deployment documentation sufficient for another workshop
    operator to understand snapshot mode, live mode, expected cadence,
    configuration, validation, operation and troubleshooting.

## Mandatory subagent execution model

Use subagents throughout this goal. The lead agent owns scope, integration,
evidence and final synthesis; it must not delegate accountability.

Before execution, list available agents and use only executable, non-disabled
agents. For the multi-phase run, make exactly one top-level asynchronous
subagent workflow call and orchestrate all children inside it. Keep only one
writer active in a shared checkout at a time. Read-only scouts and reviewers may
run in parallel. If parallel writers are genuinely necessary, give each an
isolated worktree and integrate deliberately.

### Stage A — context and evidence, in parallel

Launch:

- **`scout`** — inspect both repositories, current Git state, applicable
  instructions, bundle resources, enabled/disabled reference tables, tests,
  known failures and exact source-to-destination integration points. Require a
  concise manifest-oriented report plus clarification questions.
- **`researcher`** — verify only version-sensitive external facts needed for the
  implementation: current Lakeflow APIs, bundle schemas, Genie/AI/BI APIs,
  NEMWEB formats/corrections and attribution. Prefer primary sources and return
  dated citations plus unresolved questions.

Do not let either agent edit files.

### Stage B — implementation plan

Launch **`planner`** after Stage A. Give it the two reports, this goal and the
full NEMWEB miniwiki page. Require:

- a file/table migration manifest;
- a dependency-ordered implementation plan;
- critical versus slower-data classification;
- explicit tests and commands for each phase;
- deployment and rollback considerations;
- stop conditions and residual risks; and
- a mapping from every completion criterion to evidence.

The lead agent must reject or revise any plan that treats commented-out
reference libraries as working, omits five-minute Gold grain, uses legacy DLT
APIs, or claims cadence from configuration alone.

### Stage C — sequential implementation workers

Use **`worker`** agents sequentially in the shared checkout, or isolated
worktrees when separation is valuable. Give each worker a bounded file list,
done criteria and required checks. Suggested slices are:

1. migration manifest, provenance and bundle foundation;
2. lander/parser plus deterministic snapshot and tests;
3. critical Bronze tables;
4. critical Silver contracts;
5. critical five-minute Gold subjects;
6. slower NEMWEB analyst context;
7. metric views and semantic metadata;
8. Genie assets, benchmark/evaluation checks and AI/BI dashboard; and
9. operational documentation and evidence tooling.

A worker must return changed files, tests run, results, remaining risks and the
next dependency. Do not start the next writer until the previous output and diff
have been reviewed and integrated.

### Stage D — independent review after substantial slices

Use available specialised read-only reviewers where relevant:

- **`security-data-reviewer`** for URL/network controls, ZIP handling, path
  safety, credentials, UC boundaries, correction semantics and data leakage;
- **`edge-case-reviewer`** for malformed reports, multi-section CSV, schema
  drift, duplicates, late corrections, missing dimensions, negative/null
  values, interventions and interval/timezone boundaries;
- **`regression-reviewer`** for bundle resources, existing tests, workshop docs,
  fixtures, callers and deployment regressions; and
- **`reviewer`** as the fallback general code/plan reviewer.

Run independent read-only reviews in parallel when they examine the same stable
slice. Feed actionable findings to one subsequent worker for fixes. Re-run the
focused checks after every fix pass.

### Stage E — final adjudication

Use **`verification-adjudicator`** if available, otherwise a fresh `reviewer`, to
compare repository artifacts and captured results against every item in this
file. It must identify unsupported claims, missing commands, missing table
subjects and residual risks. The lead agent may claim completion only after all
blocking findings are resolved or clearly demonstrated to be external source
unavailability rather than an implementation gap.

## Dependency-ordered work

1. Validate the miniwiki and inspect Git status without overwriting unrelated
   work.
2. Produce the migration/provenance manifest.
3. Establish bundle variables, Volume, lander, pipeline and orchestration.
4. Build the deterministic snapshot path and parser tests.
5. Implement critical Bronze, Silver and five-minute Gold contracts.
6. Implement slower NEMWEB analyst context that is required by the curated
   questions.
7. Implement metric views and semantic metadata from stable Gold contracts.
8. Implement Genie configuration, examples, benchmark checks and dashboard.
9. Run all local tests, builds and static/bundle checks.
10. Execute workspace validation using `daveok`.
11. When the user explicitly instructs the executing session to run this goal
    end to end, deploy the selected dev target, run the live path and gather the
    three-cycle completion evidence. The repository file alone is not authority
    for an unrelated session to modify an external workspace.
12. Run final independent adjudication and update the miniwiki handoff.

## Required validation

Run relevant focused checks throughout, then the complete applicable suite:

```bash
python3 scripts/validate-miniwiki.py
uv run --extra test python -m pytest
rm -rf dist && uv build --wheel --out-dir dist
git diff --check
databricks bundle validate --strict -t dev --profile daveok
```

Also validate that:

- the Databricks CLI meets the version required by the loaded Databricks skills;
- every pipeline source file uses supported modern APIs;
- all critical table dependencies are included in the bundle;
- snapshot runs are deterministic and idempotent;
- duplicate and correction tests prove the selected natural-key behavior;
- each dashboard SQL query succeeds through the CLI before dashboard creation or
  update;
- metric-view measures reconcile to their Gold sources;
- Genie benchmark SQL/results reconcile to governed assets; and
- live evidence queries inspect data watermarks, not only resource state.

For deployed pipeline runs, poll the specific update to terminal state and
extract underlying errors from pipeline events. Do not infer success from the
top-level pipeline state. Avoid a destructive full refresh unless its data-loss
impact is understood and the executing user explicitly requests it.

## Evidence artifact

Write a dated file such as:

```text
docs/test-evidence/nemweb-e2e-YYYY-MM-DD.md
```

Include:

- commit/worktree state and relevant source versions;
- adapted-file/provenance summary;
- exact validation commands and outcomes;
- snapshot reconciliation results;
- deployed resource names without secrets or private tenant details;
- tested dashboard and benchmark queries;
- the three-cycle watermark/latency table for every critical Gold subject;
- failures encountered and fixes applied;
- unresolved external limitations; and
- the final adjudicator's finding summary.

Do not include tokens, credentials, private workspace URLs or sensitive tenant
identifiers.

## Stop and report rather than guessing when

- reference licensing or attribution cannot be satisfied;
- `daveok` is missing, unauthenticated or points to an unexpected workspace;
- required UC, SQL warehouse, pipeline, Genie or dashboard capabilities are not
  available in the selected environment;
- source report semantics or natural keys cannot be established from code,
  fixtures or primary AEMO evidence;
- a destructive refresh or incompatible schema replacement would be required;
- live NEMWEB is unavailable long enough that three-cycle evidence cannot be
  gathered; or
- unrelated working-tree changes overlap files a worker needs to replace.

A stop report must give the exact blocker, evidence collected, safe work already
completed and the smallest next action. It must not label the overall goal
complete.

## Final response contract

The lead agent's final response must state:

1. what was implemented;
2. changed files and major Databricks resources;
3. validation and live commands actually run;
4. the three-cycle five-minute Gold evidence;
5. Genie, metric-view and dashboard verification results;
6. independent review findings and their disposition;
7. residual risks or source/workspace limitations; and
8. whether the authoritative completion criteria are met.
