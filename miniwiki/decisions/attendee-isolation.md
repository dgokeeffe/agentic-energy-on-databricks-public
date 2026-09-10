# Attendee isolation in a single workspace

## Decision

Give each attendee their own **Lakebase branch** and their own **Databricks
App**, both named from one required `attendee_slug` variable. Keep every
Postgres schema name (`app_write`, `app_read`) identical across attendees.

The workshop has one workspace. Isolation therefore comes from branch and app
identity, not from renaming objects inside the database.

## Why branches rather than per-attendee schemas

The app hardcodes `app_write` in `nemweb_app/server/db/schema.ts` and in every
statement in `nemweb_app/server/db/investigations.ts`. Per-attendee schemas
would require parameterising each of those statements and the migration, and
would leave every attendee able to read and write every other attendee's rows in
a shared database.

A branch is a copy-on-write clone. Databricks documents that branch isolation
"extends to Postgres role state and databases as well — roles and databases
created, GRANTs and REVOKEs applied, and role attributes modified on one branch
have no effect on other branches"
([Branches](https://docs.databricks.com/aws/en/oltp/projects/branches)). So each
attendee gets an independent `app_write`, independent grants, and an independent
copy of the seeded data, with no application code change.

Storage cost is only the changed pages, not a full copy per attendee.

## The limit that actually binds

Verified against
[Manage projects](https://docs.databricks.com/aws/en/oltp/projects/manage-projects)
on 2026-09-07:

| Resource | Limit |
|---|---|
| Maximum number of concurrently active computes | 20 |
| Maximum number of branches per project | 500 |
| Maximum number of Postgres databases per branch | 500 |
| Maximum number of projects per workspace | 1000 |
| Maximum number of root branches | 3 |
| Maximum number of protected branches | 1 |
| Minimum scale to zero time | 60 seconds |

**500 branches per project is not the constraint. 20 concurrently active
computes is.** Each branch has its own compute, and every attendee working at
once needs their compute running. The default branch is exempt from the limit.
The attendee endpoint helper explicitly configures each endpoint with a
five-minute scale-to-zero timeout, including endpoints inherited from the
parent branch; a new connection wakes a suspended endpoint.

Over the limit the failure is a connection error, not a queue: "additional
computes beyond the limit remain suspended and you see an error when attempting
to connect to them." The documented remedies are to suspend other computes or
ask Databricks Support to raise the limit.

Practical planning rule:

| Concurrent attendees | Action |
|---|---|
| Up to 19 | One project. No further action. |
| 20 or more | Request a limit increase **before** the workshop, or shard attendees across a second project. |

Ask Support early. Do not discover this at 09:45 on the day.

## Naming constraints that forced an explicit slug

Two independent constraints make automatic naming impossible:

1. **App names** allow "only lowercase alphanumeric characters and hyphens",
   must be unique in the workspace, and are limited to **2–30 characters**
   ([Apps create API](https://docs.databricks.com/api/workspace/apps/create)).
2. **Branch and endpoint IDs** must be 1–63 characters, start with a lowercase
   letter, and contain only lowercase letters, numbers, and hyphens
   (`databricks postgres create-branch -h`).

`${workspace.current_user.short_name}` cannot be used when it contains a dot.
For example, `first.last@example.com` resolves to `first.last`, and the dot is
invalid in both an app name and a branch ID.

The existing prefix `agentic-energy-workshop-` is 24 of the 30 permitted app
characters, leaving 6 for the attendee. That is why the app name prefix is now a
variable defaulting to the short `aew`, giving `aew-<slug>` and leaving 26
characters for the slug.

`attendee_slug` is therefore a required variable with no default. Each attendee
sets it once and every isolated resource derives from it.

## Resulting names

For the synthetic example `attendee_slug=example`:

| Resource | Name |
|---|---|
| Lakebase branch | `projects/<project>/branches/dev-example` |
| Branch compute endpoint | `.../branches/dev-example/endpoints/primary` |
| Databricks App | `aew-example` |
| Postgres schema | `app_write` (identical for everyone, isolated by branch) |

## Required order of operations

The app's service principal must **create** the schema to own it. Deploying
after a local run leaves the schema owned by a human identity and the app then
fails with `permission denied … 42501`.

1. Facilitator creates the attendee branch from the seeded parent branch.
2. Facilitator temporarily grants the approved participant group project-level
   `CAN_MANAGE` so attendee agents can create compute endpoints.
3. Attendee agent creates or configures only its own primary endpoint with
   five-minute scale-to-zero, using the endpoint helper.
4. Attendee deploys their app.
5. The app's service principal creates and owns `app_write` on that branch.
6. Only then does the attendee run anything locally.
7. Facilitator revokes the temporary project permission after endpoint bootstrap.

`CAN_CONNECT_AND_CREATE` on the App's Postgres resource is a separate database
permission. It does not grant endpoint management and should not be replaced
with project `CAN_MANAGE` for the App service principal.

This matches step 9 of [`../../workshop/lakebase/preflight.md`](../../workshop/lakebase/preflight.md).

## Verification boundary

The repository validates the naming rules, bounded inputs, command ordering, and
local contract tests. Workspace-specific provisioning results, resource names,
branch positions, service-principal identifiers, and attendee outcomes are
facilitator-only evidence and must remain outside Git.

Before workshop use, a facilitator records the approved non-sensitive outcome
outside the public repository and confirms that each attendee receives only
their assigned branch and app. The generic deployment gates remain the
authoritative procedure.

## What this does not promise

- It does not isolate Unity Catalog. Bundle `mode: development` prefixes
  bundle-managed resource names, but `catalog`, `schema`, and
  `app_serving_schema` are supplied variables and are **not** automatically
  per-attendee. An attendee publishing a serving table needs their own
  `app_serving_schema` value.
- Endpoint bootstrap is an explicit exception to the usual facilitator-only
  resource policy. Temporary project-wide `CAN_MANAGE` lets attendee agents
  create compute endpoints, but is not branch-scoped and technically permits
  other project management actions. The helper and workshop policy restrict
  attendees to their own endpoint; the facilitator revokes the permission after
  bootstrap. The App service principal does not receive this permission.
- It does not make branch data live. A branch inherits a point-in-time copy;
  rows in an attendee branch are snapshot evidence, never live proof.
- Whether a synced table survives into a child branch as a still-syncing target
  is **unverified**. Treat the inherited copy as static until a facilitator
  preflight confirms otherwise.
- The 20-concurrent-compute limit was **not** load-tested. Only two branch
  computes ran at once. The limit is documented, not measured here.

## Open questions

- Confirm the concurrent-compute headroom for the actual attendee count, and
  whether a Support increase is needed.
- Decide the branch lifetime. Scale-to-zero suspends idle computes, and
  Databricks archives branches without a running compute after inactivity, so a
  workshop-length branch needs no aggressive TTL.
- Decide whether attendees self-serve branch creation or receive a
  facilitator-provisioned branch.
