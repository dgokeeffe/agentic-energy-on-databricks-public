---
name: live-landing
description: Prepare and operate the facilitator-only live NEMWEB landing after separate data-use, network, deployment, and schedule approvals.
---

# Live landing

Use this skill only after snapshot and publication gates pass.

## Read first

- [`../../Instructions.md`](../../Instructions.md)
- [`../../../PRE-REQUISITES.md`](../../../PRE-REQUISITES.md)
- [NEMWEB runbook section 5](../../deployment-gates.md#5-three-cycle-live-proof)
- [`../03-evidence-gates/SKILL.md`](../03-evidence-gates/SKILL.md)

> **Facilitators only:** Live implementation and operational scripts reside in
> `nemweb_foundation/`. Participants have no live-mode or schedule role and
> must not be directed there.

## Approval gate

Require current, recorded approval for AEMO terms, external network use, the
selected workspace target, live deployment, and the temporary schedule change.
A prior snapshot run or a prompt does not supply that approval.

Live mode requires both deployment-controlled values:

- `nemweb_mode=live`;
- `allow_live_nemweb=true`.

Participants cannot override the lander parameters. Every workspace-aware
command uses `--profile DEFAULT`.

## Safe sequence

1. Confirm the accepted snapshot, SQL, metric, Genie, and dashboard gates.
2. Validate the live configuration strictly, review the target summary, and
   confirm the live and snapshot sibling roots remain separate.
3. With explicit authorisation, deploy only the isolated `live_evidence` target.
   Keep both schedules paused.
4. Run the context Job once, then run three critical cycles manually at
   approximately five-minute start intervals. Do not manufacture a source row
   when AEMO publishes nothing new.
5. Capture each exact update and both app-serving outcomes with the evidence skill.
6. Confirm both schedules remain paused after the third cycle.
7. Record the final paused state and target-scoped live settings.

On failure, pause first, preserve raw archives and manifests, and follow the
runbook rollback. Do not destroy the bundle, delete a schema or Volume, or use a
full refresh as routine recovery.
