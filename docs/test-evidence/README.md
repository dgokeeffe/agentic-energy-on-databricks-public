# Test evidence

Dated records of commands and external state that the automated suite cannot
assert on its own. Tests remain the stronger home for reproducible clean-clone
checks; this directory is for reviewed execution evidence.

## Records

| Date | Record | Scope | Result |
|---|---|---|---|
| 2026-08-12 | [`2026-08-12-foundation-fixture-run.md`](2026-08-12-foundation-fixture-run.md) | Deterministic fixture ETL, manifest reconciliation and replay | PASS |
| 2026-08-12 | [`2026-08-12-metadata-contract-validation.md`](2026-08-12-metadata-contract-validation.md) | Required-field contract hardening and mutation test | PASS |
| 2026-09-03 | [`nemweb-e2e-2026-09-03.md`](nemweb-e2e-2026-09-03.md) | Imported public three-cycle evidence; not proof of this packaged deployment | HISTORICAL |
| 2026-09-04 | [`workshop-integration-2026-09-04.md`](workshop-integration-2026-09-04.md) | Interim stop, restoration decision, and repository checks | SUPERSEDED |
| 2026-09-05 | [`workshop-integration-2026-09-05.md`](workshop-integration-2026-09-05.md) | Snapshot foundation, app, Triggered sync, CDF, and current-state integration | PASS WITH RECORDED LIMITS |
| 2026-09-05 | [`nemweb-e2e-2026-09-05.md`](nemweb-e2e-2026-09-05.md) | Three consecutive scheduled live NEMWEB cycles, 15 critical-subject rows | PASS |

The final NEMWEB run is named `nemweb-e2e-YYYY-MM-DD.md`. Do not create a PASS
record until the live validator accepts three consecutive five-minute cycles.

## Required NEMWEB evidence

A dated NEMWEB record includes:

- commit/worktree state, source versions and adapted-file provenance;
- exact local, build, strict-bundle and workspace commands with outcomes;
- snapshot manifest hash, counts and two-root deterministic reconciliation;
- deployed resource names without private URLs or tenant identifiers;
- metric-view reconciliation and terminal benchmark/dashboard SQL results;
- one row per critical subject per cycle from
  `nemweb_foundation/scripts/capture_nemweb_evidence.py` (at least 15 rows across three cycles);
- exact pipeline update IDs, terminal states and filtered-event failure details;
- source publication lag separately from source-to-Gold and landed-to-Gold lag;
- T+1 unit target/availability evidence separately from five-minute SCADA actuals;
- failures, fixes, independent review findings and unresolved external limits.

Run:

```bash
uv run --project nemweb_foundation python nemweb_foundation/scripts/validate_nemweb_live.py /tmp/nemweb-evidence.json
```

before copying `/tmp/nemweb-evidence.md` into the dated record. A configured
schedule, successful bundle validation or green top-level pipeline state is not
live cadence evidence.

## No-change cycles

A cycle with no new AEMO row is valid only when the evidence pack records an
unchanged source listing filename, publication timestamp, interval/checksum
signature and a successful freshness check against Bronze. Never add a fixture
or manufactured row to make a cadence table pass. A source-changed cycle whose
binding Gold result remains unchanged is labelled separately; it is not “no new
source”.

## Conventions

- Use one file per run: `YYYY-MM-DD-<short-slug>.md`, except the explicit
  `nemweb-e2e-YYYY-MM-DD.md` closure format.
- Record commit SHA, dirty-state summary, tool versions and UTC capture time.
- Paste verbatim console output; do not retype or tidy results.
- State what a run does **not** prove. Snapshot evidence is always marked
  `live_evidence: false`.
- Never include credentials, tokens, private workspace URLs, tenant identifiers
  or organiser-only configuration. Review captures before committing.
- Do not stage an evidence record until every claim can be traced to retained
  command output or query results.

## Public historical evidence imported on 2026-09-05

`nemweb-e2e-2026-09-03.md` and `nemweb-e2e-evidence.json` are byte-for-byte
artifacts from public commit `4b664ce`. They prove that public deployment only;
they do not prove deployment, sync, CDF, App, or ML execution for the newly
packaged `nemweb_foundation/` and starters on this branch.
