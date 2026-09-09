# Stop an investigation jumping straight from closed back to open

**Track C · core · Lakebase central · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`, `area: lakebase`

## Operator outcome

An investigation moves through its lifecycle in a defensible order, and a reopened
investigation is visibly a reopening rather than looking like it was never closed.

## Fits Stage 4: 60 minutes

The table constrains the *set* of statuses but not the *order*:

```sql
status TEXT NOT NULL CHECK (status IN ('open', 'reviewing', 'closed'))
```

`updateInvestigation` accepts any of the three at any time. So `closed` → `open` is
allowed silently, with no record that a closed decision was reopened. For an audit
surface that is a real weakness, and it is the kind that only shows up when someone
asks "was this ever closed?"

Small, well-bounded, and it forces a genuinely interesting design conversation about
which transitions are legitimate.

**If time runs short, enforce the transitions and skip the reopen count.** A validated
state machine with tests is a complete result.

## Where to start

- `workshop/lakebase/migrations/001_app_write_investigations.sql` — the `CHECK`.
- `nemweb_app/server/db/investigations.ts:75` — `updateInvestigation`.
- `workshop/lakebase/contracts/investigation.schema.json` — the shared contract the CDF
  reducer also reads.

## Required change

- Decide and **write down** the legitimate transitions. A defensible default is
  `open → reviewing → closed`, with `closed → open` permitted only as an explicit
  reopen. Justify whatever you choose.
- Enforce it server-side, so an invalid transition is rejected with a message naming
  the attempted move.
- Record reopenings distinctly, so a reopened investigation is not indistinguishable
  from one that was never closed.
- Surface the rejection in the UI as a usable message, not a generic failure.

Enforce in the database or in the query layer — but say which, and why. If you choose
the query layer, explain what still writes directly to Postgres and could bypass it.

## 30-minute checkpoint

The transition table written down, and a test rejecting one invalid transition. The
reopen record and the UI message are the second half.

## Deterministic tests

- each legitimate transition succeeds;
- each illegitimate transition is rejected and leaves `status`, `decision` and
  `version` unchanged;
- a same-status update (`open` → `open`) resolves the documented way — decide whether
  it is a no-op or an error, and test it;
- a reopen is distinguishable from an investigation that was never closed;
- the rejection message names the attempted transition;
- existing tests in `investigations.test.ts` still pass unchanged.

## Agentic eval

Did the agent write the transition table down before coding, or infer it from the
implementation it wrote? Ask what happens on a same-status update — an unconsidered
answer means the state machine is incomplete. If it enforced in the query layer only,
ask what could bypass it.

## Evidence required

Approved plan including the transition table, changed files, test output covering every
legitimate and illegitimate transition, and a screenshot of the rejection message.

## Limits

Your own Lakebase branch. Forward-only migrations. Do not widen the existing status set.
Changing `investigation.schema.json` requires stating what breaks for the CDF reducer
that reads it.
