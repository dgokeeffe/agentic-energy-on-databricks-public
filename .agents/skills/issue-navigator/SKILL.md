---
name: issue-navigator
description: Select and route one workshop-ready GitHub issue through the shared pair lifecycle. Optional; a track is completed from its own Instructions.md.
---

# Issue navigator

**This route is optional.** Each track in [`QUICKSTART.md`](../../../QUICKSTART.md) is
self-contained and is completed from its own `Instructions.md`. An issue is only
needed when the work is contributed back, or when a facilitator has assigned one.
Do not send a participant here first.

1. List open issues carrying `workshop-ready` in **this** repository:

   ```bash
   gh issue list --label workshop-ready --state open
   ```

   Do not invent local tickets. If the command returns nothing, stop and tell the
   facilitator — an empty list means the exercises have not been raised here, not
   that the participant should improvise one.

2. The pair selects one issue and records its number and operator outcome.
3. Inspect the issue, `nemweb_foundation/`, and the named starter (`nemweb_app/`,
   `nemweb_ml/`, or `workshop/lakebase/`).
4. Continue in order through `understand-requirement`, `plan-change`, human
   approval, `implement-test`, `agentic-eval`, `adversarial-review`, and
   `prepare-pull-request`.
5. A person accepts, sends back, rejects, or stops. Agents never merge or deploy.

Keep one business responsibility and one engineering responsibility in the
pair. Participants may inspect `nemweb_foundation/`, but must not deploy,
provision, change grants, run jobs, enable live data, or change schedules.

## Issue numbers are not portable

These exercises were migrated from the private `agentic-energy-on-databricks`
repository, which shares no Git history with this one. **Every number changed.**
A number quoted in prose, a commit message, or a miniwiki page may refer to the
private repository and will resolve to the wrong issue or to nothing here.

Resolve an exercise by title and label, never by a number you read somewhere.
When you cite an issue, say which repository it belongs to.
