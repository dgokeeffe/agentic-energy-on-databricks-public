# Now

## Current focus

Workshop pairs execute the default challenge from
[`../QUICKSTART.md`](../QUICKSTART.md):

> Can an operator trust the latest regional price trend, given NEMWEB
> corrections, freshness, and timezone handling?

Facilitators use [`../foundation/deployment-gates.md`](../foundation/deployment-gates.md).
Participants choose one self-contained track from [`../QUICKSTART.md`](../QUICKSTART.md);
see [`decisions/track-structure.md`](decisions/track-structure.md).
The optional [read-only investigation practice](../workshop/agent-practice/README.md)
uses two synthetic cases to distinguish SCADA output from availability and missing
input from zero. It requires issue/plan authorisation and facilitator placement and
rehearsal; no live operation or successful agent replay is claimed by the fixtures.
The [development-learning page](features/agentic-development-learning-loop.md) records
the implemented local slice and the work still deferred.

Repository operators still need to close the live validation gate for the
[full NEMWEB Lakeflow pipeline](features/full-nemweb-lakeflow.md). Local and
snapshot results alone do not prove live five-minute operation.

The Track C app was redesigned around fuel value capture; see
[`decisions/app-value-capture-redesign.md`](decisions/app-value-capture-redesign.md).
Its remaining dependency is a facilitator grant on
`gold_nem_scada_generation_5min` in the app serving schema.

## Next safe action

Run an independent repository review and the complete pre-deployment command set
in [`../foundation/deployment-gates.md`](../foundation/deployment-gates.md). Resolve every
blocking finding before an explicitly authorised dev deployment with the
`DEFAULT` profile and an isolated schema. Keep both schedules paused through the
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

## Session handoff — 2026-09-10: registration attribution freshness (issue #7)

**Read [`decisions/registration-coverage-metric.md`](decisions/registration-coverage-metric.md)
before touching this work.** It holds the reasoning a fresh session would
otherwise re-derive, including two rejected metrics and why.

**Where the work is.** Branch `feat/registration-attribution-freshness`, seven
commits `d202a02..e08a5ff`, pushed to the fork
`saket-gogte14/agentic-energy-on-databricks-public`. Open as **draft** PR #28
against `dgokeeffe:main`. `origin` is unchanged and read-only to this account
(`push: false`, verified via the API), so a fork is the only contribution route
and a maintainer merges.

**What it does.** An analyst can see when the region and fuel attribution behind a
value-capture figure is stale, incomplete, or not assessable. Coverage is the
signed UTC publication-time distance from the SCADA being priced to the weakest of
the three monthly registration loads, carried Silver → Gold → serving → app and
rendered on the value-capture card. The partially-enriched facility count now
renders for the first time; it previously died in the domain layer at
`fuelCapture.ts:298`.

**The finding that reshaped the issue.** Issue #7's literal ask — the lag between
`registration_effective_at` and the priced intervals — is **identically zero by
construction**, because both sides are `MAX(interval_end)` of the same Bronze
table. It would have shipped an indicator that could never fire. The substitution
was approved by the requester; the operator outcome in the issue is unchanged and
met.

**Evidence.** Root and foundation 345 passed with 37 subtests (320 at `05dad2c`);
app 101 unit tests and 3 Playwright tests; typecheck, eslint and appkit lint
clean; links 120 files, safety 432 files, miniwiki 20 pages;
`git diff --check` clean. Label **prepared/snapshot** — no live NEMWEB claim.

**A blocking defect was found late, by an independent reviewer, and repaired.**
`ALTER TABLE … ADD COLUMNS IF NOT EXISTS` is not valid Databricks SQL. Proven with
a read-only probe against a deliberately nonexistent table, which separates a
parse failure from a missing-table failure: with the clause,
`[PARSE_SYNTAX_ERROR] at or near 'EXISTS'`; without it,
`[TABLE_OR_VIEW_NOT_FOUND]`. It would have failed the serving job on the next
refresh, and **no local test could catch it because none reach a SQL engine.** Now
`MERGE WITH SCHEMA EVOLUTION`, which is per-statement and reviewed rather than a
table-wide `autoMerge`.

Chasing that reviewer's symmetry point then exposed a **real pipeline defect**:
Silver published `registration_publication_at`, Gold dropped it, and the app
selected it — so the app read a column the serving table would never have had. The
coherence test had compared only two of the three layers. It now spans all three
and asserts set equality.

**Still open, needing a person:**

- **Re-review.** `e08a5ff` post-dates the review that requested it. Per
  `adversarial-review`, accepted repairs return through the gates, so a fresh
  reviewer on the full diff is the next gate before the draft is lifted.
- **E1 has no issue yet.** `io.py:281` stamps `F.lit("listing_or_http")`
  unconditionally, discarding the `retrieval_fallback` that `lander.py:432`
  computes. Every Bronze table using `section_stream` is affected. Consequence
  here: the basis leg of the degradation guard is **inert**, and a timing heuristic
  is what actually fires. It is recorded only in the PR body, so **it dies if #28
  is closed.**
- **E2 blocks workshop use.** All six snapshot manifest artifacts have
  `source_publication_at: null`, so the default path renders "not assessable" —
  correct, but an invisible demo. Anyone assigning #7 as an exercise gets a feature
  that never shows its interesting state. Re-cutting the snapshot is a
  fixture-provenance decision for a facilitator.
- **Nothing is runtime-verified in the pipeline.** `pyspark` is not a test
  dependency, so the `F.min` aggregates, the pre-filter placement and the schema
  evolution are statically proven only. Needs an authorised run with
  `--profile DEFAULT`, schedules PAUSED, `allow_live_nemweb` false.
- **Lakebase branch `dev-saket`** was provisioned from `production` (LSN
  `0/1E17F68`) and still exists, holding a compute against the documented
  20-per-project limit. Remove it when the work is done.

**Next question.** Does the re-review pass on `e08a5ff`, and should E1 be filed
before #28 leaves draft?

## Session handoff — 2026-09-09: repository split resolved

**Two repositories existed with no shared Git history, and the workshop exercises
were in the wrong one.** The public repository was started as a clean snapshot
(`2f15794`), not a fork, so no commit is common to both and no private head SHA
resolves against it. GitHub issues are repository metadata rather than Git objects,
so they did not travel with the snapshot: the code moved, the 21 issues did not.

**`…-public` is canonical** — four days newer, and the private repository has none of
the Track C app, fuel value capture, the self-contained tracks, or the
facility-dimension fix. Full reasoning, the number mapping, and what was deliberately
not migrated are in [`decisions/two-repositories.md`](decisions/two-repositories.md).

**Five exercises migrated verbatim, renumbered.** Private #5,#6,#7,#8,#9 became
public #2,#3,#4,#5,#6, each noting its original number. All 13 workshop labels were
recreated first. **Numbers are not portable** and the offset is not constant, because
public #1 is the redesign pull request.

**Private #12 was stale and was rewritten rather than copied.** It asked to build the
regional operations screen, which exists and has been redesigned twice. Public #7
instead targets two gaps found by grep: `registration_effective_at` is written by
`silver_facilities.py` and read by no Gold surface, and
`registration_enrichment_quality()` is called only from its own test. Both bear on the
value-capture figures, since `gold_nem_scada_generation_5min` groups by `region_id`
and `fuel_type` from that dimension. Public #7 carries no `workshop-ready` label,
because the issue bodies require a facilitator rehearsal first and it has never been
run.

**Two stale pointers repaired.** `issue-navigator` told an agent to list
`workshop-ready` issues, which returned nothing on a fresh clone; it now gives the
exact command, says to stop rather than improvise a ticket on an empty list, and
states the route is optional. `nemweb_app/README.md` cited four issue numbers that
did not resolve.

**The participant path never depended on issues.** `QUICKSTART.md` has no reference to
an issue or `workshop-ready`; the 2026-09-07 restructure already made each track
self-contained. The migration restores an optional contribution route, it does not
unblock the workshop.

**Still open.** Whether the five migrated exercises are still the right exercises —
only #2 was verified as genuinely open, the rest were spot-checked. Whether to archive
the private repository. And whether its two unmerged branches hold anything absent
from the public repository; nobody has looked.

## Session handoff — 2026-09-08 (third): authorised dev run

**The pipeline fix is now proven at runtime, not just statically.** Authorised dev
deployment against `agentic_energy_workshop_d4` with the `DEFAULT` profile. Cold-start
order followed: context, critical, semantics, app-serving. Both schedules stayed
PAUSED and `nemweb.source_mode` stayed `snapshot` throughout; `allow_live_nemweb`
stayed false. No live NEMWEB fetch occurred, so Gate 6 remains untouched and open.

Pipeline update resolved by uniqueness proof, not "latest": window
13:34:42.062Z-13:39:56.682Z gave exactly one candidate,
`da84017c-b83c-42f2-8c47-510df3d3efb8`, COMPLETED, `full_refresh=False`.

The decisive result: `registration_effective_at` is `2026-06-30T14:10:00Z`, equal to
`MAX(interval_end)` in Bronze SCADA and **ten weeks behind** the `2026-09-08` wall
clock. Before the fix it would have been today's date. One distinct value, 14 rows
for 14 DUIDs, so the `crossJoin` produced a scalar and did not fan out.

**The run found a second defect the fixture could never have caught.** The app's fuel
mapping was written from guessed `CO2E_ENERGY_SOURCE` strings, and the local fixture
was built from the same guesses. Against real data `Natural Gas (Pipeline)` and
`Diesel oil` fell through to the unknown bucket and displayed real generation as
"Unattributed fuel". Every distinct workspace value is now mapped and pinned, plus a
test that the canonical initcap forms match the raw AEMO casing. Same lesson as the
primary defect, one layer out: a test written from the same assumption as the code
confirms the assumption, not the behaviour.

**The app's open dependency is closed.** `gold_nem_scada_generation_5min` is
published into the serving schema by a new `nemweb_app_serving` task following the
reviewed pattern, with the overlap guard counting the composite natural key. Job run
`354366776080686` SUCCESS on both tasks; serving reconciles 22 rows to 22 across 11
region/fuel pairs; both reviewed app SQL files execute against the warehouse.

**Also repaired.** `npm ci` during `make validate-local` cleared the typegen cache and
silently downgraded `latest_region_status` to `result: unknown`. Both queries are now
fully typed. Run typegen with `nemweb_app/.env` sourced; ad hoc environment variables
leave it degraded.

**Evidence.** Foundation 299 passed with 37 subtests, root 33, app 52 unit and 3
smoke, links 92 files, safety 374 files, miniwiki 16 pages, both bundles
`Validation OK!`.

**Still open.** Whether the `crossJoin` broadcasts cleanly or adds a shuffle at
sustained five-minute cadence — the snapshot is too small to show it. The three-cycle
live gate. Interconnector and constraint join fan-out. Whether to collapse the PySpark
reimplementation into `build_facility_dimension`. Two commits were added to PR #1
after the run and still need independent review.

## Session handoff — 2026-09-08 (second)

**Pipeline defect found and fixed: the facility dimension selected rows by the wall
clock.** `silver_facilities.py` used `F.current_timestamp()` inside the `WHERE`
clause choosing effective `DUDETAILSUMMARY` and `DUALLOC` rows, so the same Bronze
data produced different Silver rows depending on when a refresh ran. Every DUID in
the snapshot carries two registration periods, and a refresh either side of the
boundary silently re-attributes five-minute generation to a different region or
fuel — which moves the Track C app's revenue and capture figures while every value
stays plausible. Latent in the current snapshot, because both periods there carry
identical region and fuel. Now pinned to the maximum SCADA `interval_end` in Bronze
and published as `registration_effective_at`. Full reasoning, three rejected
alternatives, and the narrow audit are in
[`decisions/facility-dimension-as-of.md`](decisions/facility-dimension-as-of.md).

**Why 290 tests missed it.** `build_facility_dimension` takes an explicit `as_of`
and is well tested; the pipeline never called it, reimplementing the same join in
PySpark with a clock call substituted for the pinned parameter. Tested code and
deployed code had diverged on exactly the time-dependent input.
`test_snapshot_idempotency.py` covers landing and parsing only, never the Spark
layer. Captured as facilitator material in
[`../workshop/agent-practice/green-tests-wrong-code.md`](../workshop/agent-practice/green-tests-wrong-code.md).

**The guard had the same bug it was written to catch.** The first AST checker looked
for clock calls inside `.where()`, but the original code bound
`F.current_timestamp()` to `now` and used the variable two lines later, so the
checker passed against the real defect. It now tracks names bound to a clock call
and asserts the inline shape, the via-variable shape, and a label-only `select` that
must not be flagged. Verified by reverting the view under `git stash`: **9 pass on
the fix, 2 fail on the original**, including the row-selecting clock check.

**Narrow audit of the app's read path.** SCADA correction dedup is sound
(`row_number() == 1` on `(interval_end, duid)`). The facility join cannot fan out,
because all three registration sources deduplicate before joining.
`is_effective_run` is filtered on the price path at three levels. It is **not
applicable** on the fuel path and the absent `WHERE` clause is correct, because
SCADA carries no intervention dimension. Only `silver_facilities.py` used a clock in
a filter; the other 21 uses are processing-time labels.

**Still open, outside the app's read path.** Interconnector and constraint join
fan-out, late-arriving Bronze against full materialized-view recomputation, the
fixed-AEST versus session-timezone boundary, and full-recompute cost at five-minute
cadence. Also open: whether to collapse the PySpark reimplementation into
`build_facility_dimension` so tested and deployed logic become the same code. That
is the right eventual direction but a large change to a table three Gold surfaces
depend on: gold_nem_scada_generation_5min, gold_nem_unit_dispatch_5min, and
gold_nem_unit_dispatch_availability_t1. Verified 2026-09-08; earlier notes said
"five", which was an unverified number.

**Evidence.** Foundation 299 passed with 36 subtests (9 new), modern-API check 33
sources, root 33 passed, app 50 unit and 3 smoke. **The Spark view has not been
executed** — the mechanism is proven with the shared pure function and by static
reading of the PySpark; runtime behaviour is inferred. Confirming it needs an
authorised workspace run.

## Session handoff — 2026-09-08

**Track C app redesigned around fuel value capture.** The screen previously asked
whether the latest five-minute price could be trusted, which made data quality the
subject rather than the discipline, framed itself for a trading desk that the same
page forbade from trading, and put no magnitude at stake. It now answers "where did
the value go?" — per-fuel capture rate against the regional time-weighted price,
negative-price exposure, and the AEMO re-run that moves the revenue figure. The
reasoning, the market citations, and the retired alternatives are in
[`decisions/app-value-capture-redesign.md`](decisions/app-value-capture-redesign.md).

The visual language is adapted from [Open Electricity](https://github.com/opennem/openelectricity)
(MIT), whose palette is fundamentally a fuel-technology colour system and therefore
maps one-to-one onto `gold_nem_scada_generation_5min`. Fonts are deliberately not
self-hosted, so no font binary or third-party request was added. The AGL-inspired
blue theme was retired, which also removed its trademark-adjacent risk; relevance
to that audience now comes from the decision the app supports.

**Four defects found by checking rather than assuming.** A charging battery
produced a capture rate of −0.25×, because the ratio was applied to a buyer; it is
now withheld for net consumers, and being paid to charge reads as earned rather
than lost. The theme rendered near-black and unreadable for any reviewer whose OS
prefers dark, because AppKit ships `prefers-color-scheme: dark` on
`:root:not(.light)`, which outranks a bare `:root`; `client/index.html` now opts
out and a smoke test asserts it under an emulated dark scheme. The screen opened on
the first region alphabetically, which was the least interesting; it now opens on
the weakest capture. Capture direction was carried by red/green alone, failing WCAG
1.4.1, and now also carries a symbol and a screen-reader label.

**Evidence.** App 50 unit tests and 3 Playwright smoke tests pass; typecheck,
`eslint`, and `appkit lint` clean. Root suite 33 passed, foundation 290 passed with
36 subtests, miniwiki 15 pages, links valid across 89 files, safety 370 files,
modern-API check 33 sources, `git diff --check` clean. Prettier reports the same 3
generated files as on HEAD and no others. Removing the ECharts `LineChart` reduced
the main JavaScript asset from roughly 1,106 kB / 357 kB gzip to **479 kB / 141 kB
gzip**.

**Open dependency, needs workspace authority.** Fuel capture reads
`gold_nem_scada_generation_5min`, declared as a second `uc_securable` in
`nemweb_app/databricks.yml`. A facilitator must publish that table into the app
serving schema and grant `SELECT`. Until then integration mode reports the
generation read as unavailable and degrades only that section; fuel capture is
proven against the prepared fixture alone and no live claim is made.

**Still uncertain.** Whether the two-hour, three-region fixture window is the right
teaching size, and whether an analyst reads capture rate without a short spoken
introduction. Both need a rehearsal, not more code. The work is on branch
`redesign-fuel-value-capture` and is uncommitted pending review.

## Session handoff — 2026-09-07

**Docs restructured to self-contained tracks.** `QUICKSTART.md` is now a chooser
routing to Track A, Track B, or the new Track C (`workshop/track_c_app/`). Every
wall-clock time, card number, the 14:27 evidence exchange, and cross-track pairing
were removed. 64 broken links from the deletion are now 0. Decisions are in
[`decisions/track-structure.md`](decisions/track-structure.md) and
[`decisions/attendee-isolation.md`](decisions/attendee-isolation.md).

Two deleted files held **governed data contracts**, not workshop scaffolding. The
market-notices omission and the SCADA-versus-availability rule were recovered
verbatim into [`../nemweb_foundation/DATA-CONTRACT.md`](../nemweb_foundation/DATA-CONTRACT.md);
no test assertion was relaxed. `test_workshop_routing.py` had asserted that the
lane directories must **not** be routed, the opposite of the new decision, so it
was rewritten; `test_repository_safety.py` gained a narrow test bounding Track C's
new deploy permission.

**Facilitator-only deployment evidence.** Workspace-specific resource names,
run identifiers, branch LSNs, service-principal identifiers, and attendee
outcomes stay outside Git. This repository records the generic contracts,
validation commands, and safety gates only; it does not claim that a public
clone has access to a deployed workspace or live evidence.

**Operational notes.** On a cold schema, the context job must run before the
critical job. Lakebase resource identifiers and Postgres database names are
distinct values and must be supplied from the approved target configuration.
Both checks are recorded in
[`../foundation/deployment-gates.md`](../foundation/deployment-gates.md).

**Still uncertain.** The documented concurrent-compute limit has not been
load-tested for the actual attendee count. No live NEMWEB cycle is claimed here,
so the three-cycle gate remains open. The ML bundle validates locally but has no
public deployment evidence.

## Session handoff — 2026-09-05

**What changed or was learned.** Trialled the facilitator Foundation demo and
designed the workshop's opening demonstration. The design, its measured
evidence and three discarded alternatives are in
[`decisions/opening-demo.md`](decisions/opening-demo.md).

Six issues now carry `workshop-ready`: #5, #6, #7, #8, #9, #12, spanning
<!-- Those numbers are PRIVATE-repo numbers. The exercises were migrated to the
     public repository on 2026-09-09 and renumbered: private #5,#6,#7,#8,#9 became
     public #2,#3,#4,#5,#6. Private #12 was stale (it asked to build a screen that
     now exists) and was rewritten as public #7. See the 2026-09-09 handoff. -->
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

**Evidence.** `make bundle-validate PROFILE=DEFAULT` exits 0 with both bundles
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

## Session handoff — 2026-09-09 (Track C app)

The Track C app is mid-change and **nothing is committed** (88 changed files on
`main`, two agents' work interleaved). Full continuation notes, verified state,
remaining tasks and hazards are in
[`features/track-c-exploratory-investigation.md`](features/track-c-exploratory-investigation.md).

Read that page before touching `nemweb_app/`. Two things a fresh session will
otherwise get wrong: another agent is concurrently editing
`RegionalOperationsShell.tsx` and `JourneyHeader.tsx`, so `git checkout --` on a
shared file destroys its work; and `make app-dev-mock` does not run because the
Vite config uses `middlewareMode`, so use `vite build` + `vite preview` with
`VITE_DATA_MODE=mock` set at build time.

Current checks: `tsc` clean, 82 vitest passing, 3 Playwright passing.

The requester has settled four decisions: a **fresh git worktree** for app work, a
prepared analysis **computed from on-screen evidence**, agent commits limited to
**`nemweb_app/` and `miniwiki/`**, and four further tasks in scope (Track C
instructions and exercises, section consolidation, the stale DRAFT decision page,
and fixing `make app-dev-mock`).

Next action: commit the app work in this checkout, then create the worktree — in
that order, because a worktree from `HEAD` would otherwise start without any of it.
Then fix `make app-dev-mock` before the remaining visual work.

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
