# agentic-energy-on-databricks — agent context

## Workspace

- **Host:** `https://adb-7405607636854416.16.azuredatabricks.net`
- **Catalog / schema / volume:** `edp_entdata_exp_dev_landing` / `agentic_energy` / `agentic_energy_landing`
- **Bundle:** Databricks Asset Bundle (`databricks.yml`, `engine: direct`)

## Authentication in CoDA agent sessions

Interactive `databricks auth login` is not available. Use one of these two approaches:

### Option A — CoDA app SP (no token required from user)

The app SP credentials live in the gunicorn process environment. Mint a short-lived
OAuth token on demand:

```bash
# Read creds from the app process
_PID=$(pgrep -f gunicorn | tail -1)
CLIENT_ID=$(cat /proc/$_PID/environ | tr '\0' '\n' | grep ^DATABRICKS_CLIENT_ID= | cut -d= -f2-)
CLIENT_SECRET=$(cat /proc/$_PID/environ | tr '\0' '\n' | grep ^DATABRICKS_CLIENT_SECRET= | cut -d= -f2-)

SP_TOKEN=$(/app/python/source_code/.venv/bin/python -c "
from databricks.sdk.core import Config
cfg = Config(
    host='https://adb-7405607636854416.16.azuredatabricks.net',
    client_id='$CLIENT_ID', client_secret='$CLIENT_SECRET',
    auth_type='oauth-m2m',
)
print(cfg.authenticate().get('Authorization','')[7:])
")

export DATABRICKS_HOST=https://adb-7405607636854416.16.azuredatabricks.net
export DATABRICKS_TOKEN=$SP_TOKEN
unset DATABRICKS_CONFIG_PROFILE DATABRICKS_CONFIG_FILE

# Use the real CLI (not the broker wrapper):
/app/python/source_code/.local/bin/databricks current-user me
```

The SP is `app-534yfc coda-01` (workspace-access + databricks-sql-access).

### Option B — PAT via environment variable

```bash
export DATABRICKS_HOST=https://adb-7405607636854416.16.azuredatabricks.net
export DATABRICKS_TOKEN=<pat>
unset DATABRICKS_CONFIG_PROFILE DATABRICKS_CONFIG_FILE
databricks current-user me
```

## Bundle deployment

Required variables (supply via `--var` or `BUNDLE_VAR_*` env vars):

| Variable | Value (dev) |
|---|---|
| `catalog` | `edp_entdata_exp_dev_landing` |
| `schema` | `agentic_energy` |
| `landing_volume` | `agentic_energy_landing` |
| `participant_group` | workshop participant group name |
| `facilitator_group` | workshop facilitator group name |
| `runtime_service_principal` | SP name (workshop target only) |

```bash
databricks bundle deploy \
  --var catalog=edp_entdata_exp_dev_landing \
  --var schema=agentic_energy \
  --var landing_volume=agentic_energy_landing \
  --var participant_group=<group> \
  --var facilitator_group=<group>
```

`dev` target is default; namespaces the job under the deploying identity automatically.

## GitHub / git push

`GH_TOKEN` is in the gunicorn process env but not inherited by agents:

```bash
_PID=$(pgrep -f gunicorn | tail -1)
GH_TOKEN=$(cat /proc/$_PID/environ | tr '\0' '\n' | grep ^GH_TOKEN= | cut -d= -f2-)
export GH_TOKEN
git remote set-url origin https://dgokeeffe:${GH_TOKEN}@github.com/dgokeeffe/agentic-energy-on-databricks-public.git
```

## Deployed jobs (as of 2026-08)

| Job ID | Name | Status |
|---|---|---|
| `596015428927199` | `[dev a30022336] Agentic Energy ETL` | PAUSED, healthy |
| `418412736182532` | `[dev app_534yfc_coda_daveok] Agentic Energy ETL` | PAUSED, healthy |

Both run `--mode fixture` against the landing volume. Schedule is every 30 min
(Sydney TZ) but paused pending facilitator approval.
