---
name: lane-b-navigator
description: Route the Track B owner to one production-fix stage while preserving the cross-track pair, workshop clock, UTC processing-time test, fixed-AEST market time, and human decisions.
---

# Track B navigator

Use this skill to select the next Track B stage. Read
[`../../Instructions.md`](../../Instructions.md), the current
[pair record](../../../docs/participant/workshop-pair-record.md), and the
[run of show](../../../docs/facilitator/workshop-run-of-show.md).

| If the pair needs to… | Use |
|---|---|
| read incident evidence and obtain plan approval | [`../01-read-evidence-and-plan/SKILL.md`](../01-read-evidence-and-plan/SKILL.md) |
| prove clean, seeded-red, and repaired-green states | [`../02-seeded-defect-red-green/SKILL.md`](../02-seeded-defect-red-green/SKILL.md) |
| score the agentic eval and obtain independent review | [`../03-agentic-eval-and-adversarial-review/SKILL.md`](../03-agentic-eval-and-adversarial-review/SKILL.md) |
| improve one harness check and rerun the same ticket | [`../04-improve-the-harness/SKILL.md`](../04-improve-the-harness/SKILL.md) |

Use the matching numbered prompt in a fresh conversation. Do not skip the human
decision or carry chat history forward as evidence.

Keep one Track A owner and one Track B owner. Track B consumes Track A's
approved brief and evidence threshold; Track A consumes Track B's timezone and
freshness proof. Both tracks use the same shared foundation.

Stop on an unapproved file, missing source contract, weakened test, absent
reviewer, credential request, merge, deployment, or live job debugging.
