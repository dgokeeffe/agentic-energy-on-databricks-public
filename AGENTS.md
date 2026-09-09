# AI assistant navigator

Use this file with any coding or research assistant. Read the routed source
before acting; do not infer workshop steps from a chat summary.

## Start here

1. Read [`README.md`](README.md) for the repository and hybrid workshop layout.
2. Read [`PRE-REQUISITES.md`](PRE-REQUISITES.md) before setup or workspace
   validation.
3. Send participants to [`QUICKSTART.md`](QUICKSTART.md), which routes them to
   exactly one self-contained track: Track A
   ([`lane_a_business/`](lane_a_business/Instructions.md)), Track B
   ([`lane_b_engineering/`](lane_b_engineering/Instructions.md)), or Track C
   ([`workshop/track_c_app/`](workshop/track_c_app/Instructions.md)). Tracks are
   self-paced; there is no fixed clock and no cross-track dependency.
4. Participants inspect `nemweb_foundation/` for governed contracts, but must
   not deploy it or mutate workspace resources.
5. Before miniwiki or handoff work, read the repository-owned
   [miniwiki skill](.agents/skills/miniwiki/SKILL.md). It works from a fresh
   clone and does not depend on a machine-level skill installation.
6. Read the current Git status before editing. Preserve unrelated and
   uncommitted changes.

## Keyword routing

| Request keywords | Read first | Route |
|---|---|---|
| start, quickstart, participant, track | [`QUICKSTART.md`](QUICKSTART.md) and [`workshop/track-record-template.md`](workshop/track-record-template.md) | Route to exactly one self-contained track. Do not reintroduce cross-track pairing or a fixed clock. |
| prerequisite, setup, access, profile, preflight, PF-1–PF-10 | [`PRE-REQUISITES.md`](PRE-REQUISITES.md) | Separate administrator, facilitator, and participant actions; never guess a workspace capability. |
| issue, workshop-ready, participant | [`.agents/skills/issue-navigator/SKILL.md`](.agents/skills/issue-navigator/SKILL.md) and [`QUICKSTART.md`](QUICKSTART.md) | Optional. A track is completed from its own `Instructions.md`; a GitHub issue is only needed when the work is contributed back. |
| requirement, plan, implement, test, eval, review, pull request | [`.agents/skills/understand-requirement/SKILL.md`](.agents/skills/understand-requirement/SKILL.md), [`.agents/skills/plan-change/SKILL.md`](.agents/skills/plan-change/SKILL.md), and [`.agents/skills/implement-test/SKILL.md`](.agents/skills/implement-test/SKILL.md) | Follow requirement → plan → human approval → implementation → tests → eval → independent review → pull request → human disposition. |
| NEMWEB, foundation, Bronze, Silver, Gold, lineage | [`foundation/AGENTS.md`](foundation/AGENTS.md), [`foundation/Instructions.md`](foundation/Instructions.md), and [`nemweb_foundation/README.md`](nemweb_foundation/README.md) | Use the read-only shared foundation; do not create another data store. |
| facilitator, deploy, gates, evidence | [`foundation/deployment-gates.md`](foundation/deployment-gates.md) and [`foundation/Instructions.md`](foundation/Instructions.md) | Follow the gate sequence. When a capability is unavailable, record `not-run` or `blocked` and label substitutes prepared. |
| isolation, attendee, Lakebase branch, app slug | [`miniwiki/decisions/attendee-isolation.md`](miniwiki/decisions/attendee-isolation.md) and [`workshop/lakebase/scripts/provision-attendee-branches.sh`](workshop/lakebase/scripts/provision-attendee-branches.sh) | One branch and one app per attendee, both from `attendee_slug`. Mind the 20-concurrent-compute limit per project. |
| issue, task, continuation, handoff, miniwiki | [`.agents/skills/miniwiki/SKILL.md`](.agents/skills/miniwiki/SKILL.md), [`miniwiki/now.md`](miniwiki/now.md), the applicable miniwiki page, and the current Git status | Use ordinary Markdown and the Git branch or pull request. No global skill installation, local issue database, or tracker CLI is required. |
| deploy, run job, live data, schedule | [`PRE-REQUISITES.md`](PRE-REQUISITES.md), [`foundation/AGENTS.md`](foundation/AGENTS.md), and [`foundation/Instructions.md`](foundation/Instructions.md) | Facilitators use one numbered prompt at a time. Stop unless the current task explicitly authorises the external action. Every workspace-aware command must name a profile explicitly with `--profile <name>`; never rely on an implicit default. The profile name is the operator's own and is not fixed by this repository. |

## Repository workflow

- Use Git branches and pull requests for implementation review.
- Keep durable design decisions and session continuity in [`miniwiki/`](miniwiki/index.md).
- Put the current objective, evidence, uncertainty, and next action in the
  relevant miniwiki page when another session needs to continue the work.
- Do not require participants or agents to install a local tracker, start a
  database, or run a tracker-specific command.
- Before handing off, report changed files, validation commands and results,
  open uncertainty, and the suggested next Git action.
- Do not commit, push, merge, deploy, grant access, enable live data, or make
  another external change without explicit human authorisation.

## Universal safety rules

- Never write credentials, tokens, private tenant details, or participant data
  to Git, prompts, logs, screenshots, or workshop records.
- Do not merge, deploy, run jobs, enable live data, or unpause schedules without
  explicit authorisation in the current task.
- Treat snapshot and prepared material as non-live evidence.
- Do not weaken, skip, or delete a required check to obtain a pass.
- Make the smallest requested change, run focused validation and
  `git diff --check`, and report exact commands and results.

## Non-interactive shell commands

Always use non-interactive flags for file and remote operations:

```bash
cp -f source destination
mv -f source destination
rm -f file
rm -rf directory
ssh -o BatchMode=yes host command
scp -o BatchMode=yes source host:path
```

Use `HOMEBREW_NO_AUTO_UPDATE=1` for scripted Homebrew commands and `-y` for
package managers that would otherwise prompt.
