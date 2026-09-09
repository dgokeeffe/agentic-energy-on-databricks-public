# Track C — app and Lakebase

Track C builds on the NEM regional-operations app and the writable Postgres state
behind it. You get your own isolated Lakebase branch and your own deployed app, so
you can change behaviour and see the result without affecting anyone else.

This track is self-contained. It does not depend on Track A, Track B, or a
partner. Work at your own pace, in stage order.

Copy [`../track-record-template.md`](../track-record-template.md) and keep it
beside you.

## What makes this track different

Tracks A and B stay local or read-only. **Track C deploys.** You deploy one app,
against one Lakebase branch, both named from your own attendee slug. You do not
touch the foundation bundle, anyone else's branch, or shared Unity Catalog
objects.

The design and its verified limits are in
[`../../miniwiki/decisions/attendee-isolation.md`](../../miniwiki/decisions/attendee-isolation.md).
Read it before stage 2.

## Data ownership, which you must not violate

| Object | Writer | Reader |
| `gold_nem_app_region_status` (Delta serving source) | Lakehouse publication job | Synced-table pipeline |
| `app_read.nem_region_status_synced` | Managed sync | Your app, **read-only** |
| `app_write.investigations` | Your app | Lakebase CDF |
| `lb_investigations_history` | Lakebase CDF | Lakeflow, immutable |

Analytics reads lakehouse-owned data. Lakebase owns writable application state.
**Never write to a synced table** — modifications break the sync pipeline.

The serving row repeats market-wide constraint and interconnector summaries for
each region. There is no governed interconnector-to-region mapping. **Never sum
the repeated values across regions.**

## Stages

Use a fresh AI-assistant conversation for each stage. Record what you learned,
what remains uncertain, and whether to continue, revise, or ask for help before
opening the next.

### Stage 1 — run the app locally against mock data

Prove the app works before involving any workspace resource.

```bash
make app-install
make app-test
make app-dev-mock
```

`app-dev-mock` serves on `127.0.0.1` with `VITE_DATA_MODE=mock`. Open it, use the
investigation surface, and note what the app does today.

Record: what the app shows, what it lets an operator do, and which behaviour you
intend to change.

### Stage 2 — get your isolated branch and slug

Ask the facilitator for:

- your **attendee slug** (lowercase letters, numbers, hyphens; starts with a
  letter; 26 characters or fewer), and
- the **Lakebase project ID**.

The facilitator creates your branch with
[`../lakebase/scripts/provision-attendee-branches.sh`](../lakebase/scripts/provision-attendee-branches.sh).
The facilitator also grants the approved participant group temporary `CAN_MANAGE`
on the Lakebase project so attendee agents can create their own compute endpoint.
This is a project-wide permission, not a branch-scoped permission; use it only
for the endpoint bootstrap and do not manage anyone else's resources.

Confirm your branch exists before continuing:

```bash
databricks postgres list-branches projects/<PROJECT_ID> --profile DEFAULT
```

You should see `dev-<your-slug>`. Record the branch path. Do not use a branch
that is not yours.

Create or configure only your own primary endpoint. This helper never creates,
replaces, resets, or deletes branches, and enables five-minute scale-to-zero:

```bash
PROFILE=DEFAULT PROJECT_ID=<PROJECT_ID> ATTENDEE_SLUG=<your-slug> \\
  bash workshop/lakebase/scripts/provision-attendee-endpoint.sh
```

Confirm the endpoint is ready before continuing:

```bash
databricks postgres get-endpoint \\
  projects/<PROJECT_ID>/branches/dev-<your-slug>/endpoints/primary \\
  --profile DEFAULT
```

If the endpoint command fails with a permission error, stop and ask the
facilitator. Do not request or add permissions from the attendee agent.

### Stage 3 — deploy your app, before running it against Lakebase

**Order matters.** Your app's service principal must create `app_write` so that
it owns the schema. If you connect locally first, the schema ends up owned by your
own identity and the app then fails with `permission denied … 42501`.

```bash
cd nemweb_app
databricks bundle validate --strict -t dev --profile DEFAULT \
  --var attendee_slug=<your-slug> \
  --var lakebase_project_id=<project-id> \
  --var sql_warehouse_id=<warehouse-id>
```

Check the resolved app name and branch path in the output. Your app name will be
`aew-<your-slug>` and the branch must be `dev-<your-slug>`. If the branch is not
yours, stop.

> The Lakebase database **resource ID** is hyphenated (`databricks-postgres`),
> while the Postgres **database name** is underscored (`databricks_postgres`).
> The bundle default is already correct. If you override it, confirm the real
> value with
> `databricks postgres list-databases projects/<project-id>/branches/dev-<your-slug> --profile DEFAULT`,
> or the app will point at a resource path that does not exist.

Then, once the facilitator has released deployment:

```bash
databricks bundle deploy -t dev --profile DEFAULT \
  --var attendee_slug=<your-slug> \
  --var lakebase_project_id=<project-id> \
  --var sql_warehouse_id=<warehouse-id>
```

Record the app name, the branch it points at, and the deploy exit code.

`CAN_CONNECT_AND_CREATE` on the app's Postgres resource is separate from the
project-level permission used to create the endpoint. Never grant the app's
service principal project `CAN_MANAGE` just to bootstrap compute.

Confirm your app's service principal owns the schema it created:

```bash
databricks apps get aew-<your-slug> --profile DEFAULT
```

Note the `service_principal_client_id`. That same ID should own `app_write` on
your branch. This was verified working on 2026-09-07: the deployed app created
`app_write` and `appkit`, both owned by its own service principal, and neither
schema appeared on the parent branch.

### Stage 4 — change one behaviour, with a test

Pick one change. Keep it small enough to prove.

Starting points:

| Concern | Files |
| Investigation writes | `nemweb_app/server/db/investigations.ts`, `../lakebase/migrations/001_app_write_investigations.sql` |
| Synced read contract | `../lakebase/contracts/region-status.schema.json`, `../lakebase/tests/test_synced_table_contract.py` |
| CDF current state | `../lakebase/cdf.py`, `../lakebase/tests/test_cdf_reducer.py` |

Write or expose the failing test first, then make the change.

```bash
make lakebase-test
make app-test
```

Record: the failing test before, the passing test after, the diff, and the exit
codes. A passing test you weakened is not a pass.

### Stage 5 — verify on your own branch

Redeploy and exercise the behaviour through the app against your own branch.
Reconcile what you see in the app with what is in Postgres.

Record: what you observed, whether it matched the test, and the evidence label.
Rows in your branch came from a point-in-time copy of the parent — they are
**snapshot** evidence, not live.

### Stage 6 — close

Record what you built, what would need to be true to run it for real, and what
you could not verify.

If you want your change considered for the repository, open a pull request. Do not
merge it yourself.

## Explore safely

The app is a place to try an analyst workflow, not to make an automated market
or trading decision. Use the prepared path to explore the experience before
connecting live resources.

Pause and ask the facilitator if:

- your slug or branch is not confirmed yours;
- you are about to deploy with someone else's slug;
- an app deployment would overwrite an app you did not create;
- a change would write to a synced table;
- a change would sum market-wide values across regions;
- `permission denied … 42501` appears — do **not** drop a schema to fix it, since
  that deletes data; ask first;
- a test needs weakening, skipping, or deleting to pass; or
- you need a credential, token, or private workspace detail in a file.

Keep these hard boundaries: do not deploy the foundation bundle, run its jobs,
change grants, enable live NEMWEB, change a schedule, delete a Lakebase project
or branch, or merge. Do not put credentials or private workspace details in the
app, a prompt, or a record. Prepared and snapshot evidence is welcome for
exploration, but label it clearly and do not describe it as live.
