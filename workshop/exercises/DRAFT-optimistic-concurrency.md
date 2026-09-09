# Stop two analysts silently overwriting each other

**Track C · advanced · Lakebase central · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: advanced`, `area: app`, `area: lakebase`

## Operator outcome

When two people edit the same investigation, or one person's request is retried on a
flaky network, nobody's decision is silently discarded. The loser is told, and can
see what changed.

## Fits Stage 4: 90 minutes, and it is the fullest of these

This is a **real, already-documented defect**. `nemweb_app/README.md` states it
outright:

> Investigation creation is not yet idempotent across an uncertain network retry.
> This UI prevents no server-side duplicate by itself.

And the fix is half-built: the table already has `version BIGINT NOT NULL DEFAULT 1
CHECK (version > 0)`, but `updateInvestigation` never checks it. So the column exists
purely as decoration — a last-write-wins overwrite with a version number that lies.

Fixing a known bug in code that already has the right column, and being able to *prove*
the race, is the most satisfying result available in this slot. It needs no market data.

**If time runs short, do the concurrency half only.** Optimistic locking with a
reproduced-then-fixed race is a complete, defensible result. Idempotent creation is a
second, separable fix — say in your handover that you left it, and why. Attempting both
badly is worse than doing one well.

## Where to start

- `nemweb_app/server/db/investigations.ts:35` — `createInvestigation`, the
  non-idempotent path.
- `nemweb_app/server/db/investigations.ts:75` — `updateInvestigation`, which ignores
  `version`.
- `nemweb_app/README.md` — the paragraph admitting the gap.
- `workshop/lakebase/contracts/investigation.schema.json` — the shared contract.

## Required change

Two related fixes.

**Optimistic concurrency on update.** The client sends the `version` it read. The
server updates only if the stored version still matches, and otherwise rejects with a
conflict the UI can explain. The message must say what happened, not just fail.

**Idempotent creation.** An uncertain retry of the same creation must not produce a
second row. Choose a mechanism — a client-supplied idempotency key with a unique
constraint, or a natural-key constraint on
`(nem_event_key, region_id, interval_end, operator_identity)` — and justify the
choice, including what it forbids that was previously allowed.

Do not solve the race by serialising all writes, and do not solve idempotency by
checking for an existing row before inserting: that check is itself a race.

## 30-minute checkpoint

A test that reliably reproduces the lost update: two reads, two writes, second wins
silently. **Get this failing test first.** If you do not have it by 30 minutes, you will
not have time for both halves — drop idempotent creation and finish the concurrency fix
properly.

## Deterministic tests

- two concurrent updates from the same starting version: one succeeds, one is
  rejected with a conflict, and the rejected decision text is **not** in the table;
- the test above **fails before the fix**. Demonstrate that, do not assert it;
- a conflict surfaces a message naming the conflict, not a generic error;
- the same creation submitted twice yields exactly one row;
- two genuinely different investigations for the same interval and region are both
  still allowed, unless your chosen constraint deliberately forbids it — in which case
  test and document that;
- `version` increments by exactly one per successful update;
- a rejected update leaves `updated_at` unchanged.

## Agentic eval

Did the agent prove the race exists before fixing it? A concurrency fix with no
failing pre-fix test is unverified. Did it avoid check-then-insert? Ask what its
constraint now forbids that used to be permitted, and whether any existing test
depended on that. Did it update the README paragraph that documents the gap?

## Evidence required

Approved plan, changed files, the pre-fix failing test output and the post-fix passing
output, the migration if a constraint was added, and the README paragraph updated to
describe the behaviour now.

## Limits

Your own Lakebase branch. No table lock or global serialisation as the mechanism. No
change to `investigation.schema.json` without stating what breaks for the CDF reducer
that reads it. Forward-only migrations.
