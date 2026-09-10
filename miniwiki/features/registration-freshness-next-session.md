# Next session: finishing registration attribution freshness

A sequenced continuation for issue #7 / PR #28. Read
[`../decisions/registration-coverage-metric.md`](../decisions/registration-coverage-metric.md)
and [`../now.md`](../now.md) first — this page is only the running order.

Nothing here authorises a merge, a deployment, a schedule change, a grant change,
or live data. Every step below is local, read-only against the workspace, or a
draft for a person to accept.

## Recover context first

```bash
git fetch fork
git checkout feat/registration-attribution-freshness
git log --oneline main..HEAD          # expect 7 commits, d202a02..e08a5ff
git status --short                    # expect clean
```

If the tree is not clean, stop and read what is there before doing anything else.

Baseline to reproduce before changing anything:

```bash
make test                             # 345 passed, 37 subtests
cd nemweb_app && npx vitest run       # 101 passed
```

`npm ci --include=dev` may be needed once, and Playwright needs
`npx playwright install chrome` in a fresh sandbox — without it the same three
smoke tests fail on unmodified `main` too, so that is an environment gap rather
than a regression.

## Step 1 — Re-review `e08a5ff` (blocking the draft)

`e08a5ff` repaired a blocking finding and has not itself been reviewed.
`adversarial-review` requires accepted repairs to return through the gates.

Use a **fresh, read-only reviewer that did not write the code**. Give it the
diff, this page, and the decision page, and ask for both a behavioural and a
structural verdict returning `REQUEST_CHANGES` or `PASS`.

Two things to point the reviewer at specifically, because they are the
least-verified parts of the change:

- **`MERGE WITH SCHEMA EVOLUTION`** in
  `nemweb_foundation/sql/app_serving/gold_nem_scada_generation_5min.sql`. It
  parses — verified against the SQL engine — but has never run against a
  deployed table. Ask what it does on a **cold** schema, where
  `CREATE TABLE IF NOT EXISTS` has just created the table already carrying the
  columns, and whether the `assert_true` guards between the CREATE and the MERGE
  still behave.
- **The restricted-AST threshold evaluator** in
  `tests/test_repository_layout.py`. It permits only integer literals,
  multiplication and addition. Ask whether that is genuinely safe against a
  hostile or merely unusual declaration, and whether the failure message tells a
  maintainer what to do.

A prompt alone does not enforce read-only access. If tool restrictions cannot be
verified, hand the artefacts to a person instead — an unavailable reviewer leaves
the gate **incomplete**, not passed.

## Step 2 — File the E1 issue

`io.py:281` stamps `F.lit("listing_or_http")` unconditionally, discarding the
`retrieval_fallback` that `lander.py:432` computes. It currently exists **only as
a note in the PR body**, so closing #28 loses it.

Verify each link before filing, rather than copying the claim:

```bash
grep -n "source_publication_basis" nemweb_foundation/agentic_energy/nemweb/pipeline/io.py
grep -n "source_publication_basis" nemweb_foundation/agentic_energy/nemweb/lander.py
grep -rn "section_stream" nemweb_foundation/agentic_energy/nemweb/pipeline/   # blast radius
grep -rn "source_publication_basis" nemweb_foundation/tests/                 # will a fix break a test?
```

Blast radius matters: if `section_stream` feeds every Bronze table, this is not a
registration-only defect. Say so in the issue, and state plainly whether existing
Bronze rows need a backfill or the fix is forward-only — or that it could not be
determined.

**Filing an issue is outward-facing. Ask before running `gh issue create`.**

## Step 3 — Lift the draft, if and only if the re-review passes

```bash
gh pr ready 28 --repo dgokeeffe/agentic-energy-on-databricks-public
```

Only a final `PASS` proceeds. Do not merge — this account has `pull` access only
and a maintainer merges.

## Step 4 — Raise E2 with a facilitator

All six artifacts in
`nemweb_foundation/agentic_energy/resources/nemweb_snapshot/v1/manifest.json`
have `source_publication_at: null`, so the default snapshot path renders "not
assessable". That is correct behaviour and an invisible demo: anyone assigning
#7 as a workshop exercise sees a feature that never shows its interesting state.

Re-cutting the snapshot changes fixture provenance and is **not** an agent
decision. Ask; do not do it unprompted.

## Step 5 — Clean up

`dev-saket` in the `agentic-energy` Lakebase project was created from
`production` at LSN `0/1E17F68` and holds a compute against the documented
20-per-project limit.

```bash
databricks postgres delete-branch \
  projects/agentic-energy/branches/dev-saket --profile DEFAULT
```

Confirm with the requester first — it is theirs, and deleting a branch is
irreversible.

## Deliberately not on this list

- **Deploying the foundation or running the serving job.** Both mutate the shared
  catalog `edp_entdata_exp_dev_landing`, and schema evolution on a shared serving
  surface from an unmerged branch is a facilitator decision.
- **Fixing E1 inside this branch.** It is a defect in the shared landing path;
  fixing it here would widen #7 well beyond its scope and needs its own tests
  and review.
- **Re-cutting the snapshot.** See step 4.

## Traps that already cost time

- **Clear `__pycache__` between mutation runs.** A same-size `<` → `>` mutation
  survived a file restore, because CPython validates bytecode cache on
  (mtime, size). A mutation can appear caught when it was not.
- **Never assert a bare substring over a whole file.** Three separate guards in
  this change were satisfied accidentally by correct code, and would also have
  been satisfied by deleting an explanatory comment. Assert on the AST, or on a
  scoped element.
- **No local test reaches a SQL engine or a Spark cluster.** A syntactically
  invalid `ALTER TABLE` passed every gate here. For SQL, probe the real engine
  against a deliberately nonexistent table: `PARSE_SYNTAX_ERROR` means the syntax
  is wrong, `TABLE_OR_VIEW_NOT_FOUND` means it parsed.
