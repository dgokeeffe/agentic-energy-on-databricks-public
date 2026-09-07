# Agentic Energy miniwiki

This is the workshop's shared Markdown logbook. It carries intent, design
thinking, research, guardrails, session evidence, and the next safe action across
people and agent sessions. Pages are committed with the code so a fresh clone is
useful without a service, account, local database, or machine-level skill
installation. The repository-owned workflow is documented in
[`.agents/skills/miniwiki/SKILL.md`](../.agents/skills/miniwiki/SKILL.md).

## Start with

- Workshop participants start in [`../docs/participant/workshop-playbook.md`](../docs/participant/workshop-playbook.md),
  then fill [`../docs/participant/workshop-pair-record.md`](../docs/participant/workshop-pair-record.md).
- [`now.md`](now.md) — current focus, open questions, and the next action.
- [`session-template.md`](session-template.md) — copy this when a session needs
  a durable handoff.
- [`guardrails.md`](guardrails.md) — non-negotiable safety and workshop limits.

## Feature horizon

- [`features/agentic-development-learning-loop.md`](features/agentic-development-learning-loop.md)
  — task-aware skills, review handoffs, and the implemented local lesson-replay
  exercise; facilitator placement/rehearsal and native adapters remain pending.
- [`features/full-nemweb-lakeflow.md`](features/full-nemweb-lakeflow.md) — the
  ordered migration from NEMWEB landing through five-minute Gold data and the
  downstream Genie/AI/BI analyst experience.
- [`features/price-spike-detector.md`](features/price-spike-detector.md) — a
  downstream analytics idea that depends on the NEMWEB Gold contracts.
- [`features/genie-miniwiki-integration.md`](features/genie-miniwiki-integration.md)
  — the lightweight miniwiki technique; the concrete analyst delivery now lives
  in the full NEMWEB feature page.

## Research and decisions

- [`research/nemweb-contract.md`](research/nemweb-contract.md) — source grain,
  freshness, uncertainty, and evidence prompts.
- [`research/agents-md-practices.md`](research/agents-md-practices.md) — current
  guidance and the decision behind the minimal global agent instructions.
- [`decisions/workshop-flow.md`](decisions/workshop-flow.md) — why the workshop
  uses a rolling intent → discussion → agent → review → next-item loop.
- [`decisions/opening-demo.md`](decisions/opening-demo.md) — the opening
  demonstration that a data defect's result looks correct, the measured evidence
  behind it, and three discarded alternatives including a disproved
  "agent gets caught" premise.

## How to grow this wiki

Prefer a new page over a giant catch-all file when a topic will live for more
than one session. Link from the nearest page and from `now.md` when it becomes
active. Keep pages free-form: headings, checklists, tables, sketches, and
verbatim evidence are all welcome. When a page becomes historical, leave it in
place and add a short note explaining what changed.
