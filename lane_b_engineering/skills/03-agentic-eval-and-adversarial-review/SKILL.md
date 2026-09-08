---
name: agentic-eval-and-adversarial-review
description: Keep deterministic tests separate from the agentic evaluation, score the recorded run, and obtain a facilitated evidence-based verdict from a reviewer other than the author.
---

# Agentic eval and adversarial review

Use this skill for Track B cards 6–8.

## Two verification types

- **Tests** verify deterministic behaviour: known source and implementation
  contracts produce UTC processing timestamps while preserving fixed-AEST
  market time.
- **Evals** inspect non-deterministic behaviour: tool choice, trajectory,
  operating envelope, and rubric quality.

The developer's output includes the specification, context, agent run, tests,
review evidence, and feedback, not code alone.

## Evaluation

Score every required criterion `pass` or `request changes` and cite the command,
file, diff, or run-record line that supports it. A green test does not override
a failed eval, an unapproved edit, hidden failure, or missing residual risk.

## Facilitated review

A reviewer other than the author reads the approved plan, complete diff, red and
green test output, focused regressions, eval table, failed attempts, and
residual risks. The reviewer returns:

- `REQUEST_CHANGES`, naming the missing required criterion and evidence; or
- `PASS`, confirming every required plan item is evidenced.

This is a human review, not an automated service. The reviewer may be another
attendee, the facilitator, or an independent fresh assistant session — but never
the author. Record one genuine rejection before repair; do not fix the evidence
silently before review.

A verdict does not merge or deploy the change. Stop if the author is also the
reviewer, a required criterion becomes optional, evidence is absent, or the
review asks to weaken the UTC check.
