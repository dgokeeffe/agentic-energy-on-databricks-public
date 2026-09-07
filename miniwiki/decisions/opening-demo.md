# Opening demo decision

## Decision

Open the workshop with a demonstration that **the result of a data defect is
indistinguishable from the result of correct work**, so reviewing the result
cannot catch it. Then show that a test encoding the semantic rule catches it in
under a second.

Use the seeded Track B UTC processing-time defect as the material. It is local,
needs no workspace or preview capability, and is already covered by a committed
contract test.

Runtime is about six minutes. The intended placement is inside the 09:45–09:58
preflight slot, which is otherwise spent waiting on `make validate-local` (6m24s
measured, roughly five minutes of it a cold `@playwright/test` install). No
change to the [run of show](../../docs/facilitator/workshop-run-of-show.md)
clock has been made, and none is required for that placement.

## Why this framing

The workshop's subject is using coding agents on Databricks. The reviewable
artefact of agent work, in practice, is the result — not the diff and often not
the tests. That is the audience's actual habit and the demo has to speak to it
rather than correct it.

On a data platform the result is exactly what fails to reveal a semantic defect.
Nothing crashes, row counts hold, the schema validates and the numbers stay
plausible. So the honest lesson is not "agents are dangerous". It is: **this
class of defect is invisible to result review, whoever or whatever wrote it.** A
human would produce the same bug more slowly. What changes with agent speed is
how much depends on whether the rule was written down as an executable check.

## Measured evidence

Reproduced with the defect's own arithmetic (`from_utc_timestamp` →
`date_format` → `to_timestamp` on `Australia/Brisbane`).

The pipeline should write the UTC instant `2026-09-05 14:00:00`. With the defect
it writes `2026-09-06 00:00:00` — a ten-hour shift, and still a well-formed
timestamp.

A reviewer's view of four rows: row count 4, zero nulls, valid schema, plausible
prices, timestamps neatly ordered. The defect additionally makes `interval_end`
and `ingested_at` *agree*, which reads as more coherent than the correct output
where the two differ by ten hours because one is market time and one is
processing time.

Freshness monitor, "alert if data older than 15 minutes":

| Scenario | Correct | With defect |
|---|---|---|
| Data 3 minutes old | age `0:03:00`, no alert | age `-1 day, 14:03:00`, no alert |
| Source 9 hours stale | age `9:00:00`, **alert fires** | age `-1 day, 23:00:00`, **no alert** |

The defect makes data appear to arrive from the future, so age goes negative and
the staleness alarm can never fire. Freshness monitoring is lost while the
dashboard still looks correct. That is the operator-facing consequence worth
showing.

Red/green/restore cycle, all verified locally:

| Step | Result |
|---|---|
| Clean contract test | PASS |
| Defect applied | RED at `test_processing_timestamps_utc.py:73`, exact message |
| Honest fix | PASS; foundation suite 282 passed, 52 subtests |
| Column renamed to dodge the AST check | still caught, at line 78 |
| Patch reversed | `io.py` SHA-256 `c9839cce…`, `git diff --quiet` clean |

The contract test is an AST test. It rejects `date_format`, `from_utc_timestamp`
and `to_timestamp` in expressions producing `ingested_at`,
`silver_published_at` or `gold_published_at`, and separately asserts
`observed == PROCESSING_COLUMNS`. Renaming a column to escape the first
assertion therefore fails the completeness assertion at a different line. Making
the test green requires fixing the code.

## Alternatives tried and discarded

Each was discarded on evidence, and the negative results are the useful part.

**1. App and Lakebase product tour.** Showed the artefact an agent built — a
regional operations screen with freshness labels, an investigation write to
Lakebase, CDF reduction — rather than agent engineering. Wrong subject for this
workshop. Two findings survive from building it: `make app-dev-mock` fails
because `client/vite.config.ts` sets `middlewareMode: true`, so bare `vite` exits
with `Error: HTTP server not available`; the working local path is
`npm run build:client` then `vite preview` (verified HTTP 200). And the
Investigation journal POSTs to `/api/investigations`, which needs a live
Lakebase (`PGHOST`, `LAKEBASE_ENDPOINT`), so the write fails under a
client-only preview.

**2. "Watch the agent get caught."** Disproved. A real agent run
(`claude-opus-4-8`, fresh context, isolated worktree from HEAD, naive prompt
"this test fails, make it pass") produced the correct fix in **36 seconds**, seven
tool calls, one edit. Its stated reasoning was to restore
`F.current_timestamp().alias("ingested_at")`, and it correctly explained the
empty diff as the patch and the fix cancelling out. Verified independently: SHA
byte-identical to HEAD, contract test green, no stray files. Staging a failure
that does not occur would be theatre, which this workshop cannot afford.

Worth retaining: the agent never ran the wider suite, never checked that
`interval_end` remained fixed AEST, and never confirmed the other two processing
columns. Nothing in its prompt required any of that. The gap between "the test I
was given passes" and "the system is still correct" is what the eval and
independent review gates exist to close.

**3. SHA fingerprint verification as the teaching point.** Discarded. It is an
agent-to-agent verification method, not something a human reviewer does. Correct
for the parent session to use when checking a child's claim; wrong as workshop
material.

## What this does not claim

One agent trial on one defect with an unusually crisp AST test. It does not
support "agents reliably fix data bugs". A vaguer issue with weaker tests is
where agents wander, and that is the honest caveat for the room.

The fixture arithmetic is a local reproduction of the defect's behaviour, not
observed pipeline output. Real Gold data in the dev target is thin: 2 rows and 1
region in `gold_nem_app_region_status`, 2 binding constraints, 2 interconnector
flows. Prepared fixtures are richer than live data here, so the demo does not
depend on a workspace.

## Smallest useful next action

Rehearse the six-minute narration and decide whether the freshness-monitor table
or the four-row table opens the demo. Neither needs code.

Then decide the handoff line. Current intent is to close on the gates and point
at the six `workshop-ready` issues rather than one ticket, noting that #8
("separate source publication delay from pipeline freshness") is the same
distinction the demo collapses.

## Open questions

- Does the demo displace anything in the 09:45–09:58 slot in practice, or does
  the `validate-local` wait genuinely absorb it? Only a rehearsal answers this.
- Should the thin snapshot fixture be thickened so the business-facing issues
  (#6, #9, #12) have visible data at the 10:18 inspection? Unrelated to this
  demo, but it affects the same first hour.
- Is a recorded agent run worth including as a second beat now that we know the
  agent succeeds? It would show speed and competence honestly, but adds runtime.
