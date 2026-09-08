---
name: snapshot-mode
description: Validate and reconcile the deterministic NEMWEB snapshot without mixing landing roots or presenting prepared rows as live evidence.
---

# Snapshot mode

Use this skill for local snapshot validation or an explicitly authorised
facilitator snapshot run.

## Read first

- [`../../Instructions.md`](../../Instructions.md)
- [`../../../PRE-REQUISITES.md`](../../../PRE-REQUISITES.md)
- [NEMWEB runbook sections 1–4](../../deployment-gates.md#1-local-and-identity-gates)

> **Facilitators only:** The runbook's `nemweb_foundation/` commands operate the
> reviewed implementation. Do not send participants to that directory.

## Required state

Confirm all of the following before a workspace run:

- `nemweb_mode=snapshot` and `allow_live_nemweb=false`;
- the landing path is the Volume root, not its `snapshot/` or `live/` child;
- both periodic jobs are paused;
- the selected catalog, schema, Volume, warehouse, identity, and permissions
  match the approved development target; and
- every workspace-aware command selects `--profile daveok`.

Snapshot and live data occupy separate sibling roots with permanent mode
markers. Do not delete, migrate, or combine an older parent-root layout.

## Procedure

1. Run local miniwiki, test, build, snapshot, API, and whitespace checks from
   the exact working directories in the runbook.
2. Validate the bundle strictly and review the resource summary. This is
   validation, not permission to deploy or run.
3. After explicit deployment and run authorisation, run only the named critical
   DAG. Never request a full refresh.
4. Record the orchestration run ID, child lander result, pipeline ID, and exact
   update ID. Poll that update to a terminal state; never assume the latest
   update is the right one.
5. Reconcile landed files, Bronze, Silver, quarantine, and Gold. Check
   correction order, natural keys, effective-run uniqueness, expectations, and
   watermarks.
6. Record `live_evidence: false` with every snapshot result.

Stop if the target differs, the exact update is ambiguous, a quality metric is
missing, a duplicate key appears, or snapshot data is about to support a live
claim.
