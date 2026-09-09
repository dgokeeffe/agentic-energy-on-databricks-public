---
title:   Code guardrails (cross-cutting)
status:  active
updated:
---

# Code guardrails

Cross-cutting rules to apply in **any** code work, not tied to one
subsystem. Each is stated generally, with a concrete example of where it
bit. Integrate new guardrails as they come up — merge into an existing
entry when it's the same rule on a new axis, add a new entry only for a
genuinely new axis, and consolidate/reword when entries overlap. This page
is editive like any topic, not an append log. Keep each entry as *rule →
why → how to apply → example*.

## How this page fills up (don't hand-author it)

This topic is a **fixture of the miniwiki pattern**, not an ordinary
subsystem topic — the schema refers to it by name. It starts empty and
grows on its own: whenever you catch the agent working *the wrong way*
(coining a synonym for an existing verb, diffing the wrong base,
over-building speculative API surface, mis-naming for the local module,
…) and correct it in-session, the next `/miniwiki save` **self-scans for
that correction and folds a generalizing rule in here**, without being
told to (see `WIKI.md` → *Self-scan for corrections on every save*, branch
(a)). The save confirmation lists what it added so you can veto.

Only *generalizable* rules qualify — a one-off "not that file" is not a
guardrail. New guardrails are **integrated, not appended**: merged into the
closest existing entry when they're the same rule on a new axis; a new
entry only for a genuinely new axis.

Delete this "How this page fills up" section once you have real guardrails
and the mechanism is second nature — or keep it as a reminder. Either way,
the numbered entries below are yours to accrue.

## Entry format (template — replace with real guardrails)

<!--
## 1. <One-line rule name>

**Rule.** What to do, stated generally.

**Why.** The cost of getting it wrong / the value of the rule.

**How to apply.** The concrete tell — the moment in coding where this
rule should fire, and what to do then.

**Example.** Where it actually bit, concretely.
-->

_(no guardrails yet — the first `save` that folds one in replaces this
line)_

## Links

_(journal entries where guardrails were first extracted land here)_
