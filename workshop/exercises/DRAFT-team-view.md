# Use the team column the app already writes but never reads

**Track C · core · Lakebase central · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`, `area: lakebase`

## Operator outcome

An analyst can see what their team is investigating, not only what they personally
recorded, so two people on the same desk stop duplicating each other's work.

## Fits Stage 4: 60–75 minutes

`team_identifier TEXT NOT NULL` is in the table and is written on every insert. It
appears **once** in `investigations.ts` — in the `INSERT`. Nothing reads it. No query
filters, groups, or displays it.

So the app collects team attribution and then throws it away, which is a satisfying
kind of gap to close: the data is already there and correct, and you are building the
first thing that uses it.

**If time runs short, do the read path only.** A team-scoped list is a complete result;
the per-team summary counts are the polish.

## Where to start

- `nemweb_app/server/db/investigations.ts:35` — the `INSERT`, the only place
  `team_identifier` appears.
- `nemweb_app/server/db/investigations.ts:63` — `listInvestigations`, which ignores it.
- `nemweb_app/client/src/components/InvestigationPanel.tsx`.

## Required change

- A team-scoped read returning investigations for the requesting analyst's team.
- A visible distinction between "mine" and "my team's", so attribution is never lost.
- Per-status counts for the team, so the shape of the workload is readable at a glance.
- Team membership derived from the trusted request context, never from a request-supplied
  team name.

That last point is the crux. If a caller can pass their own `team_identifier` on a read,
they can read any team's investigations. Decide where team membership comes from and
defend it.

## 30-minute checkpoint

A team-scoped list returning rows for the right team and not for another. Counts and the
mine-versus-team distinction are the second half.

## Deterministic tests

- the team read returns rows for that team and excludes another team's rows;
- a request supplying a different `team_identifier` cannot read that team's rows;
- an analyst's own investigations remain individually attributed within the team view;
- per-status counts match the rows returned;
- an analyst whose team has no investigations sees an empty state, not an error;
- existing single-analyst behaviour is unchanged.

## Agentic eval

Did the agent accept a team identifier from the request, or derive it from trusted
context? This is the exercise most likely to produce a quiet authorisation hole, so ask
directly for the test that proves cross-team reads are refused.

## Evidence required

Approved plan, changed files, test output including the cross-team refusal, and a
screenshot showing the same branch rendered for two different teams.

## Limits

Your own Lakebase branch. No team identifier accepted from request JSON. No cross-team
read. No new shared table; the existing column is sufficient.
