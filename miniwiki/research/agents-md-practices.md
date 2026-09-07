# AGENTS.md practices for this operating environment

## Why this page exists

I reviewed current public guidance on `AGENTS.md`, Codex customization, skills,
and Claude project context before trimming the global Pi instructions.

## Research notes

The guidance is consistent on the main point: `AGENTS.md` should be a short,
precise operating manual for durable facts that agents would otherwise repeatedly
rediscover. It should complement, not replace, a README, skills, tests, project
docs, or changing session context.

Useful durable content includes:

- repository orientation and important directories;
- exact build, test, lint, or validation commands;
- engineering conventions and PR expectations;
- constraints, security boundaries, and expensive or dangerous operations; and
- what “done” means and how to verify it.

For larger repositories, guidance can be layered: global personal defaults,
repository instructions, and more specific instructions near a subsystem. The
more specific context adds to the broader context. User instructions remain the
highest-priority direction.

Repeated workflows belong in skills. Changing context belongs in the miniwiki.
A task prompt should carry the goal, relevant context, constraints, and done
criteria. One session should stay focused on one coherent outcome; branch or
start a new session when the work truly diverges or context becomes expensive.

## Sources

- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md)
- [AGENTS.md open format](https://agents.md/)
- [Claude context guidance](https://support.claude.com/en/articles/14553240-give-claude-context-and-better-prompts)

## Applied decision

The global `~/.pi/agent/AGENTS.md` was intentionally kept small. It now contains only personal defaults, miniwiki
continuity, subagent boundaries, Databricks skill routing, and concise writing
preferences. Detailed repeatable behavior lives in skills; project-specific
commands and safety rules live in each repository's `AGENTS.md`.

## Open question

If a rule is repeated because agents keep missing it, first decide whether it is
a stable global fact, a project rule, a miniwiki handoff, a skill, or a test/CI
guard. Do not automatically add another paragraph to the global file.
