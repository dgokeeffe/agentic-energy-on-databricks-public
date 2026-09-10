# Agentic Energy miniwiki

This is an optional Markdown logbook for intent, design thinking, research, and
session notes. Pages are committed with the code so a fresh clone remains useful
without a service, account, or local database. Use ordinary Markdown when it is
helpful; nothing in this directory is required for development.

## Start with

- [`now.md`](now.md) — current focus, open questions, and the next action.
- [`session-template.md`](session-template.md) — optional handoff template.

## Feature horizon

- [`features/agentic-development-learning-loop.md`](features/agentic-development-learning-loop.md)
  — task-aware skills, review handoffs, and the implemented local lesson-replay
  exercise; facilitator placement/rehearsal and native adapters remain pending.
- [`features/full-nemweb-lakeflow.md`](features/full-nemweb-lakeflow.md) — the
  ordered migration from NEMWEB landing through five-minute Gold data and the
  downstream Genie/AI/BI analyst experience.
- [`features/track-c-exploratory-investigation.md`](features/track-c-exploratory-investigation.md)
  — the Track C app reframed as an exploratory analyst workflow (Observe → Ask
  Genie → Review evidence and uncertainty → Save investigation → Follow up), the
  prepared Genie-analysis prototype, and the live two-agent collision in this
  checkout. **Read before editing `nemweb_app/`.**
- [`features/registration-freshness-next-session.md`](features/registration-freshness-next-session.md)
  — the sequenced continuation for issue #7 and pull request #28: the re-review
  gate still open, the E1 issue not yet filed, and the traps that already cost
  time in this work.
- [`features/price-spike-detector.md`](features/price-spike-detector.md) — a
  downstream analytics idea that depends on the NEMWEB Gold contracts.
- [`features/genie-miniwiki-integration.md`](features/genie-miniwiki-integration.md)
  — the lightweight miniwiki technique; the concrete analyst delivery now lives
  in the full NEMWEB feature page.

## Research and decisions

- [`research/nemweb-contract.md`](research/nemweb-contract.md) — source grain,
  freshness, uncertainty, and evidence prompts.
- [`research/draft-issue-source-publication-basis.md`](research/draft-issue-source-publication-basis.md)
  — a verified, not-yet-filed issue body: Bronze overwrites the field that says
  whether a publication timestamp came from AEMO or from our own download clock,
  across 8 tables, with a second fabrication upstream that makes the honest branch
  unreachable.
- [`research/agents-md-practices.md`](research/agents-md-practices.md) — current
  guidance and the decision behind the minimal global agent instructions.
- [`decisions/workshop-flow.md`](decisions/workshop-flow.md) — why the workshop
  uses a rolling intent → discussion → agent → review → next-item loop.
- [`decisions/opening-demo.md`](decisions/opening-demo.md) — the opening
  demonstration that a data defect's result looks correct, the measured evidence
  behind it, and three discarded alternatives including a disproved
  "agent gets caught" premise.
- [`decisions/track-structure.md`](decisions/track-structure.md) — why each track
  is self-contained, why the fixed clock was removed, and what replaced the
  cross-track pair record.
- [`decisions/attendee-isolation.md`](decisions/attendee-isolation.md) — how each
  attendee gets an isolated Lakebase branch and App in one shared workspace, the
  20-concurrent-compute limit that actually binds, and the naming constraints
  that make an explicit attendee slug unavoidable.
- [`decisions/app-value-capture-redesign.md`](decisions/app-value-capture-redesign.md)
  — why the Track C app was reframed from "can I trust this number?" to fuel value
  capture, the Open Electricity design system it borrows, and the availability and
  settlement boundaries it must state on screen.
- [`decisions/two-repositories.md`](decisions/two-repositories.md) — why two
  repositories exist with no shared history, that the public one is canonical, how
  the workshop exercises were migrated and renumbered, and why issue numbers quoted
  in older pages may not resolve.
- [`decisions/facility-dimension-as-of.md`](decisions/facility-dimension-as-of.md)
  — the facility dimension selected registration rows by wall-clock time, so the
  same Bronze data produced different Silver rows; why 290 tests missed it, why the
  pinned instant is derived from the data, and the bug found in the guard itself.
- [`decisions/registration-coverage-metric.md`](decisions/registration-coverage-metric.md)
  — why issue #7's own freshness metric is identically zero and could never fire,
  the market-time alternative that reports 2750 days stale on a fresh load, what
  publication-time coverage measures instead, and the four of the author's own
  guards that mutation testing caught doing nothing.

## How to grow this wiki

Prefer a new page over a giant catch-all file when a topic will live for more
than one session. Link from the nearest page and from `now.md` when it becomes
active. Keep pages free-form: headings, checklists, tables, sketches, and
verbatim evidence are all welcome. When a page becomes historical, leave it in
place and add a short note explaining what changed.
