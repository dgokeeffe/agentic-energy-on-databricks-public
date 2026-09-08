# Workshop workflow decision

## Decision

Participants execute one shared playbook,
[`../../QUICKSTART.md`](../../QUICKSTART.md). Use a
committed, loosely organized Markdown miniwiki for session continuity rather
than a dependency graph or issue database.

## Why

The workshop is a rolling conversation: intent changes as people and agents
learn, side research can become a future feature, and every session should leave
behind enough context for a fresh agent to continue. Plain Markdown is easy to
read, grep, review, branch, and merge. It gives designs, guardrails, research,
and session notes a home rather than forcing every thought into a task title.

## What this does not promise

Markdown does not provide atomic claiming, automatic dependency unblocking,
conflict-free assignments, or machine-enforced approval gates. The team keeps
those boundaries explicit in prose and uses Git, pull requests, tests, and named
human decisions for the controls that need enforcement. A page status is never
proof that code is correct or approved.

## Rolling loop

1. Capture intent.
2. Discuss assumptions and the boundary.
3. Approve a bounded agent brief.
4. Let the agent investigate, draft, implement, and test.
5. Review evidence as a human.
6. Save the outcome and the next item.

The SDLC here is therefore not just “intent → agent → ship.” It is a continuous
room with humans and agents: new ideas enter, bounded work leaves, and the
logbook keeps the thread across 10–20 focused sessions.
