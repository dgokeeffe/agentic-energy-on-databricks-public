# Make an investigation's history impossible to lose

**Track C · core · Lakebase central · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`, `area: lakebase`

## Operator outcome

When someone asks "why did we decide that, and who changed their mind?", the answer is
in the data. An investigation's decision can be revised, and every earlier version
survives with who wrote it and when.

## Fits Stage 4: 60–90 minutes

`updateInvestigation` currently overwrites `decision` in place. The previous text is
**gone** — there is no history table and no trigger. So the app can already lose the
reasoning behind a decision, which is exactly what the workshop's governance framing
says must not happen.

You will see the bug happen, then fix it. That arc fits the slot well, and it needs no
market variety at all: the data is what you type.

**If time runs short, cut the UI.** The migration plus a transactional write plus the
forced-failure test is the complete result. Reading history through the panel is the
polish — a `SELECT` against your branch proves it just as well.

## Where to start

- `workshop/lakebase/migrations/001_app_write_investigations.sql` — note `version
  BIGINT NOT NULL DEFAULT 1 CHECK (version > 0)`. The column exists; nothing
  increments it into a history.
- `nemweb_app/server/db/investigations.ts:75` — `updateInvestigation`, the
  destructive write.
- `nemweb_app/server/db/investigations.test.ts` — the existing test file to extend.

## Required change

Preserve prior versions on update.

- A new migration adding a history table in `app_write`, keyed on
  `investigation_id` and `version`.
- `updateInvestigation` writes the prior row to history and increments `version`, in
  **one transaction**, so a failure cannot leave history and current disagreeing.
- The panel shows the current decision, with earlier versions available and each
  labelled with its author and timestamp.
- Migrations stay forward-only and idempotent, matching the existing
  `CREATE TABLE IF NOT EXISTS` style.

Do not solve this by preventing edits. The point is that revision is legitimate and
must be recorded.

## 30-minute checkpoint

Migration applied and a test proving an update leaves a history row behind. If you are
not there by 30 minutes, skip the UI entirely and spend the time on the transaction and
its forced-failure test — that is the part that matters.

## Deterministic tests

- one update produces exactly one history row and `version` becomes 2;
- three updates produce three history rows with versions 1, 2, 3 and no gaps;
- the current row always holds the latest decision;
- a failed update leaves **neither** a history row nor a version bump — prove this by
  forcing a failure inside the transaction, not by reasoning about it;
- re-running the migration on an already-migrated branch is a no-op;
- history records the author from the trusted request context, not from request JSON.

## Agentic eval

Did the agent make the write transactional, or write history and current separately
and assume both succeed? Ask it to demonstrate the forced-failure test actually
failing before the fix — a test never seen to fail is indistinguishable from one that
cannot fail. Did it keep migrations idempotent?

## Evidence required

Approved plan, the migration, changed files, test output including the forced-failure
case, and a screenshot showing a decision with at least two versions.

## Limits

Your own Lakebase branch. Forward-only migrations; no destructive schema change, no
`DROP`, no branch reset. Do not disable CDF. Deleting a synced table, dropping a
schema, resetting a branch, or deleting a project each need a separate human decision.
