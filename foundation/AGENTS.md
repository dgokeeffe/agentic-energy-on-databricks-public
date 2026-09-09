# Foundation assistant routing

Facilitators prepare and operate the shared foundation. Participants may inspect
[`../nemweb_foundation/`](../nemweb_foundation/README.md) for governed contracts
and tests, but must not deploy it or mutate workspace resources. The participant
entry point is [`../QUICKSTART.md`](../QUICKSTART.md).

| Request | Read first | Action |
|---|---|---|
| participant issue | [`../.agents/skills/issue-navigator/SKILL.md`](../.agents/skills/issue-navigator/SKILL.md) | Follow the shared issue → plan → approval → implementation → tests → eval → review → pull request → human disposition lifecycle. |
| source, grain, correction | [`skills/00-nemweb-navigator/SKILL.md`](skills/00-nemweb-navigator/SKILL.md) | Preserve fixed NEM semantics. |
| snapshot | [`skills/01-snapshot-mode/SKILL.md`](skills/01-snapshot-mode/SKILL.md) | Keep snapshot and live roots separate and label non-live output. |
| live landing | [`skills/02-live-landing/SKILL.md`](skills/02-live-landing/SKILL.md) | Require current facilitator approval and both live gates. |
| evidence | [`skills/03-evidence-gates/SKILL.md`](skills/03-evidence-gates/SKILL.md) | Capture exact IDs and fail closed. |

Before a workspace command, read [`../PRE-REQUISITES.md`](../PRE-REQUISITES.md).
Every workspace-aware command uses `--profile DEFAULT`. Guidance is not approval
to deploy, run a job, access live data, provision Lakebase, or change a schedule.
