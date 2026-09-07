# Workshop quickstart

The workshop runs through GitHub Issues and works in Omni Sandbox with ordinary
Git, Markdown, and prepared fixtures. Participants do not install a tracker or
provision Databricks resources. The [facilitator run of show](docs/facilitator/workshop-run-of-show.md)
is the only clock source.

## Form a pair

Keep one person responsible for the business outcome and one responsible for
engineering quality. Record both in the [pair record](docs/participant/workshop-pair-record.md).
A pair owns one change together; these are responsibilities, not separate lanes.

## Select one issue

1. Open the repository's GitHub Issues page.
2. Select one open issue labelled `workshop-ready`.
3. Record its number, operator outcome, acceptance points, and stops.
4. Read [`AGENTS.md`](AGENTS.md), the complete issue,
   [`nemweb_foundation/`](nemweb_foundation/README.md), and the named starter.

Use the [issue navigator](.agents/skills/issue-navigator/SKILL.md), then follow
this sequence without skipping a stage:

```text
understand measurable requirements
→ propose exact files and deterministic tests
→ approval by a person who did not draft the plan
→ branch and implement
→ deterministic tests
→ agentic eval
→ independent adversarial review
→ pull request with Closes #N
→ person accepts, sends back, rejects, or stops
```

The detailed instructions are in the
[participant playbook](docs/participant/workshop-playbook.md). Start a fresh
assistant conversation for requirement, implementation, and review stages, and
carry facts through the issue, plan, pair record, files, and command output.

## Local limits

Participants may inspect `nemweb_foundation/`, `nemweb_app/`, `nemweb_ml/`, and
`workshop/lakebase/`. They may run local tests and read-only validation. They do
not deploy, run Databricks jobs, create Lakebase or Unity Catalog resources,
change grants, enable live NEMWEB, change schedules, push without approval, or
merge. Prepared fixtures must stay visibly labelled non-live.

Start with:

```bash
git status --short
make validate-local
```

If a required workspace or preview is unavailable, use the published prepared
fixture and record the limitation. Never turn an unrun platform step into a
pass.
