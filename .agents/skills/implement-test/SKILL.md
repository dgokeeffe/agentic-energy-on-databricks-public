---
name: implement-test
description: Implement an approved workshop issue and prove it with deterministic tests.
---

# Implement and test

Work on a branch from the agreed base. Change only approved files. Add or expose
the named deterministic test first, capture the failure when the issue requires
a red/green repair, then make the smallest implementation change. Preserve
fixed-AEST market timestamps, UTC processing timestamps, source-sign flow,
intervention rows, corrections, immutable provenance, and prepared labels. Run
the focused tests, relevant complete suite, safety checks, and `git diff
--check`. Do not weaken checks or treat a build as behaviour proof. Record exact
commands, exit codes, changed files, failures, fixes, and residual risk, then
continue to `agentic-eval`.
