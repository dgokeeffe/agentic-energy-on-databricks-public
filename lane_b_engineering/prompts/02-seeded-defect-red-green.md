# Prompt 02 — prove red, repair, and prove green

Copy this prompt into a **fresh conversation**. Complete only the Track B part
of cards 4–5.

```text
This is a fresh conversation. I am the Track B owner in a cross-track pair. Read lane_b_engineering/Instructions.md, lane_b_engineering/skills/02-seeded-defect-red-green/SKILL.md, the approved task plan, docs/participant/workshop-playbook.md cards 4–5, and our current pair record. Work from the repository root. First run the named UTC contract test and record the clean green result. Confirm the patch target has no unrelated edits, apply the authoritative exercise patch, rerun the same test, and require a genuine red result. Dispatch the approved repair only after red is recorded. The repair must remove the AEST-naive processing-time conversion while leaving market interval_end fixed AEST. Rerun the same test and approved focused regressions. Record changed files, diff, exact commands, exit codes, output, evidence that the test was unchanged, residual risk, and the human decision. Stop if clean is not green, seeded is not red, another file is needed, or a check is weakened. Do not reverse the patch after implementing the repair, merge, deploy, run a Databricks job, expose credentials, or continue past the noon checkpoint.
```
