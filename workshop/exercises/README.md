# Draft Stage 4 exercises, for facilitator review

**Nothing here is workshop-ready.** These are drafts for the repository owner to
read, cut, and edit before any GitHub issue is raised. A facilitator must rehearse an
exercise before it carries `workshop-ready`; that requirement comes from the exercise
bodies themselves and is not waived by anything here.

## These are Stage 4 slots, not standalone tickets

[`workshop/track_c_app/Instructions.md`](../track_c_app/Instructions.md) already has
six stages, and **Stage 4 is deliberately open**: *"Pick one change. Keep it small
enough to prove."* It offers a table of starting points but no concrete exercise. That
is the gap these fill.

That framing sets the real budget. In a **3 to 4 hour track**, Stage 4 is not the
whole session:

| Stage | What it costs |
|---|---|
| 1–3: local run, branch, slug, **deploy** | the largest slice. `make validate-local` alone measured **6m24s**, about five minutes of it a cold `@playwright/test` install |
| **4: the change** | **60–90 minutes realistically** |
| 5–6: verify on your branch, close | redeploy and reconcile, not negligible |

So each draft below is scoped to **60–90 minutes**, states a **30-minute
checkpoint**, and names the one thing to cut if time runs short. An exercise that
only pays off at the end is the wrong shape at this length.

Track A and Track B have their own numbered stages; the non-Lakebase drafts here suit
those tracks' equivalent slots.

## What the data actually supports

Verified against the deployed dev workspace on 2026-09-09, not assumed:

| | |
|---|---|
| `gold_nem_region_dispatch_5min`, effective runs | **2 intervals, 1 region** |
| Negative prices in the snapshot | **0** |
| Restated (corrected) intervals | **0** |
| `bids`, `trading`, `settlement`, `market_notices` archives | **0 each** |
| Gold tables with zero consumers | **6** |

The two dispatch archives are named `PUBLIC_DISPATCHIS_202401010005_SYNTHETIC.zip` —
synthetic, and there are two. Nothing ingests every five minutes today:
`nemweb.source_mode=snapshot`, `allow_live_nemweb=false`, and both schedules are
PAUSED. The five-minute cadence is what live mode *would* do; live mode has never
been run, and that is Gate 6.

This is deliberate. It is what makes `make foundation-snapshot` reproducible to a
byte-identical SHA-256. The cost is almost no market variety.

**A note on the earlier NEMWEB work.** The
`australian-energy-nemweb-analytics` repository has a much broader pipeline — BOM
weather, ABS CPI, CER rooftop solar, public holidays, market notices, PASA. Its
workspace no longer exists, and it was deployed to different hosts than the workshop's
(`adb-...776.16` and `adb-...303.3` versus the workshop's `adb-...517.17`). The
workshop foundation is an adaptation of it, recorded in `NOTICE.md` at source revision
`4c66923`. So none of that breadth is available as data here, and `goal.md` explicitly
placed those feeds outside the critical path. The code remains a useful reference if
the workshop ever needs a second source family.

### Consequence, stated plainly

An exercise needing a price spike, a negative price, a correction, several regions, a
bid, or a settlement row **cannot be seen working today**. A participant can write the
code and unit-test it, but the demonstration becomes "watch your detector find
nothing", which is a poor use of 90 minutes.

Every draft carries a **Visible today** line:

- **yes** — works against the current snapshot as-is;
- **yes, Lakebase only** — the payoff is in Postgres, which the participant writes
  themselves, so no market variety is needed;
- **needs richer data** — blocked on a facilitator landing real archives.

Do not promote a "needs richer data" draft to `workshop-ready` without doing that
first.

### Thickening is one authorised live run, not a fixture project

The lander's live discovery uses `critical_lookback_hours = 2`, so a single authorised
run would fetch roughly two hours of real NEMWEB: about 24 five-minute intervals
across five regions, with whatever genuinely happened. Bids and trading have their own
Current listings.

That is a separate authorisation from any deployment approval, gated behind
`--allow-live` wired to `allow_live_nemweb` in `resources/nemweb_lander.job.yml`. It
is also better than hand-authoring fixtures, because real data contains values nobody
thought to guess. This session shipped a fuel mapping built from guessed
`CO2E_ENERGY_SOURCE` strings, tested against a fixture built from the same guesses;
two real fuels fell through to "Unattributed fuel" and only a deployment revealed it.

## Index

Demonstrable today. Eight of the ten are Lakebase-central, which is what a 90-minute
slot with no market variety needs.

| Draft | Track | Difficulty | Lakebase | Fixes a real defect |
|---|---|---|---|---|
| [`DRAFT-shift-handover.md`](DRAFT-shift-handover.md) | C | core | **central** | no |

Facilitators can rehearse the visible shift-handover comparison with the
[planned and shoddy-run prompts](shift-handover-facilitator-prompts.md). Keep
that comparison separate from participant evidence and reset between runs.
| [`DRAFT-investigation-audit-trail.md`](DRAFT-investigation-audit-trail.md) | C | core | **central** | **yes** — `decision` overwritten in place |
| [`DRAFT-soft-delete-restore.md`](DRAFT-soft-delete-restore.md) | C | core | **central** | **yes** — hard `DELETE`, unrecoverable |
| [`DRAFT-status-transitions.md`](DRAFT-status-transitions.md) | C | core | **central** | **yes** — `closed` → `open` silently allowed |
| [`DRAFT-team-view.md`](DRAFT-team-view.md) | C | core | **central** | **yes** — `team_identifier` written, never read |
| [`DRAFT-watchlist-thresholds.md`](DRAFT-watchlist-thresholds.md) | C | core | **central** | no |
| [`DRAFT-optimistic-concurrency.md`](DRAFT-optimistic-concurrency.md) | C | advanced | **central** | **yes** — README admits it |
| [`DRAFT-accessibility-audit.md`](DRAFT-accessibility-audit.md) | C | core | no | **likely** — never audited |
| [`DRAFT-shell-decomposition.md`](DRAFT-shell-decomposition.md) | C | core | no | **yes** — `5 / 60` duplicated in a component |
| [`DRAFT-loading-error-states.md`](DRAFT-loading-error-states.md) | C | core | no | partly — two queries, one error state |
| [`DRAFT-genie-refusal.md`](DRAFT-genie-refusal.md) | A | core | no | no |
| [`DRAFT-metric-view-capture.md`](DRAFT-metric-view-capture.md) | A | advanced | no | **yes** — definition exists only in TypeScript |
| [`DRAFT-ml-refuse-to-train.md`](DRAFT-ml-refuse-to-train.md) | B / ML | core | no | **yes** — README requires a gate nothing enforces |

Designed but blocked on data — review the shape, do not schedule:

| Draft | Track | Difficulty | Lakebase | Blocker |
|---|---|---|---|---|
| [`DRAFT-rebid-narrative.md`](DRAFT-rebid-narrative.md) | A or C | advanced | for notes | `gold_nem_bid_stack` has 0 rows |
| [`DRAFT-interconnector-congestion.md`](DRAFT-interconnector-congestion.md) | B | advanced | no | 1 region cannot diverge from itself |
| [`DRAFT-ml-train-baseline.md`](DRAFT-ml-train-baseline.md) | B / ML | advanced | no | **3 training rows.** Needs weeks of history, not one live cycle |

## Frontend and ML coverage, and why ML is mostly blocked

**Frontend.** Three drafts are frontend-only: accessibility audit, shell decomposition,
and loading/error states. The strongest is decomposition, because
`RegionalOperationsShell.tsx` is **485 lines** with six responsibilities, and it contains
this:

```tsx
row.actualGenerationMw * (5 / 60) * (priceByInterval.get(row.intervalEnd) ?? 0)
```

That `5 / 60` is the interval-to-hours conversion, and `INTERVAL_HOURS` already exists in
`domain/fuelCapture.ts`. Market semantics encoded twice — the same shape as the pipeline
defect the workshop demonstration is built around, sitting in the app right now.

Note there is currently **no chart component at all**. The AppKit `LineChart` was removed
when the screen was reframed, because its ECharts runtime cost 1,106 kB uncompressed
against 479 kB now. A charting exercise would reintroduce that; measure before proposing
it.

**ML is the weakest area, and the numbers say why.** Measured, not assumed:

| | |
|---|---|
| `nemweb_ml/tests/fixtures/history.json` | **6 rows** |
| `validate_training_eligibility` output | **train=3, validation=1, test=2** |
| Label | `label_price_spike_next_30m` |
| Spike variety in the governed snapshot | 2 intervals, 1 region, **0 negative prices** |

The starter itself is good — 196 lines across `features`, `split`, `contracts`, `train`,
`batch_score`, with leakage and chronological-split tests already enforced, and
`notebooks/train.py` stopping at a deliberate `NotImplementedError`. Only the data is
missing, and its own README says so plainly.

So there are two ML drafts:

- **`DRAFT-ml-refuse-to-train.md`** is completable today. It builds the eligibility gate
  the README says is required but that nothing enforces, and the 6-row fixture must
  **fail** it. Teaching an agent to refuse insufficient data is more valuable than
  teaching it to fit three rows.
- **`DRAFT-ml-train-baseline.md`** is the exercise people expect, and is blocked hardest
  of anything here. A 30-minute-ahead spike label needs **days to weeks** of history, so
  one authorised live cycle does not unblock it — it needs MMSDM archive backfill.

### On Genie Code and Omnigent

**Confirmed available: attendees work in Genie Code and Omnigent.** Every draft is written
to suit that — each names its starting files, its tests by name, and what evidence to
return, rather than assuming a particular shell.

The ML drafts suit an agent especially well: small code volume, but they demand reading a
README and three contract modules before writing anything. The predictable failure is
enthusiasm — training a model and reporting a metric on two test rows — and both drafts
make that the first thing the eval asks about.

#### One unresolved environment question, for a facilitator

The repository still describes itself as **local-first**, and that is not yet reconciled
with attendees working in Genie Code:

- `PRE-REQUISITES.md` line 4: *"local-first. Workspace features are used only when the
  named preflight item has"* been verified.
- Participants are required to *"have Git, Python 3.10 or later, and `uv` available
  locally"* and to *"be able to edit the pair record and run `make validate-local`"*.
- `workshop/track_c_app/Instructions.md` runs `make app-dev-mock`, which serves the app on
  `127.0.0.1`, and `make app-test` / `make lakebase-test`.
- **`PRE-REQUISITES.md` never mentions node or npm**, yet Track C's tests need both:
  `vitest` for 52 unit tests and `@playwright/test` for the 3 smoke tests. The cold
  Playwright install alone measured about five minutes.

So before scheduling the frontend and Lakebase drafts, confirm:

1. Can an attendee run `npm`, `vitest`, and Playwright in their working environment? If
   not, the frontend drafts still work but their **smoke-test evidence cannot be
   produced**, and each draft's evidence list needs adjusting to say so.
2. Can they reach `127.0.0.1` to see the app, or do they only ever see the deployed app?
   Several drafts ask for a screenshot.
3. **PF-9 is still recorded as `Unverified`** in `PRE-REQUISITES.md`. That is the item that
   approves the coding assistant and repository host and decides whether source may leave
   the tenant. Naming Genie Code and Omnigent there is a facilitator action; this file
   cannot do it.

None of this blocks raising the issues. It does determine which evidence an attendee can
actually return, so settle it before an exercise is marked `workshop-ready`.

## Two things that bind at 10–20 attendees

### 20 concurrent Lakebase computes, and that is the hard ceiling

Each attendee's branch needs its own compute.
[`attendee-isolation.md`](../../miniwiki/decisions/attendee-isolation.md) records the
verified limit: **20 concurrently active computes**, 500 branches. So branches are not
the constraint; **concurrent computes are**.

At 10 attendees there is comfortable headroom. **At 20 you are exactly at the ceiling
with none**, and the failure mode is a connection error rather than a queue. That page
already gives the remedy: request a limit increase before the workshop, or shard
attendees across a second project. Its own warning is worth repeating — *"Ask Support
early. Do not discover this at 09:45 on the day."*

The five-minute scale-to-zero helps: an attendee reading instructions is not holding a
compute. But every attendee actively running the app at the same moment is, and that is
precisely what happens in Stage 5.

### One issue per attendee is the wrong unit

Ten drafts do not cover twenty attendees, and they should not have to.

**Lakebase isolation makes the data collision-free** — each attendee has their own
branch, their own `app_write`, their own rows. Several people can do the same exercise
simultaneously and never see each other's data.

**The repository is where they collide.** Two attendees fixing the same file produce
conflicting pull requests. I checked for overlap across the drafts: only one pair shares
a file, `shift-handover` and `investigation-audit-trail`, both touching
`001_app_write_investigations.sql`. Everything else is disjoint.

So the practical shapes are:

| Approach | Works at 20? | Cost |
|---|---|---|
| Same exercise, several attendees, each on their own branch | **yes** | Their PRs conflict if contributed back |
| One exercise each, ten exercises, ten attendees | yes | Needs ~20 exercises for 20 attendees |
| Attendees fork, PR to their own fork | **yes, cleanly** | No shared contribution history |
| Pairs, so 20 attendees need 10 exercises | **yes** | Pairing is optional in the current tracks |

My recommendation: **do not write twenty exercises.** Let several attendees take the
same one — Lakebase already isolates the work — and treat a conflicting pull request as
a teachable moment rather than a failure. Ten well-rehearsed exercises beat twenty
untested ones, and the tracks are self-paced, so uptake will be uneven anyway.

## My recommendation

Raise all **thirteen** demonstrable drafts **without** `workshop-ready` until rehearsed.
Keep the three blocked ones as design records. One authorised live lander run unblocks
the rebid and congestion drafts plus the spike-detector and corrected-interval exercises;
it does **not** unblock ML baseline training, which needs archive backfill.

Rehearse these three first, because each repairs something genuinely broken today rather
than completing an invented task:

1. **`DRAFT-investigation-audit-trail.md`** — `updateInvestigation` destroys the previous
   decision text. There is no history table.
2. **`DRAFT-optimistic-concurrency.md`** — the README admits the gap; `version` exists
   and is ignored.
3. **`DRAFT-soft-delete-restore.md`** — `DELETE` is real and unrecoverable.

All three are Lakebase-central, all three are visible today, and all three end with a
participant having fixed a defect they can point at.
