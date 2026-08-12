# AGENTS.md — agent context for agentic-energy-on-databricks

Canonical guidance for AI coding agents in this repo. `CLAUDE.md` and `GEMINI.md`
are thin pointers here so they can never drift.

## Before you try to deploy

If you are running inside a **CoDA container** (a Databricks App terminal or an
Omnigent runner — the usual case for agents in this workshop), Databricks auth is
**already configured**. Do not run `databricks auth login`, do not hunt for a PAT,
and do not conclude that deployments are impossible when a CLI call fails on
credentials.

```bash
databricks current-user me        # this works with no setup step
./scripts/deploy.sh dev          # after exporting the BUNDLE_VAR_* values
```

Read this before deploying:
**[`.claude/skills/deploying-from-coda/SKILL.md`](.claude/skills/deploying-from-coda/SKILL.md)**

It covers the auth model, which identity you deploy as (the app's own service
principal unless a PAT was injected), the Unity Catalog grants that identity
needs, and an error → cause → fix table for the auth failures that *look* like
missing credentials.

Do **not** scrape credentials out of the app process (`/proc/<pid>/environ`) to
work around an auth error. CoDA strips the app SP secret and `GH_TOKEN` from
terminals deliberately; the brokered token path is the supported route and a
fresh bearer is minted per CLI invocation. `git push` likewise works through
CoDA's configured credential helper without extracting a token.

## Workspace / bundle facts

| Thing | Value |
|---|---|
| Bundle | Databricks Asset Bundle, `databricks.yml`, `engine: direct` |
| Default target | `dev` (`mode: development`, namespaced per deploying identity) |
| Catalog / schema / volume (dev) | `edp_entdata_exp_dev_landing` / `agentic_energy` / `agentic_energy_landing` |

Bundle variables are never committed. Supply them as `BUNDLE_VAR_<name>` env vars
(the `DATABRICKS_` prefix is **not** recognised) or `--var`:

| Variable | dev value |
|---|---|
| `catalog` | `edp_entdata_exp_dev_landing` |
| `schema` | `agentic_energy` |
| `landing_volume` | `agentic_energy_landing` |
| `participant_group` | workshop participant group |
| `facilitator_group` | workshop facilitator group |
| `runtime_service_principal` | ETL SP — **`workshop` target only** |

`DATABRICKS_HOST` is optional: `scripts/deploy.sh` resolves it from the
authenticated CLI when it is not exported (CoDA does not export it).

Deployed dev jobs are per-identity and disposable — the durable evidence of a run
is the immutable manifest under the landing Volume, not the job. Expect one
`[dev <identity>] [dev] Agentic Energy ETL` job per deployer.

## Everything else

- Deployment model, per-developer `dev` target rules, and the UC grant traps
  (service principals are not in `account users`; UC cannot grant to
  workspace-local groups): [`docs/deployment.md`](docs/deployment.md)
- Local fixture workflow (no workspace, credentials, or network) and the Beads
  task graph: [`README.md`](README.md)
- Keep changes focused, and run the suite before deploying:
  `uv run --extra test python -m pytest`
