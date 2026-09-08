---
name: agentic-eval
description: Evaluate the implementation trajectory separately from deterministic tests.
---

# Agentic eval

Use the issue's approved rubric to score requirement interpretation, tool and
API choice, inspected evidence, failed attempts, recovery, safety limits, and
whether the operator outcome was met. Cite files and command output. A green
unit test is not an eval result, and an implementation recap is not evidence.

Use the [track record](../../../workshop/track-record-template.md), or the
existing maintenance task record, to explain whether the chosen preparation and
proof fit the task. For investigations, separate explanations ruled out with
cited evidence from paths not investigated. An unsupported inference is not proof
that its opposite is true; state the remaining uncertainty and evidence needed.

Distinguish useful refinement (improving an approach within the approved plan),
defect correction (repairing a violated requirement), restart (abandoning an
approach), and block (unable or unauthorised to proceed). Record a short reason
when relevant, or that none occurred. Useful refinement is not automatically a
failure. Do not impose a turn count or an improvement metric per participant.

If the approved plan includes the optional
[read-only calibration](../../../workshop/agent-practice/README.md), retain the
original and variant inputs, baseline and replay results, proposed lesson, and
keep/revise/discard decision. Label actual agent output separately from
facilitator-prepared output, and unrun steps as `not-run`. A correct baseline may
need "no extra instruction needed"; "do not generalise" is also a legitimate
outcome. No participant must create a new skill. Keep lesson changes in the pair
record for read-only replay. Shared-skill or test changes outside the original
approved plan require a later approved task; do not start a post-review repository
mutation. The exercise never replaces required eval or review.

Any required criterion scored as failed returns the change to
`implement-test`. Preserve the complete eval record for `adversarial-review`.
