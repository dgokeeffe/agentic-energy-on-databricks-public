---
name: improve-the-harness
description: Improve one Track B test, evaluation criterion, plan check, or review prompt in response to an observed failure, then rerun the same UTC ticket and decide keep or revert.
---

# Improve the harness

Use this skill for Track B cards 9–10. Start from one failure recorded during
an earlier stage. Do not invent a failure for the exercise.

## Change one thing

Choose exactly one:

- deterministic test;
- agentic evaluation criterion;
- task-plan check; or
- review prompt.

Name the observed failure, expected improvement, measure such as catch rate or
cost per accepted change, and the previous version or revert point. Freeze the
same UTC ticket, test, data, and required criterion before the rerun.

## Compare

Rerun the same ticket through the revised harness. Record before and after tool
calls, edits, failed attempts, test output, eval result, review verdict, and
cost. Decide explicitly to keep or revert the one change.

Do not change the ticket, criterion, or expected result to obtain a pass. Do not
make a second harness change before measuring the first. Preserve the named UTC
test, fixed-AEST market time, independent human review, no-merge rule, and
no-deploy rule.

Record the track result and closing-note inputs: an existing workflow, decision
owner, evidence required, stop, and date within a fortnight.
