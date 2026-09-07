# Workshop pair record

Copy this file for the selected GitHub issue. Do not record credentials,
private workspace details, or participant personal data.

| Field | Record |
|---|---|
| GitHub issue number and title | |
| `workshop-ready` confirmed | |
| Business outcome responsibility | |
| Engineering quality responsibility | |
| Operator outcome | |
| Task kind, preparation choice, and verification rationale | |
| Governed source, grain, units, and freshness | |
| Prepared, snapshot, or live status | |
| Fixed contracts | |
| Exact implementation files | |
| Deterministic tests and commands | |
| Plan approver and decision | |
| Branch | |
| Focused and complete test results | |
| Agentic-eval result and artifact | |
| Explanations ruled out with cited evidence, versus paths not investigated | |
| Refinement, defect correction, restart, or block, with a short reason when relevant | |
| Independent reviewer and verdict | |
| Structural-review result, location, consequence, and remaining uncertainty | |
| Proposed lesson or "do not generalise"; original and second-case inputs/results; keep/revise/discard decision | |
| Reproduced findings and repairs | |
| Pull request with `Closes #N` | |
| Remaining uncertainty | |
| Human accept, send back, reject, or stop | |

The required order is issue → measurable requirement → exact plan → human
approval → implementation → deterministic tests → agentic eval → independent
review → pull request → human disposition. An unrun deployment, preview, sync,
CDF, or ML job is `not-run`, never a pass.

## Using the learning fields

Choose preparation and proof for the task, not a permission tier. Cite evidence
for explanations ruled out; do not count an uninvestigated path as disproven.
Record a reason for useful refinement, defect correction, restart, or block when
relevant, or state that none occurred. The structural result concerns the actual
approved change, separately from behavioural review: "no material issue found" or
"not applicable" with a reason is valid.

For the optional [read-only calibration](../../workshop/agent-practice/README.md),
retain the exact original and second-case inputs, prompt versions, baseline and
replay outputs, source citations, and independent check. Label each result
`actual agent output`, `actual human output`, or `facilitator-prepared output`;
mark unrun steps `not-run`. Record the proposed lesson and keep/revise/discard
reason, or "no extra instruction needed" or "do not generalise". Prepared output
is not proof that an agent ran. There is no required improvement metric or new
skill per participant.

The exercise needs selected-issue and plan authority plus facilitator placement
and rehearsal; it does not replace a required check. Keep lesson instructions
here for read-only replay. Shared-skill or test changes outside the original
approved plan require a later approved task, not a post-review repository mutation.
