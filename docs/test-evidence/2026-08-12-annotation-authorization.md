# Test evidence — native annotation authorization boundary

| | |
|---|---|
| Captured (UTC) | 2026-08-12T06:09:37Z |
| Repository commit (base) | `d635d29923a30881c713b8bf7fec40dc17627af7` (branch `super_devs`) |
| Python | 3.10.12 |
| pytest | 9.1.1 |
| Beads issue | `agentic-energy-defect-annotation-identity` (local slug graph; the shared graph calls this `agentic-energy-5g3`) |
| Overall | **PASS** — 27 new tests, 10/10 mutations caught, 63 total passed, fixture output byte-identical |

## Headline: this was a missing feature, not a defect

The bead is titled as a defect ("annotation access does not enforce identity
boundaries"), which implies vulnerable code exists. It does not. Before writing
anything I searched the full history, not just the working tree:

```bash
git grep -n 'operator_annotations' -- .
# docs/challenge-spec.md:249  (prose only)

for b in $(git branch -r --format='%(refname:short)' | grep -v HEAD); do
  git grep -c 'operator_annotations' "$b" -- '*.sql' '*.py'; done
# 0 files across all 11 remote branches

git rev-list --all | while read c; do
  git grep -q 'operator_annotations' $c -- '*.py' '*.sql' && echo "FOUND in $c"; done
# (no output)
```

The scrubbed `scripts/lakebase.py` recovered from `1d51e14` is Lakebase
*provisioning* only (`ensure_project`, `ensure_branch`, `apply_schema`,
`grant_schema_privileges`) — no annotation CRUD, no `author_identity`.

So there was no unsafe code path to repair. This change **implements** the
boundary that `docs/challenge-spec.md` sections 8.2 and 8.4 specify. It is
committed as a feature. Labelling it a bug fix would misdescribe the work.

## What was added

`resources/lakebase/control_plane.sql` (+104 lines):

- `agentic_energy.operator_annotations` with all eight spec-8.2 columns.
- `author_identity TEXT NOT NULL DEFAULT current_user` — identity is assigned by
  the database. A client-settable `author_identity` is not an identity, it is
  free text: any annotator could file a note as another principal and the audit
  trail would faithfully record the forgery.
- `ENABLE` **and** `FORCE ROW LEVEL SECURITY`. The grants are table-wide, so
  without RLS any annotator could rewrite any other author's row. `FORCE` holds
  the table owner to the same boundary instead of exempting it.
- `FOR UPDATE ... USING (author_identity = current_user) WITH CHECK (...)`.
  `USING` decides which rows may be modified; `WITH CHECK` decides what they may
  become. With `USING` alone an author could hand a row they own to another
  identity and escape their own audit trail.
- `FOR INSERT ... WITH CHECK (author_identity = current_user)` binds new rows.
- `BEFORE UPDATE` trigger refreshing `updated_at`, incrementing `audit_version`,
  and pinning `author_identity`/`created_at` to their `OLD` values. Column
  defaults alone are stale-by-construction on UPDATE: `updated_at` would keep its
  insert value forever and `audit_version` would never leave 1, while still
  looking authoritative.
- Roles `agentic_energy_annotator` (SELECT/INSERT/UPDATE) and
  `agentic_energy_reader` (SELECT), guarded by a `pg_roles` check because
  `CREATE ROLE` has no `IF NOT EXISTS`. **No DELETE** — annotations are audit
  records, superseded via `status`, not destroyed.
- `gold_entity_key` validated by regex CHECK, because spec 8.2 notes a physical
  FK into a synced read-only relation is capability-dependent.

## A. Tests were written first and were genuinely red

```bash
uv run --offline --extra test python -m pytest tests/test_annotation_authorization.py -q
```

Against unmodified `control_plane.sql`, **18 of 22 failed**:

```text
FAILED test_native_annotations_table_is_declared
FAILED test_every_audit_and_identity_column_is_present[annotation_id]
FAILED test_every_audit_and_identity_column_is_present[audit_version]
FAILED test_every_audit_and_identity_column_is_present[author_identity]
FAILED test_every_audit_and_identity_column_is_present[created_at]
FAILED test_every_audit_and_identity_column_is_present[gold_entity_key]
FAILED test_every_audit_and_identity_column_is_present[note]
FAILED test_every_audit_and_identity_column_is_present[status]
FAILED test_every_audit_and_identity_column_is_present[updated_at]
FAILED test_author_identity_is_not_client_supplied
FAILED test_audit_timestamps_and_version_are_server_defaulted
FAILED test_annotation_status_is_constrained
FAILED test_note_cannot_be_blank
FAILED test_row_level_security_is_enabled_and_forced
FAILED test_update_policy_restricts_writes_to_the_authoring_identity
FAILED test_insert_policy_binds_new_rows_to_the_caller
FAILED test_annotator_role_cannot_delete_or_touch_gold
FAILED test_gold_entity_key_is_validated_logically
```

The 4 that passed did so vacuously (guards with nothing yet to guard); they
became load-bearing once the table existed.

## B. Two of my own tests were wrong, and were corrected

After implementation, two tests still failed. Both were **test defects, not
implementation defects**, confirmed before changing either side:

1. `test_annotator_role_cannot_delete_or_touch_gold` — scanned raw SQL text, so
   the prose in `-- No DELETE: annotations are audit records` registered as a
   DELETE grant. A comment *explaining* the boundary was read as a breach of it.
   `grep -n DELETE control_plane.sql` returned only that comment line; there is
   no DELETE grant. Fixed by stripping `--` comments before asserting privileges.
2. `test_annotations_do_not_write_back_to_gold` — banned *all* triggers on the
   table, which is broader than the spec-8.3 rule it claimed to enforce. The
   audit trigger is `BEFORE UPDATE` on the annotations table and assigns only
   `NEW.*` on its own row. Fixed to inspect trigger *bodies* for writes to other
   relations, which is the actual prohibition.

Recording this because "I changed the test until it passed" and "the test
asserted the wrong thing" look identical in a final green run.

## C. Mutation testing — 10/10 caught

Each security property was deliberately broken and the suite re-run:

```text
M1  drop DEFAULT current_user on author_identity  -> FAILED test_author_identity_is_not_client_supplied
M2  drop WITH CHECK from the UPDATE policy        -> FAILED test_authorship_cannot_be_reassigned_by_an_update
M3  remove FORCE ROW LEVEL SECURITY               -> FAILED test_row_level_security_is_enabled_and_forced
M4  grant DELETE to the annotator role            -> FAILED test_annotator_role_cannot_delete_or_touch_gold
M5  trigger body writes to a gold table           -> FAILED test_annotations_do_not_write_back_to_gold
M6  stop pinning author_identity to OLD           -> FAILED test_authorship_and_creation_time_are_immutable
M7  remove the status CHECK constraint            -> FAILED test_annotation_status_is_constrained
M8  stop incrementing audit_version               -> FAILED test_audit_trigger_makes_updated_at_and_version_move
M9  over-strict key regex (^[A-Z]{2})             -> FAILED test_gold_entity_key_constraint_accepts_real_pipeline_keys
M10 permissive key regex (.*)                     -> FAILED test_gold_entity_key_constraint_rejects_malformed_keys
```

Every mutation was caught by the specific test that owns that property.

M9/M10 matter most: they pin the `gold_entity_key` CHECK to keys the pipeline
*actually emits*. The test runs the fixture pipeline and validates every real
Gold key against the committed regex, so an over-strict constraint that would
block legitimate annotations fails loudly rather than passing a static check.

## D. No regression

```bash
uv run --offline --extra test python -m pytest        # 63 passed in 0.20s  (36 -> 63)
uv build --offline --wheel --out-dir dist            # agentic_energy_on_databricks-0.1.0-py3-none-any.whl
databricks bundle validate --strict -t dev           # Validation OK!
```

Fixture ETL unchanged — `bronze=11, silver=6, quarantine=3, gold=3` on both
runs, and `diff -r -x manifest.json` between two runs is empty. The manifest
differs only in the `run_id` explicitly passed to each run.

Structural SQL checks (no Postgres available offline): `$$` markers balanced (4,
even), parenthesis balance 0, single quotes even.

## Provenance and limitations

**What this proves.** The committed DDL *declares* the identity boundary spec 8.2
and 8.4 require, every clause is load-bearing under mutation, and the Gold key
constraint agrees with real pipeline output. These checks run from a clean clone
with no external state, so CI enforces them on every change.

**What this does not prove.** No statement here was executed against PostgreSQL.
The sandbox has no Database Instance, no `psql`, and no PyPI egress for
`psycopg`, so the SQL is **unparsed and unapplied**. Specifically unverified:

- That the artifact applies without syntax error, and applies twice (idempotence
  is asserted structurally — `IF NOT EXISTS`, `DROP POLICY IF EXISTS`, `pg_roles`
  guards — not by a second live apply).
- That RLS *enforces* the boundary at runtime: that annotator A genuinely cannot
  UPDATE annotator B's row. This is the central claim and it remains
  **untested against a live engine**.
- Whether Lakebase permits `FORCE ROW LEVEL SECURITY`, `CREATE ROLE`, and
  `plpgsql` triggers for the applying principal. If Lakebase restricts any of
  these, this artifact will need revision.
- Whether `current_user` is the correct identity anchor in Lakebase. It matches
  the existing convention in this file (`source_metadata.updated_by`,
  `metadata_versions.created_by`), but if the application connects via a single
  pooled service principal, `current_user` is the *app* identity, not the end
  user's — in which case per-user attribution must be threaded explicitly and
  this design needs revisiting. **This is the highest-risk open assumption.**

**Before deployment**, a facilitator must apply this to a real Lakebase branch
and record: the apply output, a second apply proving idempotence, and a
negative test where one role fails to modify another's row.

The bead is left open. Per `AGENTS.md`, closing the human review gate is not an
agent action.
