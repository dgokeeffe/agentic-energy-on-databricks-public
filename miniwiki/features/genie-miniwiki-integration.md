# Databricks Genie miniwiki integration

## Why this exists

Use the miniwiki as a lightweight backlog and engineering logbook for Genie
coding sessions. It should make it easy to answer:

- What feature or question were we discussing?
- What did we learn?
- What is the next small thing to implement?
- What should the next person or agent know?

The repository uses ordinary Markdown pages and validation scripts for miniwiki
continuity; no repository-owned skill is required.

## Technique

Keep feature ideas, research, side reviews, guardrails, and session notes on
separate free-form pages. Let pages sit at different stages of readiness. Use
links and plain language for relationships; do not turn the miniwiki into a
second issue tracker.

At the end of a focused session, save the useful reasoning, result, evidence,
open questions, and one bounded next item. When a feature is blocked, record the
question that would unblock it instead of inventing work for the agent.

## Optional Genie context

When it helps the next session, note the intended audience/question, relevant
semantic or source context, benchmark questions, and freshness or governance
concerns. Keep API and deployment details in the code and the relevant
Databricks documentation, not in this backlog skill.

## Session handoff

- **Current state:** the lightweight skill and free-form page template are ready.
- **Evidence:** miniwiki validation and the repository test suite remain the
  normal checks.
- **Open risks:** do not guess workspace-specific Genie capabilities.
- **Next item:** use the skill on one concrete Genie feature and capture what the
  next session should implement.
