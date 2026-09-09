# Make a deleted investigation recoverable

**Track C · core · Lakebase central · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`, `area: lakebase`

## Operator outcome

An analyst who deletes an investigation by mistake can get it back. A governed record
of a market decision is not destroyed by one click.

## Fits Stage 4: 60 minutes

`deleteInvestigation` at `nemweb_app/server/db/investigations.ts:93` issues a real
`DELETE`:

```sql
DELETE FROM app_write.investigations
WHERE investigation_id = $1::uuid AND operator_identity = $2
RETURNING investigation_id
```

The row is gone. In a workshop whose whole framing is auditable governed decisions,
the app can permanently destroy one with no recovery and no trace that it existed.

Short, self-contained, and the payoff is obvious: delete something, get it back.

**If time runs short, skip the restore UI.** Soft delete plus a test proving the row
survives and is hidden is a complete result; restore via a direct `UPDATE` is fine.

## Where to start

- `nemweb_app/server/db/investigations.ts:93` — `deleteInvestigation`.
- `workshop/lakebase/migrations/001_app_write_investigations.sql` — the table.
- `nemweb_app/server/db/investigations.test.ts` — extend this.

## Required change

- A migration adding a nullable deletion timestamp and the identity that deleted it.
- `deleteInvestigation` sets those instead of removing the row.
- `listInvestigations` excludes soft-deleted rows by default.
- A restore path clearing the deletion, recorded like any other change.

Do not add a `DELETE` behind a flag. The point is that the row survives.

## 30-minute checkpoint

Migration applied, `deleteInvestigation` soft-deleting, and a test proving the row is
still in the table but absent from the list. Restore is the second half.

## Deterministic tests

- after delete the row is still present in the table and absent from the default list;
- restore returns it to the list with its decision text intact;
- deleting an already-deleted investigation does not change the original deletion
  timestamp or identity;
- an analyst cannot soft-delete another analyst's investigation — the existing
  `operator_identity` predicate must survive your change;
- the deleting identity comes from the trusted request context, not request JSON;
- re-running the migration on a migrated branch is a no-op.

## Agentic eval

Did the agent keep the `operator_identity` predicate, or drop it while rewriting the
statement? That would let anyone delete anyone's record — ask for the test that proves
it still holds. Did it leave any `DELETE` path in place?

## Evidence required

Approved plan, the migration, changed files, test output, and a before/after row count
showing the row survived a delete.

## Limits

Your own Lakebase branch. Forward-only migrations. No hard `DELETE` retained. Do not
disable CDF; dropping a schema, resetting a branch, or deleting a project each need a
separate human decision.
