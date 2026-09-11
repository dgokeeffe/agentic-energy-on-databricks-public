# Facilitator runbook

Work in a fresh checkout dedicated to this workshop. Never copy the baseline's
private override files: they point at working baseline resources. Use an explicit
profile and a new deployment identifier. The rehearsal record in `HANDOFF.md`
states what has actually been tested.

## Learner checkpoint

Use `lab/initial-supply` and follow `workshop/initial-supply/README.md`. The six
exercise scenarios intentionally fail at the stub; baseline checks must pass.
Participants implement the helper and submit their diff and test output for
review. Their local SQLite tests are not a Spark execution claim.

## Isolated solution deployment

```sh
git clone --branch solution/initial-supply https://github.com/dgokeeffe/agentic-energy-on-databricks-public.git energy-solution
cd energy-solution
make setup
make check
make lab-test
# Choose a fresh lowercase identifier, at most 18 characters.
make provision PROFILE=<profile> CATALOG=<catalog> DEPLOYMENT_ID=<new-id> TARGET=lab
make provision PROFILE=<profile> CATALOG=<catalog> DEPLOYMENT_ID=<same-new-id> TARGET=dev
make validate PROFILE=<profile> TARGET=dev
make validate PROFILE=<profile> TARGET=lab
make deploy PROFILE=<profile> TARGET=lab
make refresh PROFILE=<profile> TARGET=lab
```

The retained provisioning automation uses dedicated dev/lab Lakebase branches,
0.5–1 CU endpoints, five-minute idle suspension, an isolated runtime principal,
and ignored target overrides. Schedules stay paused. Do not provision a fleet
without an attendee roster and agreed sizing. Inspect the generated configuration
before deploying; ensure its names differ from every existing baseline resource.

The solution adds a Gold MV to the one authored pipeline. It does not add a
serving/sync/API contract. To bring up the unchanged app in a fresh environment,
continue the explicit publication, three Postgres CLI syncs, full-column parity,
least-privilege grants and app deployment in `docs/operations.md`. Never infer
Lakebase readiness from a pipeline pass.

## Reset and teardown

For learner code reset, preserve work with a commit or patch, then create a new
checkout from the learner branch. Do not deploy the stub. To reset the data
exercise without destroying archival history, redeploy the reviewed solution and
run the normal refresh in the same isolated snapshot environment; re-run the
verification. This re-evaluates the MV from corrected baseline products.
Do not full-refresh Bronze or truncate landing records.

To retire an environment, first record its exact bundle resource inventory,
Lakebase project/branches/catalogs, schemas, runtime principal and owner. Keep
schedules paused and stop the explicitly named workshop app. Endpoints suspend
when idle. Permanent teardown needs a separately reviewed deletion list; neither
`bundle destroy` nor project/schema deletion is an automatic reset command.
Delete only the approved workshop resources after retaining needed investigation
records and evidence. Existing baseline resources are never teardown targets.

## Review record

Retain Git SHA, CLI version/profile name, isolated identifiers, validation output
for both targets, job run/update IDs, result reconciliations, and each verification
limit. Review the full diff, not just green tests. PR approval/merge and release
tags remain maintainer actions; this runbook does not authorize either.
