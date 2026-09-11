# Workshop handoff

Initial-supply learner and solution checkpoints are implemented, tested, published
as draft PRs, and rehearsed in an isolated snapshot environment. “Initial supply”
remains an explicit provisional interpretation: regional signed observed SCADA
output, not availability or total market supply. Historical evidence and the
bounded contract are in [workshop/scope.md](workshop/scope.md).

## Review checkpoints

| Purpose | Branch | Verified code commit | PR |
|---|---|---|---|
| Learner: implementation absent | `lab/initial-supply` | `50cd044eb357198df232d1fa17059fd3af58fddd` | [#42](https://github.com/dgokeeffe/agentic-energy-on-databricks-public/pull/42) |
| Completed solution | `solution/initial-supply` | `0caa75036bf65db0cada51f145ab841b860db9c8` | [#43](https://github.com/dgokeeffe/agentic-energy-on-databricks-public/pull/43) |

The handoff is a subsequent documentation-only change. Both code checkpoints
passed external CI, including fresh public-package setup. The deployed revision
was `2ba10867c954de7739e9c775989150b431b8a3c8`; its `src/`, `resources/`, and `app/`
are byte-identical to the verified solution checkpoint. Later changes fixed
public Python artifact URLs and strengthened facilitator verification tooling.
No merge or release tag was created or moved.

## Verified results

- 176 Python tests, 102 app tests, app typecheck/lint/build, and 5 prepared browser tests passed.
- Learner gate proved exactly six intended stub failures; the same six SQL behavior scenarios passed on the solution.
- Both `dev` and `lab` passed strict authenticated bundle validation with CLI 1.16.1 and explicit profile `daveok`.
- Initial refresh and non-destructive reset both succeeded. The new Gold MV passed all six remote checks after both runs.
- Genie reference SQL returned 8 supply, 2 effective-price and 22 fuel rows.
- Two publications and both rounds of managed sync updates succeeded. Full-column parity passed for 2 regional, 22 fuel and 28 unit rows; keys and row counts remained stable and CDF stayed enabled.
- After both sync rounds, all three authenticated app APIs and investigation create/list/update/stale-version rejection/delete passed. Temporary investigation records were removed.

## Start and operate

Learners use [the exercise](workshop/initial-supply/README.md): fresh checkout,
`make setup`, `make check`, `make lab-start-check`; implement the one helper and
run `make lab-test`. Do not deploy the learner stub.

Facilitators use [the runbook](workshop/RUNBOOK.md) for isolated provision,
validation, deployment, explicit read grants, refresh, publication, sync parity,
app checks and reset. [Genie preparation](workshop/genie/README.md) contains the
scoped questions, data context and executable reference SQL.
[Retirement](workshop/TEARDOWN.md) separates non-destructive reset from a reviewed
permanent deletion inventory.

## Resources and evidence

Rehearsal identifier: `supply0912`. Its project is `energy-supply0912`, with
dedicated `dev` and `lab` branches and registered Lakebase catalogs. Endpoints
are 0.5–1 CU with 300-second idle suspension. Only `lab` has deployed bundle
resources: one authored pipeline, four jobs, one SQL warehouse, two regular
schemas, three managed syncs, and app `energy-lab-supply0912`. Both schedules
are paused; the app is running for review. No fleet was provisioned.

Private configuration and exact workspace IDs, run/update IDs, full exports,
app checks and logs remain outside Git in the solution worktree:
`.databricks/workshop/rehearsal.json`, `resource-inventory.json`, and adjacent
evidence files. Target overrides and Lakebase bindings remain under
`.databricks/bundle/<target>/`. Do not copy baseline overrides into this checkout.

`main` and `baseline-v1` still resolve to
`0345aea12a1638c14126a1003bff692fa1b6018a`. The original baseline app remains
RUNNING and its pipeline IDLE. Its resources and data were not changed.

## Limits and next action

This is non-live synthetic data with NSW-only price coverage. Browser tests use
prepared responses; authenticated API checks are separate. Workspace UI deployment
was not exercised. Genie preparation is complete, but no Genie space, app/Genie
integration or Conversation API evaluation is claimed. Permanent teardown command
shapes were checked against the CLI but deletion was not executed.

No execution blocker remains. Next: review both draft PRs and the provisional
initial-supply definition. Keep solutions separate from the learner checkpoint
and shared baseline. Agree an attendee roster and sizing before any fleet setup.
