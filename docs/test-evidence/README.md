# Test evidence

Dated records of what was executed and what it printed, for runs whose evidence
is worth keeping but which the automated suite cannot assert on its own.

## Records

| Date | Record | Scope | Result |
|---|---|---|---|
| 2026-08-12 | [`2026-08-12-foundation-fixture-run.md`](2026-08-12-foundation-fixture-run.md) | Deterministic fixture ETL run, manifest reconciliation, replay determinism, closure of `agentic-energy-93y` | PASS |
| 2026-08-12 | [`2026-08-12-metadata-contract-validation.md`](2026-08-12-metadata-contract-validation.md) | Contract validation hardening for `agentic-energy-zwh`: unvalidated required fields, mutation test, unchanged baseline | PASS |
| 2026-08-12 | [`2026-08-12-databricks-dev-deployment.md`](2026-08-12-databricks-dev-deployment.md) | Bundle deploy to the `dev` target, serverless run, byte-level local/serverless equivalence | PASS (with caveats) |
| ongoing | [`agent-token-usage.md`](agent-token-usage.md) | What the README token badge measures, how to refresh it, and why two totals are quoted | reference |

## Helpers

| File | Purpose |
|---|---|
| [`verify_bead_closure.py`](verify_bead_closure.py) | Asserts a foundation bead is closed **with** reconciliation evidence in its close reason, and that its dependents are unblocked. Exit 0 on success, 1 on any failure. |

## What belongs here

- Evidence for the **acceptance gate** in [`../workshop-acceptance.md`](../workshop-acceptance.md)
  that the suite cannot express: work-graph state, byte-level replay hashes,
  deployment preflight output.
- Checks that depend on **gitignored or per-machine state** — most obviously the
  Beads Dolt database (`.beads/.gitignore` ignores `embeddeddolt/`), which is why
  `verify_bead_closure.py` lives here instead of under `tests/`.

## What does not

- Anything that can be a normal test. If a check runs from a clean clone with no
  external state, put it in `tests/` where CI will run it every time. A document
  is weaker evidence than a passing assertion.
- Credentials, tokens, workspace-specific identifiers, private tenant detail, or
  organizer-only solution notes. Console captures must be reviewed for these
  before being committed.

## Conventions

- One file per run: `YYYY-MM-DD-<short-slug>.md`.
- Record the commit SHA, tool versions, and capture time in a header table, so a
  reader can tell what the evidence applies to.
- Paste **verbatim** console output. Do not retype or tidy results.
- State the limitations explicitly — which sections another person can reproduce,
  and what the run does *not* prove. Evidence that overclaims is worse than none.
