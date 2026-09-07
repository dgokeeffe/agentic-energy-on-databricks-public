# Now

## Current focus

Workshop pairs execute the default challenge from
[`../docs/participant/workshop-playbook.md`](../docs/participant/workshop-playbook.md):

> Can an operator trust the latest regional price trend, given NEMWEB
> corrections, freshness, and timezone handling?

Facilitators use [`../docs/facilitator/workshop-run-of-show.md`](../docs/facilitator/workshop-run-of-show.md).
Use the shared GitHub-issue lifecycle, not a seeded patch from the historical lane
directories. The optional [read-only investigation practice](../workshop/agent-practice/README.md)
uses two synthetic cases to distinguish SCADA output from availability and missing
input from zero. It requires issue/plan authorisation and facilitator placement and
rehearsal; no live operation or successful agent replay is claimed by the fixtures.
The [development-learning page](features/agentic-development-learning-loop.md) records
the implemented local slice and the work still deferred.

Repository operators still need to close the live validation gate for the
[full NEMWEB Lakeflow pipeline](features/full-nemweb-lakeflow.md). Local and
snapshot results alone do not prove live five-minute operation.

## Next safe action

Run an independent repository review and the complete pre-deployment command set
in [`../docs/nemweb-operations.md`](../docs/nemweb-operations.md). Resolve every
blocking finding before an explicitly authorised dev deployment with the
`daveok` profile and an isolated schema. Keep both schedules paused through the
initial pipeline, semantic, benchmark and dashboard SQL gates.

## Open threads

- Prove each deployed Lakeflow source analyses and executes on serverless compute.
- Execute metric-view reconciliation plus every canonical Genie/dashboard SQL
  statement before creating or updating analyst assets.
- Retrieve the deployed dashboard and Genie space to confirm their resolved link.
- Observe three consecutive scheduled five-minute cycles and retain one evidence
  row per critical subject/cycle using the exact pipeline update IDs.
- Report daily T+1 unit target/availability separately from five-minute SCADA
  actual output; never infer availability that AEMO Current does not publish.
- Keep market notices omitted until a bounded plain-text parser, fixture and
  correction contract are independently proven.

## Session handoff — 2026-09-05

**What changed or was learned.** Trialled the facilitator Foundation demo and
designed the workshop's opening demonstration. The design, its measured
evidence and three discarded alternatives are in
[`decisions/opening-demo.md`](decisions/opening-demo.md).

Six issues now carry `workshop-ready`: #5, #6, #7, #8, #9, #12, spanning
pipeline, operations, dashboard, Genie and app areas. Before this the label was
on zero issues, so the documented participant selection path in
[`../QUICKSTART.md`](../QUICKSTART.md) returned an empty list.

Foundation stages 01 and 02 ran green against the dev target with the `daveok`
profile. Orchestration run `112853277696041` terminated SUCCESS in 4m10s. The
exact pipeline update was resolved by the runbook's uniqueness proof rather than
by selecting "latest": the `publish_medallion` window 13:01:48.444Z–13:04:50.664Z
yielded exactly one candidate, `a94157f3-6e45-448a-91fd-bb73dfe19d6f`, COMPLETED,
cause JOB_TASK, `full_refresh=False`. Its filtered events were 277, all INFO, no
ERROR or WARN. Reconciliation: Bronze/Silver/Gold dispatch price 4→4→4, Gold
SCADA 22 rows, quarantine 0/0/0, zero natural-key and zero effective-run
uniqueness violations, both intervention runs retained with exactly one
effective, metric view reconciling to 2 effective rows. Schedules stayed PAUSED
and `allow_live_nemweb` stayed false throughout. Snapshot remains non-live
evidence and does not touch the live gate below.

`capture_nemweb_evidence.py` correctly refused in snapshot mode with
`live evidence requires pipeline configuration nemweb.source_mode=live`.

**Three repairs applied, uncommitted.** `evidence.py` now emits a mode-aware
`next_command` and an explicit `live_evidence` field, because the DAG previously
advertised the capture script unconditionally and sent a snapshot operator into a
guaranteed traceback. `make bundle-validate` now sources `.env` and pre-checks
every no-default variable by name; it previously failed cold on
`app_serving_schema`. That uncovered a larger gap: `nemweb_ml` requires six
variables, has no overrides file, and none were documented anywhere in the
repository, so that bundle had never validated. `env.example` now documents all
16 variables. Seven stale duplicate `docs/*.md` pages carrying an older,
conflicting clock were removed with `git rm`; the three `docs/coda-*` files are
legitimate redirect stubs and were left alone.

**Evidence.** `make bundle-validate PROFILE=daveok` exits 0 with both bundles
reporting `Validation OK!`. Root and foundation suites 282 passed, 52 subtests.
Links valid across 105 tracked files, miniwiki 11 pages, safety 379 files.
`make foundation-snapshot` manifest SHA-256 `785e7c6f…` unchanged by the edits.
`git diff --check` clean.

**Still uncertain.** Whether the six-minute demo fits the preflight slot in
practice; only a rehearsal answers it. Whether the thin snapshot fixture should
be thickened before the 10:18 inspection, since business-facing issues #6, #9 and
#12 currently inspect 2 rows and 1 region.

**Next question.** Rehearse the demo narration, then decide whether the staged
deletions and three repairs are committed as one change.

## Session handoff — 2026-09-02

Stages 1–8 implemented the migration/provenance foundation, secure parser and
snapshot, Bronze/Silver/Gold contracts, slower analyst context, metric views,
Genie benchmarks and dashboard. Stage 9 added deterministic snapshot and strict
live-evidence validators plus the operator runbook. Evidence capture polls one
explicit update, filters that update's events, reads nested exceptions, checks
current NEMWEB listings and queries data watermarks rather than trusting resource
state.

The five-minute unit/facility product is SCADA `actual_generation_mw`, enriched
from monthly NEMWEB MMSDM dimensions. Authoritative dispatch target and
availability remain a distinct daily T+1 table. Snapshot output is synthetic or
an attributed row excerpt and always marked `live_evidence: false`.

Facilitators only: do not write a dated PASS evidence file until
`uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_live.py`
accepts at least three consecutive cycles (15 critical-subject rows) and final
independent adjudication finds no
unsupported claim.
