# Test evidence — Databricks `dev` deployment and serverless run

| | |
|---|---|
| Captured (UTC) | 2026-08-12T05:11Z |
| Repository commit | `54e72c8` (branch `Team-SGS`) |
| Bundle target | `dev` (`mode: development`, `engine: direct`) |
| Workspace | `adb-7405607636854416.16.azuredatabricks.net` |
| Deploying identity | `app-534yfc coda-10` (app service principal, `c55e123f-1a72-4bf8-97d4-e439fffd5654`) |
| Job | `[dev app_534yfc_coda_10] [dev] Agentic Energy ETL` — id `96658206377065` |
| Run | `804474132962441` — **TERMINATED SUCCESS** |
| Result | `bronze=11, silver=6, quarantine=3, gold=3` — identical to local |
| Overall | **PASS**, with caveats under [Limitations](#limitations) |

## Test suite state

No failing tests. The suite was green before, during, and after this deployment:

```text
........................................                                 [100%]
40 passed in 0.19s
```

Any "14 failed" seen in session history was a **deliberate mutation test** from
[`2026-08-12-metadata-contract-validation.md`](2026-08-12-metadata-contract-validation.md):
the new validation block was temporarily deleted to prove the new tests were
load-bearing, then restored. Failure there was the intended outcome.
See [Failures and non-failures](#failures-and-non-failures).

## Bundle variables used

Not committed, per repo policy. Supplied as `BUNDLE_VAR_*`:

| Variable | Value | Provenance |
|---|---|---|
| `catalog` | `edp_entdata_exp_dev_landing` | documented dev value, confirmed present |
| `schema` | `agentic_energy` | documented dev value, confirmed present |
| `landing_volume` | `agentic_energy_landing` | documented dev value, confirmed present |
| `participant_group` | `App-DG-ENTDATA-Engineer` | **substituted** — see [Limitations](#limitations) |
| `facilitator_group` | `App-DG-ENTDATA-DevOps` | **substituted** — see [Limitations](#limitations) |

`DATABRICKS_HOST` was not exported; `scripts/deploy.sh` resolved it from the
authenticated CLI as designed:

```text
==> Resolved DATABRICKS_HOST from the authenticated CLI: https://adb-7405607636854416.16.azuredatabricks.net
```

## Preflight

```text
databricks catalogs list      -> edp_entdata_exp_dev_landing present
databricks schemas list       -> agentic_energy present
databricks volumes list       -> ['agentic_energy_landing']
databricks bundle validate --strict -t dev  -> Validation OK!
```

## Deployment

```bash
./scripts/deploy.sh dev
```

```text
Validation OK!
Building default...
Uploading dist/agentic_energy_on_databricks-0.1.0-py3-none-any.whl...
Uploading bundle files to /Workspace/Users/c55e123f-…/.bundle/agentic-energy/dev/files...
Deploying resources...
Updating deployment state...
Deployment complete!
```

## Serverless run

```bash
databricks bundle run agentic_energy_etl -t dev
```

```text
Run URL: https://adb-7405607636854416.16.azuredatabricks.net/jobs/96658206377065/runs/804474132962441
2026-08-12 05:10:49  RUNNING
2026-08-12 05:11:21  TERMINATED SUCCESS
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3
```

Artifacts landed in the Volume under the immutable per-run path:

```text
/Volumes/edp_entdata_exp_dev_landing/agentic_energy/agentic_energy_landing/dev/runs/804474132962441/
  bronze/  gold/  manifest.json  quarantine/  silver/
```

Manifest from the deployed run:

```json
{
  "layers": {"bronze": 11, "gold": 3, "quarantine": 3, "silver": 6},
  "metadata_sha256": "e2235552b0131cfc2272a6a1da5075a8bea2d5a66c13d57496b8f770562ca94e",
  "mode": "fixture",
  "pipeline_ingested_at": "2024-04-07T00:00:00Z",
  "run_id": "804474132962441",
  "source_definitions": {"read": 2, "selected": 2},
  "sources": {
    "aemo_dispatch_fixture": {"accepted": 4, "bronze": 6, "deduplicated": 1, "quarantine": 2, "silver": 3},
    "weather_fixture":       {"accepted": 4, "bronze": 5, "deduplicated": 1, "quarantine": 1, "silver": 3}
  }
}
```

`metadata_sha256` matches the local run exactly, proving both paths executed the
same contract.

## Local vs serverless — byte-level equivalence

Every data layer was downloaded from the Volume and compared against a fresh
local run:

```text
bronze/aemo_dispatch_fixture.jsonl         MATCH  74b81048350cda0b…
bronze/weather_fixture.jsonl               MATCH  d45bab3f6e3e0df9…
silver/aemo_dispatch_fixture.jsonl         MATCH  f757635ce33ffcce…
silver/weather_fixture.jsonl               MATCH  28c2855232646104…
quarantine/rejected.jsonl                  MATCH  42abde41b303b6fa…
gold/market_weather.jsonl                  MATCH  f56fe6473b47cf8f…
```

`manifest.json` is deliberately excluded from the hash comparison: it embeds
`run_id`, which is orchestration-assigned and differs by construction. All other
manifest fields match.

> **Superseded for two artifacts.** Left unedited as the verbatim record of this
> run. The `agentic-energy-yx8` / `agentic-energy-aln` fixes added keys to the
> quarantine and Gold layers, so `quarantine/rejected.jsonl` and
> `gold/market_weather.jsonl` now hash differently. The local-vs-serverless
> equality demonstrated here still holds — both sides changed together. This
> deployed run predates the fixes and has **not** been re-run against them.
> Current baseline: `docs/test-evidence/2026-08-12-bugfix-quarantine-and-gold.md`.

This is the strongest available evidence for the "same generic contract on both
paths" invariant — not merely equal row counts, but identical bytes.

## Deployed job configuration

```text
name        : [dev app_534yfc_coda_10] [dev] Agentic Energy ETL
schedule    : PAUSED  0 0/30 * * * ?
max_conc    : 1
mode param  : fixture
run_as      : {}   (deploying identity, not a pinned SP)
```

Confirmed as intended: the **schedule remains PAUSED**, so nothing fires
unattended before facilitator approval; `--mode fixture` is pinned, so no live
NEMWEB fetch occurs; `run_as` is unpinned, so the job is deployable per
developer.

## Failures and non-failures

| Observation | Status | Explanation |
|---|---|---|
| `14 failed, 26 passed` | **not a failure** | Mutation test with validation code deliberately removed; restored immediately, `40 passed` |
| `KeyError: 'source_timezone'` etc. | **fixed** | The defect `agentic-energy-zwh` addressed; now `MISSING_SOURCE_FIELD:<field>` |
| `INVALID_METADATA_SNAPSHOT_ID` during probing | **operator error** | `--metadata-snapshot-id` omitted on an external contract |
| `FileNotFoundError` on fixtures during probing | **operator error** | Fixtures live under `agentic_energy/resources/fixtures/`, not `fixtures/` |
| First probe reporting "ACCEPTED SILENTLY" ×5 | **invalid measurement** | `--metadata-root` is ignored unless `--metadata` is also passed, so the packaged contract was read instead of the mutated one. Corrected run is in the contract-validation record. |
| `Warning: failed to commit beads files: exit status 128` | **benign** | Beads attempting a git commit of its own state |

Nothing in the repository is currently failing, and nothing was committed in a
failing state.

## Limitations

Read before treating this as a green deployment gate.

- **The participant and facilitator groups are substitutes, not the real ones.**
  No workshop groups exist in this workspace (`admins`,
  `DATA-DG-PLATFORM-ENGINEER`, `App-DG-ENTDATA-*`, `users`, one clone). I used
  `App-DG-ENTDATA-Engineer` / `App-DG-ENTDATA-DevOps` so the bundle could
  validate. **The deployed job's ACLs therefore grant the wrong audiences** and
  must be redeployed with facilitator-supplied group names before any workshop
  use.
- **This is a per-developer `dev` deployment.** `mode: development` namespaces the
  job to the deploying identity, so it is disposable and invisible to others. It
  is not the shared `workshop` target, which additionally pins
  `runtime_service_principal`.
- **Fixture mode only.** `--mode fixture` is hard-coded in the task, so this
  proves nothing about live NEMWEB acquisition, its network bounds, or its
  licensing gate. Per `../workshop-acceptance.md`, the live path needs a reviewed
  bundle change and a human deployment gate.
- **The schedule is PAUSED and must stay that way** until source terms,
  identity, storage, and workspace preflight are approved. Deploying did not
  unpause it, but any redeploy from a modified resource file could.
- **Deployment is not a scored acceptance pass.** It demonstrates the serverless
  path runs the same contract; the Databricks extension in
  `../workshop-acceptance.md` also expects a Lakebase metadata snapshot to drive
  the dispatcher, which this run does not use — it reads the repository contract
  from the Volume.
- **Volume run directories accumulate.** Five run directories already exist under
  `dev/runs/`. They are immutable evidence by design, but they are not garbage
  collected.

## Reproducing

```bash
export BUNDLE_VAR_catalog=edp_entdata_exp_dev_landing
export BUNDLE_VAR_schema=agentic_energy
export BUNDLE_VAR_landing_volume=agentic_energy_landing
export BUNDLE_VAR_participant_group=<facilitator-supplied>
export BUNDLE_VAR_facilitator_group=<facilitator-supplied>

./scripts/deploy.sh dev
databricks bundle run agentic_energy_etl -t dev
databricks bundle summary -t dev          # job id and URL
```
