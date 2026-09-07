---
name: miniwiki
description: >-
  Maintain a loosely organized wiki of committed Markdown pages for feature
  ideas, research, decisions, preferences, guardrails, and session continuity.
  Use when the user asks to read up on a topic, choose the next thing to build,
  or save what was learned. Keep the pages free-form and let the page titles and
  page boundaries provide the only lightweight organization.
metadata:
  version: "0.2.0"
---

# miniwiki

Use a directory of ordinary Markdown files as the project's engineering logbook.
The pages are committed to the working branch so a fresh session can recover the
conversation without relying on chat history or a ticket service.

This is deliberately not a ticket system, issue graph, CSV board, local
database, or single long-running plan. The complete skill is stored in this
repository so it works from a fresh clone in Omni Sandbox and other assistants;
it does not depend on a machine-level skill installation. Feature designs can sit at different stages of readiness.
Unrelated research, side reviews, personal preferences, and guardrails can live
beside implementation work.

## How to use it

When this skill is available, treat these requests as miniwiki operations:

- **“Read up on X in miniwiki.”** Search the Markdown pages, read the relevant
  pages, and summarize what is known, uncertain, related, and worth asking next.
- **“What is the next thing to implement?”** Search the pages and identify the
  most useful focused next action from the existing feature horizon. Do not
  invent a new ticket hierarchy.
- **“Let’s save what we learned to miniwiki.”** Put the useful reasoning,
  alternatives, evidence, and unresolved questions into the relevant page or a
  new page, then link it from nearby context when helpful.
- **“Wind down.”** Stop opening new work. Save the session result, open threads,
  and likely next items before ending.

## Finding the right page

1. Look for a local `miniwiki/` directory or the project's documented wiki root.
2. If an index or current-focus page exists, read it, but do not require either
   page to exist.
3. Search filenames and page contents with grep-like tools for the user's topic.
4. Read the best matching pages before creating anything new.
5. Create a new descriptive page only when the topic deserves a durable home.

Control organization mainly through page titles and where a page is split. Do
not force every page into a schema. Let the author organize the inside of a page
in whatever way makes the thinking easiest to recover.

## Working inside pages

Free-form content is intentional. Headings, checklists, tables, sketches,
quoted discussion, strange intermediate task lists, and long-form notes are all
allowed. Do not rewrite a page into a cleaner task format merely because its
structure is unusual.

When continuing a feature, preserve its history and uncertainty. Record:

- what prompted the feature or question;
- what has been learned and from where;
- assumptions, alternatives, and what could make the conclusion wrong;
- what is in and out of scope;
- the smallest useful next action;
- evidence, tests, or links; and
- unresolved questions, risks, or human decisions.

These are suggestions, not required fields. A short note is better than losing
context because a template felt too heavy.

## Session rhythm

Use the miniwiki as a rolling conversation between people and agents:

1. Recover the relevant context.
2. Discuss or research the question.
3. Choose one focused action when something is ready.
4. Do the work without silently expanding scope.
5. Save what changed or was learned.
6. Leave the next question visible for the next session.

A feature may move backward from implementation to discussion. A completed
session action does not mean the entire feature is complete.

When a session becomes expensive or unfocused, stop opening new work. Write the
handoff and next items first. Prefer several focused sessions over one giant
context window.

## Lightweight handoff

There is no mandatory status vocabulary. When useful, leave a compact note such
as:

```text
What changed or was learned: ...
Evidence and links: ...
Still uncertain: ...
Next question: ...
```

Use a human-readable owner or person name when a next action truly needs one.
Do not manufacture IDs, priorities, dependency edges, or completion claims just
to make the Markdown look like a tracker.

## Boundaries

The miniwiki records intent and continuity; it does not grant authority. An
agent may research, write notes, draft code, implement, test, and prepare a
handoff. Keep human decisions, review, merge, deployment, and access changes
explicit and separate.

Never put credentials, private tenant details, or sensitive result data in the
wiki. If the repository has a wiki link checker, use it, but do not add rigid
workflow tooling unless the user asks for it.
