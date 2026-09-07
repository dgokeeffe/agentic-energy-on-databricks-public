---
name: seeded-defect-red-green
description: Apply the labelled UTC processing-time defect, prove the named test turns red, repair only the approved implementation, and prove the unchanged test turns green.
---

# Seeded defect: red to green

Use this skill for Track B cards 4–5. Work from the repository root and use the
commands in [`../../Instructions.md`](../../Instructions.md).

## Before mutation

1. Confirm the task plan is approved by a person other than its author.
2. Record the patch and test SHA-256 values.
3. Confirm the patch target has no unrelated edits.
4. Run the named test and record a clean green result.

## Exercise sequence

1. Apply [`assets/track-b-defect.patch`](assets/track-b-defect.patch).
2. Run `assets/processing_timestamps_utc_contract.py` through the exact repository
   command in the instructions. Record the expected non-zero exit and UTC
   assertion failure.
3. Give the approved agent the plan, red output, and only the allowed files.
4. Repair processing time without changing fixed-AEST `interval_end`.
5. Rerun the same test and the approved focused regressions.
6. Record changed files, diff, exact commands and exit codes, failed attempts,
   test-file hash, residual risks, and human decision.

The clean repository, not the seeded state, is the starting product. Never call
an unpatched file defective.

For facilitator verification or exercise reset, reverse the patch before any
participant repair, rerun the test, and compare the target-file SHA-256 with the
pre-patch value. Reversal must restore identical bytes.

Stop if the clean test fails, the patched test passes, the target already has
unrelated edits, another file is needed, the test changes, market time changes,
or deployment debugging begins.
