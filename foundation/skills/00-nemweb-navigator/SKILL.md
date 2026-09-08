---
name: nemweb-navigator
description: Route facilitator preparation of the shared NEMWEB foundation to one safe stage while preserving fixed market-time, correction, intervention, source-cadence, and cross-track-pair contracts.
---

# NEMWEB navigator

Use this skill when a facilitator asks what to do next with the shared NEMWEB
foundation.

## Read first

1. [`../../Instructions.md`](../../Instructions.md)
2. [`../../../PRE-REQUISITES.md`](../../../PRE-REQUISITES.md)
3. [`../../deployment-gates.md`](../../deployment-gates.md)
4. [`../../../nemweb_foundation/README.md`](../../../nemweb_foundation/README.md)

> **Facilitators only:** The runbook links to the completed implementation in
> `nemweb_foundation/`. Participants remain in `QUICKSTART.md` and the
> participant playbook.

## Route one stage

| Current need | Next skill or prompt |
|---|---|
| Target identity, validation, or deployment with schedules paused | [`../../prompts/01-deploy-foundation.md`](../../prompts/01-deploy-foundation.md) |
| Deterministic fixture or snapshot reconciliation | [`../01-snapshot-mode/SKILL.md`](../01-snapshot-mode/SKILL.md) |
| Separately approved live-source preparation | [`../02-live-landing/SKILL.md`](../02-live-landing/SKILL.md) |
| Exact update, watermark, quality, or three-cycle proof | [`../03-evidence-gates/SKILL.md`](../03-evidence-gates/SKILL.md) |
| Participant activity | [`../../../QUICKSTART.md`](../../../QUICKSTART.md) |

Open only the prompt for the current stage, and use a fresh conversation. A
completed stage does not authorise the next one.

## Preserve these contracts

- Tracks are self-contained; do not reintroduce cross-track pairing.
- Use one shared Bronze/Silver/Gold foundation; do not create another data
  store.
- Treat interval-ending market time as fixed AEST and processing timestamps as
  UTC instants.
- Retain source versions in Bronze and select valid corrections in Silver.
- Use `is_effective_run` for ordinary Gold analysis; do not aggregate both
  intervention rows.
- Call Current SCADA output `actual_generation_mw`; reserve target and
  availability for the daily T+1 product.
- Treat snapshot or prepared material as non-live.
- Select `--profile daveok` for every workspace-aware command.

Stop on an unexpected identity, target, permission, source contract, or missing
approval. Use the published prepared substitute rather than improvising.
