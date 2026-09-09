# Write the shift handover an operator would actually read

**Track C · core · Lakebase central · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`, `area: lakebase`

## Operator outcome

An analyst finishing a shift can hand over in one click: every open investigation,
what was decided, what is still unresolved, and the market evidence each decision
rested on. The next analyst reads one screen instead of asking.

## Fits Stage 4: 60–90 minutes

The payoff arrives early and improves from there. You write real rows into your own
Postgres branch and immediately see them on screen — no waiting on a pipeline, no
market variety required, nothing shared with another attendee.

It is also the one exercise here where **you generate the interesting data yourself**.
The snapshot has two intervals and no price spikes, but your handover gets as rich as
you make it, because the investigations are yours.

**If time runs short, cut the grouping.** A flat list of unresolved investigations with
a correct count is a complete result. Grouping and styling are the polish.

## Where to start

- `workshop/lakebase/migrations/001_app_write_investigations.sql` — the existing
  table: `status` (`open`/`reviewing`/`closed`), `decision`, `evidence_reference`,
  `version`, `operator_identity`, `team_identifier`.
- `nemweb_app/server/db/investigations.ts` — full CRUD already exists
  (`createInvestigation`, `listInvestigations`, `updateInvestigation`,
  `deleteInvestigation`). Extend it; do not start over.
- `nemweb_app/client/src/components/InvestigationPanel.tsx` — the existing journal UI.

## Required change

Add a handover view over the investigations already in your branch.

- A query returning open and reviewing investigations, newest first, grouped so the
  reader sees unresolved work before closed work.
- Each entry shows the region, the market interval in **fixed AEST**, who recorded it,
  the decision text, and the evidence reference.
- A count of what is unresolved, prominent enough to be the first thing read.
- Empty state that says the shift is clear, not a blank panel.

`operator_identity` must come from the trusted `x-forwarded-user` request context,
never from request JSON. `trustedOperatorIdentity` in `investigations.ts` already does
this — use it.

## 30-minute checkpoint

Investigations you created appear in a handover list with the unresolved count correct.
If you are not there by 30 minutes, drop the grouping and get the flat list working.

## Deterministic tests

- an open and a reviewing investigation both appear; a closed one does not appear in
  the unresolved count;
- the unresolved count matches the rows returned;
- an empty branch renders the clear-shift state rather than a blank panel;
- market intervals render in fixed AEST and processing timestamps in UTC, matching
  the existing `domain/time.ts` helpers;
- identity is read from the request context, and a request supplying
  `operator_identity` in its JSON body cannot override it;
- every Postgres value is a bind parameter.

## Agentic eval

Did the agent extend the existing CRUD rather than writing a parallel query layer?
Did it use `trustedOperatorIdentity` instead of accepting identity from the body? Did
it keep AEST and UTC distinct? Ask it to show the test that proves a JSON-supplied
identity is ignored.

## Evidence required

Approved plan, changed files, test output, a screenshot of both the populated and
empty states, and the row count in your branch before and after.

## Limits

Your own Lakebase branch only. No schema change outside `app_write`, no deployment
beyond your own app, no shared resource. Do not write market data into Postgres — the
lakehouse owns that; Postgres owns your decisions.
