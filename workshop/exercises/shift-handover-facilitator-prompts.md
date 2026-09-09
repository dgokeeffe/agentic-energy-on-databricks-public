# Shift-handover facilitator prompts

This packet supports the visible Track C shift-handover exercise in
[`DRAFT-shift-handover.md`](DRAFT-shift-handover.md). It compares a planned,
contract-first agent run with a deliberately underspecified vibe-coded run.

The comparison is a facilitator demonstration, not a productivity benchmark.
Use the same clean starting commit, the same attendee branch, and the same
acceptance criteria for both runs. Do not expose credentials or use shared
resources. Keep the shoddy run separate from participant work, and reset the
working tree before the good run.

## Shared brief

The operator needs a shift-handover view over investigations already stored in
the attendee's `app_write` Lakebase schema. The view must show unresolved work
first, count open and reviewing investigations, show the region, fixed-AEST
market interval, trusted operator, decision, and evidence reference, and show a
clear empty state. Closed investigations must not count as unresolved.

The existing CRUD and identity boundary are part of the contract:

- `nemweb_app/server/db/investigations.ts` owns investigation persistence and
  already exposes trusted identity from `x-forwarded-user`.
- `nemweb_app/client/src/components/InvestigationPanel.tsx` is the existing UI
  entry point.
- `workshop/lakebase/migrations/001_app_write_investigations.sql` defines the
  writable schema.
- Market intervals are fixed AEST; processing timestamps are UTC.
- Postgres values must use bind parameters.
- The lakehouse owns market data; Lakebase owns operator decisions.

The first visible checkpoint is a populated handover list with a correct
unresolved count. If the grouping is not ready, a flat correct list is an
acceptable checkpoint.

## Planned run: contract-first prompt

Use this in a fresh assistant conversation from a clean worktree. Approve the
plan before allowing implementation.

```text
You are implementing the self-contained shift-handover exercise in
workshop/exercises/DRAFT-shift-handover.md. Work only in the attendee's own
Track C app/Lakebase scope. Do not deploy, access live NEMWEB, change shared
resources, alter the foundation bundle, or expose credentials.

Goal: add a visible handover view over existing investigations in the app's
app_write schema. Open and reviewing investigations are unresolved; closed
investigations are not. Show unresolved count first, list unresolved work newest
first, and show region, fixed-AEST market interval, trusted operator identity,
decision text, and evidence reference. Render an explicit clear-shift empty
state.

Before editing:
1. Read AGENTS.md, QUICKSTART.md, workshop/track_c_app/Instructions.md,
   workshop/exercises/DRAFT-shift-handover.md,
   nemweb_app/server/db/investigations.ts,
   nemweb_app/client/src/components/InvestigationPanel.tsx,
   workshop/lakebase/migrations/001_app_write_investigations.sql, and the existing
   time helpers and tests.
2. Trace the existing CRUD, request identity boundary, query conventions, and
   component data flow. Do not create a parallel database or query layer.
3. State the smallest approved file set, the API shape, the SQL ordering/filter,
   the empty-state behaviour, and the tests you will add or update. Call out
   uncertainty before writing code.

Implementation constraints:
- Use trustedOperatorIdentity from request context; JSON operator_identity must
  never override it.
- Use bind parameters for every Postgres value.
- Keep market interval rendering fixed AEST and processing timestamps UTC.
- Keep Lakebase limited to operator decisions and investigation state.
- Preserve existing create/update/delete behaviour unless a test proves a
  necessary compatible change.
- Do not add a schema outside app_write.

Validation:
- First write failing tests for open/reviewing/closed filtering, unresolved
  count, empty state, AEST/UTC rendering, trusted identity, and bind parameters.
- Run the focused server and client tests, then make lakebase-test and the
  relevant app test/typecheck commands.
- Start the mock app only if it is available locally; do not substitute a
  screenshot for test evidence.
- Report changed files, commands and exit codes, the populated and empty-state
  observations, remaining uncertainty, and the human decision needed next.

Stop after the implementation and validation report. Do not commit, push, merge,
deploy, provision a branch, or change a schedule.
```

### Expected good-run behaviour

A good run should produce a short plan before edits, identify the existing
identity and time contracts, make a small change, add focused tests, and show
both populated and empty states. It should explicitly say if app or Lakebase
checks cannot run in the current environment.

## Shoddy run: deliberately vague vibe-coded prompt

Use only in an isolated demonstration worktree. Do not use its output as an
approved participant solution.

```text
Make the shift handover feature look good in the app. Use the existing
investigations and Lakebase stuff, add whatever API and UI code is needed, and
make the tests pass. Show open items first, include the important details, and
make a nice empty state. Keep it simple and do it quickly.
```

### What the shoddy run is intended to expose

Review the result for predictable failures rather than rewarding speed:

- It may invent a second query or persistence path instead of extending CRUD.
- It may count closed rows as unresolved or sort incorrectly.
- It may accept `operator_identity` from request JSON rather than trusted
  request context.
- It may render UTC as local/AEST or convert fixed-AEST market intervals.
- It may interpolate SQL values instead of using bind parameters.
- It may put market data into Lakebase.
- It may update snapshots, weaken tests, or claim success without running them.
- It may attempt deployment or workspace access without facilitator release.

Record actual findings with file and test evidence. Do not manufacture a failure:
a vague prompt can still produce a correct result. If it does, record that and
explain which missing instructions were not needed for this case.

## Comparison record

Retain the exact prompt, starting commit, changed files, commands, exit codes,
screenshots or screen observations, and the human/reviewer decision for each
run. Label each result as `actual agent output`, `actual human output`, or
`facilitator-prepared output`. Record `not-run` when a check is unavailable.

| Check | Planned run | Shoddy run |
| --- | --- | --- |
| Existing CRUD reused |  |  |
| Trusted identity preserved |  |  |
| Fixed AEST and UTC kept distinct |  |  |
| Closed rows excluded from unresolved count |  |  |
| Empty state visible |  |  |
| Bind parameters used |  |  |
| Focused tests run and green |  |  |
| Local/mock app observation |  |  |
| Unapproved workspace action attempted |  |  |
| Reviewer decision and residual risk |  |  |

This comparison does not replace the required plan approval, deterministic
tests, independent review, or human disposition for the actual participant
change.
