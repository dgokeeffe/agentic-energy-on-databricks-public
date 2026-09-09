# Track C app: exploratory analyst investigation

Session handoff written 2026-09-09, ~23:50. Continue from here; do not rely on
chat history.

## Where this came from

The requester asked for the Track C app to look and behave like the GridSense
Intelligence Hub (`~/Repos/8-gridsense-intelligence-hub`, a separate local
repository, not a dependency). Three corrections happened during that session and
all three matter to whoever continues:

1. **GridSense is not an eight-tab command centre.** `frontend/src/config/demo.ts`
   sets `LTAP_DEMO_MODE = true` and `App.tsx` returns early on it, so the shipped
   app is `Header + LiveGenerationLanding` only. The tabs, war room, Digital Twin,
   Scenario Simulation and its ticker are dead code. `/net-zero` is the one
   separate page.
2. **The first attempt added instead of replacing.** A journey header and a map
   were bolted on top of the existing value-capture screen, producing fourteen
   sections of two different apps. The requester called this "slop". Anything
   further must replace or consolidate, not layer.
3. **The workflow framing was wrong.** The app implied an operator *decision*.
   The current instruction is an exploratory analyst workflow, below.

## Approved direction

```text
Observe → Ask Genie → Review evidence and uncertainty → Save investigation → Follow up
```

Replace "Decide" and "record the call" with "Investigate". The app must not imply
the user is making a bid, dispatch, curtailment or trading decision.

Build a **prepared Genie-analysis prototype**. Do not claim a released Genie Agent
is connected. It must use the selected region and interval, produce a clearly
labelled prepared analysis, state what the data does not establish, let the
analyst edit the result, and save the reviewed investigation to Lakebase.

## Hard boundaries

- Prepared or snapshot evidence is always labelled as such.
- No claim about availability, curtailment, causation, bids or forecasts. AEMO
  Current publishes no five-minute availability, so curtailment is not derivable.
- No credentials or private workspace details in code, prose, logs or screenshots.
- No writes to synced read-only tables. Lakebase `app_write` is the only writable
  state.
- No deployment, permission, schedule or live NEMWEB change.
- Do not revert unrelated work or overwrite another agent's changes.

## Verified state at handoff

Branch `main`, **88 files changed, nothing committed**.

| Check | Result |
|---|---|
| `npx tsc -b tsconfig.client.json` | clean |
| `npx vitest run` | **82 passed**, 6 files |
| `npx playwright test` | **3 passed** |

Playwright needs `npm run smoke:install` first, and it binds port 8000 — kill any
stray `vite preview` before running, or it fails with "port already used".

`make app-dev-mock` **does not work**: `client/vite.config.ts` sets
`middlewareMode: true`, so the Vite CLI exits with "HTTP server not available".
This predates this session (present in the initial repository snapshot). To see the
app, do what the Playwright config does:

```bash
cd nemweb_app
VITE_DATA_MODE=mock npx vite build --config client/vite.config.ts
VITE_DATA_MODE=mock npx vite preview --config client/vite.config.ts --host 127.0.0.1 --port 8000
```

`VITE_DATA_MODE` is read at **build** time. Building without it produces an
integration bundle that shows "Regional conditions could not be loaded" locally.

## Two live hazards

**Another agent is writing to this checkout.** It is working the `goal.md` Delta
landing task graph (`nemweb_foundation/delta_lander.py`, `source_registry.py`,
`land_nemweb_delta.py`) *and* it has edited Track C app files:

| Time | File | Whose |
|---|---|---|
| 23:27:26 | `client/src/components/InvestigationPanel.tsx` | theirs |
| 23:27:40 | `client/src/components/RegionalOperationsShell.tsx` | theirs, over mine |
| 23:43:21 | `client/src/components/JourneyHeader.tsx` | **theirs, editing my file** |

`git status` went 3 → 88 files during the session. `git checkout --` on any shared
file will destroy their work. Check `git status` and mtimes before editing, and
re-check after.

**They have already built most of this brief.** `InvestigationPanel.tsx` today has
an "Ask Genie for a prepared analysis" button, a labelled *"Prepared Genie-style
analysis"* alert, region/interval context, an editable note, and a Lakebase save.
The plan below deliberately **extends** their panel. Do not build a second
competing investigation surface.

## What exists and can be retained

Added this session, all under `nemweb_app/`:

| File | Lines | Purpose |
|---|---|---|
| `client/src/domain/facilityMap.ts` | 322 | projection, facility→dispatch join, coverage; pure |
| `client/src/domain/facilityMap.test.ts` | — | 27 tests |
| `client/src/components/NemGeneratorMap.tsx` | 327 | real NEM generator map |
| `client/src/components/TopProducersChart.tsx` | 186 | top stations by output |
| `client/src/components/GenerationByFuelChart.tsx` | 169 | stacked area fuel mix |
| `client/src/components/JourneyHeader.tsx` | 107 | five-step stepper |
| `client/src/lib/theme.ts` | 39 | explicit light/dark |
| `client/src/data/topology/` | — | 435 facilities, 572 DUIDs + `ATTRIBUTION.md` |
| `client/src/data/unitDispatchRepository.ts` + mock | — | third governed read |
| `config/queries/latest_unit_dispatch.sql` | — | reviewed SQL |
| `tests/fixtures/unit-dispatch.json` | — | real DUIDs, incl. an unmatched one |

The two charts are the **Observe** step and are done. The map is real: coordinates
are static public reference data (OpenElectricity, MIT, attributed in
`ATTRIBUTION.md`), every megawatt comes from `gold_nem_unit_dispatch_5min`, and
nothing on it is synthetic. `radiusFor` is capped at 15 so neighbouring Hunter
Valley stations stay countable; `regionAnchors` derives label positions from the
data rather than by hand.

Charts use AppKit's echarts-backed `AreaChart`/`BarChart`. **No new dependency was
added** — GridSense uses recharts, which is not installed here. Do not add it for
one chart.

## What must be renamed or removed

| Where | Now | Should be |
|---|---|---|
| `client/src/components/AppPurpose.tsx:37` | "record what you decided" | investigate what the evidence supports |
| `client/src/components/QueryState.tsx:41` | "before making an operator decision" | before investigating further |
| `JourneyHeader.tsx` STEPS | Observe · Locate · Explain · Investigate · Learn | the five approved steps |
| `RegionalOperationsShell.tsx:462` | `className="decision-cta"` | `investigate-cta`, plus the CSS rule |

**Do not rename the `decision` column.** It is persisted in
`app_write.investigations` (`server/db/schema.ts`), already shipped in
`workshop/lakebase/migrations/001_app_write_investigations.sql`, carries
`REPLICA IDENTITY FULL`, and feeds the Lakebase CDF contract. Renaming means a
migration plus a CDF-consumer change. The UI label is already "Investigation
note"; map at the UI edge and record this as deliberate debt.

## Requester decisions, 2026-09-09

Answered directly by the requester at handoff. These are settled; do not re-ask.

| Question | Decision |
|---|---|
| Two agents in one checkout | **Fresh git worktree** for the app work |
| Depth of the prepared analysis | **Computed from the evidence on screen** |
| The 88 uncommitted files | **Agent may commit app work only** |
| Also in scope | Track C instructions + exercises, section consolidation, the stale DRAFT page, and `make app-dev-mock` |

### Commit authorisation, and its exact limit

The requester authorised the agent to commit **`nemweb_app/` and `miniwiki/`
only**. `nemweb_foundation/` belongs to the other agent and must be left
uncommitted and untouched. This is a scoped exception to the repository default
that nothing is committed without explicit authorisation; it does not extend to
pushing, opening a pull request, merging or deploying.

**Unavoidable side effect, flag it in the commit message.**
`client/src/components/RegionalOperationsShell.tsx` and
`client/src/components/JourneyHeader.tsx` contain both agents' changes in the same
files. Committing the app work therefore also commits the other agent's
InvestigationPanel and Genie CTA work. There is no clean way to separate them
without rewriting one agent's edits, which is out of bounds. Say so in the message
rather than implying sole authorship.

### Worktree sequencing, which is not the obvious order

A worktree created from `HEAD` starts **without** any of this session's work,
because none of it is committed. So the commit must come first:

```bash
cd /Users/david.okeeffe/Repos/agentic-energy-challenge
git status --short                      # confirm what is app vs foundation
git add nemweb_app miniwiki             # NOT nemweb_foundation
git commit                              # note the interleaved authorship
git worktree add ../aec-track-c-app HEAD
cd ../aec-track-c-app && npm --prefix nemweb_app install
```

After that the worktree is the only place app files are edited, and the original
checkout is left to the other agent. Re-run `git status` in both before editing
either.

## Smallest plan to finish

1. **Language sweep** — the four renames above. UI only, no schema. ~30 lines.
2. **Re-sequence the stepper** to the five approved steps, and drive `activeStep`
   from real state rather than the hardcoded `activeStep={2}` in
   `RegionalOperationsShell.tsx`.
3. **`client/src/domain/preparedAnalysis.ts`** (new, pure, total): takes region,
   interval, capture and map coverage; returns
   `{ observations[], notEstablished[], followUps[] }`. Pure so it is unit-testable
   and so the "prepared, not a released Genie Agent" claim is structurally true —
   there is provably no Genie call. This is the only real work.
4. **Review evidence and uncertainty** — render `notEstablished` as an explicit
   list beside the editable note, not one sentence inside an `Alert`.
5. **Follow up** — reuse the existing `status` enum (`open`/`reviewing`/`closed`)
   already in the schema and the PATCH route. No migration.

Steps 1, 2 and 4 land in files the other agent is editing, which is why the
worktree comes first.

### What "computed from the evidence on screen" means concretely

The requester chose the computed option over templating, so `preparedAnalysis.ts`
must derive from values already on the page rather than interpolating a fixed
sentence. Inputs available without any new read:

| Input | Source already in the shell |
|---|---|
| capture rate per fuel, weakest fuel | `regionCapture`, `weakestCapture` |
| time-weighted regional price | `capture.timeWeightedPriceAudPerMwh` |
| negative-price interval count | `capture.negativePriceIntervalCount` |
| restated intervals, restated revenue | `priceSourceRunNo > 1`, `restatedRevenueAud` |
| stations reporting, unmapped DUIDs | `MapCoverage` from `facilityMap.ts` |
| source and Gold freshness | `sourceIntervalWatermark`, `goldPublishedAt` |

`notEstablished` should be derived too, not a constant: unavailability of
five-minute availability is always true, but "N units unenriched" or "M intervals
restated" only belong in the list when the data says so. That is the difference
between a computed analysis and a template wearing one.

## Also in scope, per the requester

6. **Track C instructions and exercises.**
   `workshop/track_c_app/Instructions.md` stage 1 still tells participants to run
   `make app-dev-mock` (broken, see below) and describes the value-capture screen.
   The twelve `workshop/exercises/DRAFT-*.md` files reference the old journal
   wording. Re-cut both against the exploratory workflow.
7. **Consolidate the remaining sections.** 13 sections, ~4,770px. `AppPurpose` and
   `JourneyHeader` overlap; the hero, KPI grid and value-capture card restate the
   same finding three times. Note that `tests/smoke.spec.ts` asserts
   "What it cannot tell you" and the no-five-minute-availability boundary, and the
   original author deliberately stated that boundary twice (purpose card and
   footer). Consolidate without dropping either.
8. **Rewrite `decisions/DRAFT-gridsense-control-room-port.md`.** It argued for a
   design this brief supersedes and still contains the corrected claim that
   GridSense is an eight-tab command centre. Rewrite it as the
   exploratory-investigation decision, or delete it and fold the durable findings
   (the `LTAP_DEMO_MODE` discovery, the pipeline comparison, the facility
   coordinate source) into this page.
9. **Fix `make app-dev-mock`.** Root cause is `middlewareMode: true` in
   `client/vite.config.ts`, which exists because AppKit's Express server mounts
   Vite as middleware in dev. Likely smallest fix, **unverified**: make it
   conditional, e.g. `middlewareMode: process.env.VITE_STANDALONE !== 'true'`, and
   set `VITE_STANDALONE=true` in the Makefile target. That keeps the AppKit server
   path intact and gives participants hot reload, which `vite preview` does not.
   Verify before trusting this; the alternative is to change the target to
   `build` + `preview` and accept losing hot reload.

## Tests to run

```bash
cd nemweb_app
npx tsc -b tsconfig.client.json
npx vitest run                 # 82 now; add ~8 for preparedAnalysis
npx playwright test            # 3 now; extend to Ask → Review → edit → Save
cd .. && make app-test miniwiki links safety
git diff --check
```

New `preparedAnalysis` tests should assert: output varies with region and interval;
every result carries a prepared label; `notEstablished` is never empty; and no
availability, curtailment, causation, bid or forecast claim is reachable.

Cannot run here, with reason: `make bundle-validate` needs `--profile DEFAULT` and
no task has authorised a workspace call; `npm run typegen` needs a live warehouse,
which is why `shared/appkit-types/analytics.d.ts` was hand-edited to add
`latest_unit_dispatch` despite its "DO NOT EDIT" banner. **Regenerate it** when a
warehouse is available.

## Design decisions worth keeping

- **Fuel tokens are one shared vocabulary.** `--fuel-*` in `index.css` drives the
  charts, the value-capture bars and the map, so three surfaces cannot disagree
  about brown coal. Do not introduce a second palette.
- **Dark mode lifts only the darkest five fuel tokens.** Hue stays fixed; Open
  Electricity calibrated these against a near-white page, and `coal_black`
  (`#121212`) rendered as invisible bars on a `#161b22` card. Shell tokens follow
  GridSense; the 10px rem root is retained because ~900 lines of CSS depend on it.
- **Theme is class-driven, never a media query.** AppKit ships
  `@media (prefers-color-scheme: dark) { :root:not(.light) { … } }` which outranks
  a bare `:root`. `index.html` keeps `class="light"` for first paint. A Playwright
  test guards a reviewer whose OS prefers dark.
- **No `live` boolean anywhere.** Both data modes read prepared data. A `prepared`
  boolean previously produced a pulsing green live dot beside the word "Prepared".
  `JourneyHeader` takes `provenanceLabel: string` plus `stale: boolean` instead.
- **One provenance badge per page**, in the header. Sections do not repeat it.
- **Notices are chips, not banners.** Three stacked full-width banners became one
  wrapping `.notice-row`. The old warning banner reused
  `--fuel-solar_utility` as an alert colour, so "read unavailable" looked like a
  chart series. Only live staleness is styled as an alert.

## Failure modes to avoid

Every one of these actually happened this session:

- **Shortening prose silently dropped required content.** A compact chip lost
  "Do not treat these values as current" (a test caught it) and the diagnostic
  explaining that a failed read is a *missing grant, not an outage*. When
  condensing, check what the original sentence was carrying.
- **Tests passed while the screen was broken.** Black bars on a black card,
  "Bayswater ×3", and a green live dot beside "Prepared" all passed `tsc` and
  vitest. **Build it, open it, and read the rendered page** before reporting.
- **Hand-placed coordinates were wrong.** Region label anchors guessed by eye put
  NSW1 ~100 units above its own stations and TAS1 over Victoria. Derive from data
  and assert it.
- **`colors` on an AppKit chart maps to series, not categories.** An array indexed
  per-bar silently gives every bar the first colour. Use one series per fuel.
- **Accessible names collide.** A landmark labelled by a heading containing
  "recorded decision" made `getByLabel('Decision')` match both the region and the
  journal textarea. Narrow landmark names.

## Suggested order

1. Commit `nemweb_app/` + `miniwiki/` in this checkout, then create the worktree.
2. Task 9 (`make app-dev-mock`) next — it unblocks seeing the app with hot reload,
   and every later visual task benefits.
3. Task 3 (`preparedAnalysis.ts`) — new file, no conflict, the substantial piece.
4. Tasks 1, 2, 4, 5 — the language sweep, stepper, uncertainty list, follow-up.
5. Task 7 (consolidation), then task 6 (instructions and exercises) last, so the
   docs describe a settled screen.
6. Task 8 (DRAFT page) whenever convenient.

## Open questions

None blocking. If the other agent's Genie work diverges from the approved five-step
workflow, that is a conversation for the requester rather than something to
resolve by overwriting their files.
