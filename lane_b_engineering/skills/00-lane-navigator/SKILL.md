---
name: lane-b-navigator
description: Route a Track B attendee to one production-fix stage while preserving the UTC processing-time test, fixed-AEST market time, and human decisions.
---

# Track B navigator

Use this skill to select the next Track B stage. Read
[`../../Instructions.md`](../../Instructions.md) and the current
[track record](../../../workshop/track-record-template.md).

The track is self-paced. There is no fixed clock; complete stages in order and
record the decision for each before opening the next.

| If you need to… | Use |
|---|---|
| read incident evidence and obtain plan approval | [`../01-read-evidence-and-plan/SKILL.md`](../01-read-evidence-and-plan/SKILL.md) |
| prove clean, seeded-red, and repaired-green states | [`../02-seeded-defect-red-green/SKILL.md`](../02-seeded-defect-red-green/SKILL.md) |
| score the agentic eval and obtain independent review | [`../03-agentic-eval-and-adversarial-review/SKILL.md`](../03-agentic-eval-and-adversarial-review/SKILL.md) |
| improve one harness check and rerun the same ticket | [`../04-improve-the-harness/SKILL.md`](../04-improve-the-harness/SKILL.md) |

Use the matching numbered prompt in a fresh conversation. Do not skip the human
decision or carry chat history forward as evidence.

Track B is self-contained and does not depend on another track. It reads from the
shared governed foundation; do not create a second data store.

Stop on an unapproved file, missing source contract, weakened test, absent
reviewer, credential request, merge, deployment, or live job debugging.
