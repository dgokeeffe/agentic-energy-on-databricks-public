# Track B — production fix

Track B repairs one deliberately seeded UTC processing-time defect and proves
that both deterministic checks and an agentic evaluation can reject weak work.

This track is self-contained. It does not depend on Track A, Track C, or a
partner. Work at your own pace, in stage order. You may pair with someone on the
same track if you prefer; nothing requires it.

Copy [`../workshop/track-record-template.md`](../workshop/track-record-template.md)
and keep it beside you.

The repository starts green. The exercise patch changes a processing timestamp
to an AEST-naive wall clock. Your repair must restore UTC processing instants
without converting the market `interval_end`, which remains interval-ending
fixed AEST (UTC+10, no daylight saving).

## Required outputs

- an approved task plan naming files, fixed contracts, tests, evaluation
  criteria, and stop conditions;
- clean, red-after-patch, and repaired-green results from the same named test;
- the implementation diff and evidence that the test was not weakened;
- focused regression output and exact command exit codes;
- an agentic evaluation of tool choice, trajectory, operating envelope, and
  rubric quality;
- a verdict from a reviewer other than the author — another attendee, the
  facilitator, or an independent fresh assistant session; and
- one measured harness improvement with a same-ticket before/after result and
  an explicit keep-or-revert decision.

Tests verify deterministic behaviour: a known implementation contract produces
the expected UTC processing timestamps. Evals inspect the agent's tool choice,
trajectory, operating envelope, and work quality against the rubric. A passing
test cannot compensate for a failed eval or an unapproved file change.

Record results in your track record. An agent summary is a claim, not
proof; attach the command, exit code, test output, diff, and human decision.

## Authoritative exercise assets

| Asset | Location |
|---|---|
| Task-plan template | [`skills/01-read-evidence-and-plan/assets/task-plan.md`](skills/01-read-evidence-and-plan/assets/task-plan.md) |
| Seeded-defect patch | `skills/02-seeded-defect-red-green/assets/track-b-defect.patch` |
| UTC contract-test entry point | `skills/02-seeded-defect-red-green/assets/processing_timestamps_utc_contract.py` |

Run all commands from the repository root:

```bash
uv run --extra test python -m pytest lane_b_engineering/skills/02-seeded-defect-red-green/assets/processing_timestamps_utc_contract.py -q
git apply lane_b_engineering/skills/02-seeded-defect-red-green/assets/track-b-defect.patch
uv run --extra test python -m pytest lane_b_engineering/skills/02-seeded-defect-red-green/assets/processing_timestamps_utc_contract.py -q
# This second test invocation must fail. Implement the approved repair, then
# rerun the same test until it passes.
```

To restore the clean teaching state instead of completing the repair:

```bash
git apply -R lane_b_engineering/skills/02-seeded-defect-red-green/assets/track-b-defect.patch
uv run --extra test python -m pytest lane_b_engineering/skills/02-seeded-defect-red-green/assets/processing_timestamps_utc_contract.py -q
```

Do not apply or reverse the patch when unrelated edits affect its target file.
The facilitator validation compares the target file's SHA-256 before the patch
and after reversal to prove byte-identical restoration.

## Numbered stages

Use a fresh AI-assistant conversation for every numbered prompt. Finish the
current stage and record its human decision before starting the next.

| Stage | Prompt | Output |
|---|---|---|
| 1. Read evidence and approve plan | [`01-read-evidence-and-plan.md`](prompts/01-read-evidence-and-plan.md) | defect statement, cited contracts, approved plan |
| 2. Seed, reproduce, and repair | [`02-seeded-defect-red-green.md`](prompts/02-seeded-defect-red-green.md) | clean/red/green results, diff, regression, decision |
| 3. Evaluate and review | [`03-agentic-eval-and-review.md`](prompts/03-agentic-eval-and-review.md) | eval evidence and independent verdict |
| 4. Improve one harness check | [`04-improve-the-harness.md`](prompts/04-improve-the-harness.md) | one change, same-ticket rerun, keep or revert |

## Stops

Stop and return to the approver if:

- the source contract or named test cannot be found;
- the plan permits another implementation file, schema, dataset, repository,
  credential, merge, or deployment;
- the patch target already has unrelated edits;
- the clean test is not green or the patched test is not red;
- market time is changed from fixed AEST;
- a check is deleted, skipped, relabelled optional, or weakened;
- the agent changes an unapproved file or hides failed attempts;
- the author reviews their own work;
- live deployment debugging begins; or
- the harness change uses a different ticket or criterion.

Do not merge, deploy, run a Databricks job, change a schedule, expose secrets,
or approve your own work.
