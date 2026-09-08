---
name: adversarial-review
description: Obtain independent plan, semantic, security, and regression review before a pull request.
---

# Adversarial review

A reviewer other than the author receives the issue, approved plan, diff,
deterministic test output, eval, failed attempts, and residual risks. Check plan
compliance, NEM semantics, AppKit API use, Lakebase identity and SQL
parameterisation, ML leakage, participant safety, and unsupported claims as
applicable. This applies to authorised repository maintenance too; task kind
never grants permissions or reduces the existing reviewer floor in
[agentic-verification](../agentic-verification/SKILL.md).

Return two explicit answers:

- **Behavioural review:** Does the change meet the intended behaviour? Check
  acceptance evidence, regression and failure cases, source claims, and what the
  tests do not establish. Distinguish explanations ruled out from paths not
  investigated.
- **Structural review:** Does the actual approved change fit the existing design?
  Examine responsibilities, dependencies, duplication, and interfaces separately
  from passing tests. Name each material issue's location and consequence, not
  just a style preference. Record the result and remaining uncertainty in the
  [track record](../../../workshop/track-record-template.md) or maintenance
  task record. "No material issue found" or "not applicable" with a reason is
  valid; do not manufacture a defect or seed an extra exercise.

For an approved calibration, independently compare the retained outputs against
the source contract and the facilitator/reviewer expected findings. Check original
and variant replay, actual versus prepared labels, and keep/revise/discard reasoning.
Do not treat a static fixture test as proof of agent behaviour or general learning.
Keep lesson instructions in the pair record, not a post-review repository change.

Use fresh, read-only review context. If native agents are unavailable, use a
constrained fresh session or a human reviewer; if tool restrictions cannot be
verified, use a human review of supplied artefacts. A prompt alone does not enforce
read-only access. Fallbacks preserve independence, human approval, and the existing
reviewer floor; unavailable reviewers leave the gate incomplete.

Return `REQUEST_CHANGES` with a reproducible file, command, or criterion finding,
or `PASS` with the same level of detail. Reproduce findings, repair through
`implement-test`, and rerun the affected gates. Only a final `PASS` proceeds to
`prepare-pull-request`. Accepted repairs return through the gates; a final review
is not permission for further repository mutations.
