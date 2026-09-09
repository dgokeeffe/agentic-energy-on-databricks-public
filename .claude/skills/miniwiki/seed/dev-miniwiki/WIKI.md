# dev-miniwiki

Personal, cross-session, cross-host developer log-book. Adapts
Karpathy's "LLM Wiki" pattern
(https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
to software development.

- **Raw sources** = git branches and the chat sessions that produced
  them. The wiki references them (branch, base commit, host) but never
  owns them.
- **The wiki** = the markdown under `dev-miniwiki/`. LLM-written,
  User-browsed.
- **The schema** = this file. It tells any agent how to read and
  maintain the wiki.

Lives on its **own long-lived git branch** (never merged to `main`),
checked out to a directory of your choosing on each host and kept current
by pull/push. The `dev-miniwiki` plugin records that directory per-host
(`~/.config/miniwiki/config.json`) and locates the wiki from it — it makes
no assumption about the branch name, the checkout location, or which repo
you invoke it from. (See the plugin README for one-time setup.)

## The two lifecycles — do not collapse them

**`journal/` — ephemeral working captures.** Dated, point-in-time
entries: a handoff so a fresh agent can resume, an idea/spark that
popped up mid-session, a note on a path being tried. They accumulate
fast and age out. Each records the branch / commit / host it came from.
Groom archives an entry once its content has been distilled into a topic
page, or once the path it described was abandoned.

**`topics/` — living distillations.** One page per development area
(e.g. `transaction-management.md`). This is **not** a record of what
landed in `main` — it is a synthesis that is reshaped continuously as
the work evolves across many PRs over weeks. For calibration: a single
topic page is routinely rewritten across many commits over a few days,
growing past several hundred lines — terminology reconciled, approaches
replaced, an implementation-state section added. A topic page lives like
that. It **survives even when its working branch is reset or
thrown away** — that is the whole point: the distilled thinking outlives
the code that came and went.

A topic page distills **paths taken *and not taken*** — rejected
approaches and *why* they were dropped are first-class content here.
(This is exactly the rationale that does **not** belong in code comments
per a typical repo's agent guide — e.g. `AGENTS.md`; the miniwiki is its
proper home.)

`kind` (handoff / idea / thread / note) is **frontmatter, not a folder** —
everything about one area stays together under its topic regardless of
kind.

## What belongs here — pattern, not event

The wiki is a **knowledge base to refer back to**. The distinction that
governs what to capture is *knowledge vs artifact-instance*, and it is
**independent of how detailed the knowledge is**: a topic page about a
design can run to hundreds of lines and still be pure knowledge — detail
about *how the system/design works* belongs here at any depth. What does
**not** belong is the specifics of the *one artifact you were looking at*
(a PR's findings, a ticket's particulars, a single bug's trace), unless
they reveal a durable fact. Keep the *diet* ("am I eating healthily"), not
the *meal* ("what I ate yesterday") — where meal-vs-diet is
event-vs-pattern, not short-vs-long.

**Artifact-review/investigation saves need an explicit altitude check.**
When a `save` follows a review or investigation of a *specific artifact*
(a PR, ticket, design doc, bug), the session holds both the artifact's
specifics and durable knowledge, and **only the user knows why they were
looking** — so which half is worth keeping is theirs to decide, not the
agent's to assume. The capture agent MUST **stop and ask**: save *this
artifact's specifics*, *the general knowledge*, or *both*? This is a
**blocking question, never a passing mention** (mentions get skimmed
past). It applies **only** to artifact-review/investigation saves —
ordinary development-session saves capture normally, without asking.

## Maintenance principles

The model is a **selective editor, never a bulk archive or a
whole-system re-summarizer.** Inference is slow in proportion to the
context it chews, so every rule here exists to keep one iteration cheap:
small read, small edit, never re-process what is already distilled.

- **Capture, then distill — two passes, two agents.** A `save` drops a
  raw dump into `inbox/` and commits it immediately (capture); a separate
  fresh agent later folds it into `journal/` + `topics/` (distill). Never
  "read everything, think, rewrite the wiki" in one pass. See *The save
  pipeline*.
- **Edit impacted sections, never rewrite the page.** Folding into a
  topic = editing the specific sections the new work touched (append a
  *Path not taken*, update *Current state*, refresh the summary). Using
  `Edit` to change three lines beats re-emitting an 800-line page through
  the model — that re-emission is the single biggest avoidable cost.
- **Keep topics atomic — one concern per page.** Splitting one large area
  into per-concern pages (e.g. data-model / api / drain / storage /
  roadmap) is the model: smaller pages mean smaller reads and smaller
  edits. Split a page that has grown to span two concerns rather than
  letting concerns blend.
- **Every topic opens with a canonical summary** (≤5 lines): the durable
  state of the area. `resume` and any "answer" read *that* first and only
  drill into sections or journal entries when it is insufficient.
- **Retrieve narrowly.** Locate with pointers, read the few sections that
  matter, never ingest a folder. Already the skill's contract.
- **Put work where the resource is cheap.** The session agent has a huge
  context — slow to emit, expensive to read more into — but it alone holds
  the session, so it only *captures* (a terse dump). A fresh small-context
  agent, where read-modify-write is fast, does the *distilling*. Judgment
  stays with the capturer (encoded as dump hints); only the mechanical
  editing moves. See *The save pipeline*.
- **Prefer edit-shaped work over open-ended.** "Add this path-not-taken,"
  "refresh this summary," "merge these two captures" — not "reorganize
  the wiki however seems best." Open-ended re-synthesis is slow and drifts.
- **Batch grooming.** Sweep staleness across many entries in one pass,
  not one entry per turn.

## The save pipeline: capture → distill

A `save` is **two stages run by two agents**. This is the whole latency
story, so it is load-bearing.

**Stage 1 — capture (the session's own agent, foreground, fast).** That
agent is the slow one: its context is huge, so every token it emits and
every file it reads is costly. So it does the *minimum* — appends **one
raw dump** to `inbox/`, commits and pushes just that file, and returns.
The session is now safe on the remote in seconds, which is the whole
point of a save. It does **not** edit topics, read long pages, or touch
`index`/`log`.

**Stage 2 — distill (a fresh subagent, background).** A separate
small-context agent drains `inbox/`: per dump it writes the polished
`journal/` entry, applies the dump's changeset to `topics/`, refreshes
canonical summaries, updates `index.md`/`log.md`, secret-scans,
commits+pushes, and deletes the drained dump. Its context is small, so
the read-modify-write of topics — the slow part for the session agent —
is fast here. The user never waits for it.

Why split this way: at save time the session agent's context is being
**dumped anyway**, so protecting it buys nothing; the only remaining cost
is wall-clock latency, and editing living topics is what's slow. So that
work moves to where context is cheap (a fresh agent) and off the critical
path (background). `resume` is the mirror image — it runs at the *start*
of a fresh window where context is precious, so it keeps narrow retrieval.

**Capture commits first.** A crashed or never-spawned distiller therefore
loses nothing: the dump is committed in `inbox/` and the next invocation
re-drains it. Distillation is a second commit on top.

**The dump is a changeset the session agent authors — including
corrections.** It is the only party holding *both* the new session
information *and* its memory of what the wiki said when it read it at
startup, so it alone knows which existing claims are now wrong. The dump
therefore carries new facts **and anchored corrections** — *"topic X,
section Y, «quoted stale line» is wrong because Z; replace with W."* The
distiller applies these; it does not re-derive what changed.

**Self-scan for corrections on every save — the user should not have to
ask.** As part of authoring the dump, the capture agent reviews the
session for two kinds of correction the user gave it, and folds both in
**without being told to**:

- **(a) How the agent worked** — the user caught it coining a synonym,
  diffing the wrong base, over-building surface, etc. → a
  **`code-guardrails` change**. Additive and low-risk, so applied
  automatically; the save confirmation *lists* what was folded in so the
  user can veto, but silence means kept. Only *generalizable* rules
  qualify — a one-off "not that file" is not a guardrail. Guardrails are
  **integrated, not appended**: merge into the closest existing entry
  when it's the same rule on a new axis; new entry only for a new axis.
- **(b) A wiki/design fact** — the user corrected content in an existing
  topic. → an **anchored correction** (the mechanism above). Recorded so
  it is never lost, but **never silently applied**: the distiller matches
  the anchor or flags it for `groom`. Merging or rewording existing
  guardrails is itself a content edit, so it routes through this
  anchor/flag path too — the page may shrink, but not without the user
  seeing the rewrite.

The user still does the *noticing* (the agent can't reliably detect its
own stumble) and corrects in-session as normal; what changes is that the
agent captures the correction itself at the next save instead of waiting
to be told.

**The distiller verifies, never guesses.** It locates each correction's
anchor (section header + quoted snippet) in the *live* file. Match →
apply. No match (stale memory, or the file moved on) → **flag for the
next `groom`**, never edit. A fuzzy memory degrades to "flagged," not to
a wrong edit. Corrections cover only topics the session agent actually
read.

## Layout

```
dev-miniwiki/
  WIKI.md          # this schema
  index.md         # catalog of topics + status
  log.md           # append-only timeline; one line per capture
  inbox/           # raw capture dumps awaiting distillation — transient queue
  journal/         # dated working captures (written by the distiller) — ephemeral
  topics/          # one living distillation per area — survives branch resets
  archive/         # stale / abandoned / fully-distilled entries land here
```

The `/miniwiki` skill itself ships in the `dev-miniwiki` plugin, not in
this tree.

## inbox/ dump format

Raw, transient capture — the distiller's input queue. Terse fragments are
fine; the distiller writes the prose and deletes the file once drained.

Filename: `inbox/YYYY-MM-DDTHHMMZ-<slug>.md` (UTC timestamp orders the
queue; `-2` on collision). Frontmatter = the same working context as a
journal entry (`created`, `host`, `branch`, `base_commit`, `kind`,
`topics`) plus `distill: pending`.

Body, two parts:

1. **Brain-dump** — what happened: the problem, where it stands, what was
   tried, what's next, links to PRs/code. Fragments, not prose.
2. **Distill hints** — the changeset, edit-shaped, one per line, only for
   topics the agent actually read/touched this session:
   - `new → <topic>/<section>: <fact>`
   - `correction → <topic>/<section>: «quoted stale text» wrong because
     <reason>; replace with <new text>`
   - `summary-delta → <topic>: <what changed in the ≤5-line summary>`
   - `path-not-taken → <topic>: <approach> rejected because <reason>`
   - `new-topic → <slug>: <one-line scope>`

## journal/ entry format

Written by the distiller from an inbox dump. Filename:
`journal/YYYY-MM-DD-<slug>.md` (suffix `-2`, `-3` on
same-day collision). Frontmatter:

```yaml
---
created:     2026-06-29T13:59Z     # date -u +%Y-%m-%dT%H:%MZ
updated:     2026-06-29T13:59Z
host:        ip-10-91-13-194        # hostname
branch:      <working-branch>       # the WORKING branch, not miniwiki
base_commit: a1b2c3d4 <commit subject line>
                                    # git log --oneline -1 of the working worktree.
                                    # Record hash AND title: the title survives rebase
                                    # and is grep-findable forever; the bare hash does not.
kind:        handoff                # handoff | idea | thread | note
status:      active                 # active | landed | stale
topics:      [<area-slug>]
---
```

Body: whatever a future agent needs to pick this up cold — the problem,
where things stand, what was tried, what's next, links to PRs/code.

## topics/ page format

Filename: `topics/<topic-slug>.md`. Frontmatter: `title`, `status`
(`active` | `done` | `abandoned`), `updated`. Recommended sections:

- **Summary** — the canonical summary: ≤5 lines, the durable state of the
  area, refreshed from changed evidence on each `save`. Read first by
  `resume`/answer; everything below is drilled into only when this is
  insufficient.
- **Current state** — where the work stands now.
- **Open threads / next steps.**
- **Paths not taken** — approaches considered and rejected, with the
  reason. Append-only in spirit; this is the highest-value section.
- **Links** — journal entries, PRs, in-branch design docs, key code.

## log.md

Append-only timeline, newest at the bottom. A pipe-delimited GFM table:
one row per capture. The two header rows (column names + `---` separator)
are static at the top; every `save` appends a data row beneath them. The
`---` separator is what makes GitHub render it as a table — without it the
pipes get mangled into broken text. Data rows keep the plain `a | b | c`
form, so the file stays greppable (`tail`, `awk -F'|'`) exactly as before.

```
utc | mode | topic | kind | branch @ host | summary | path
--- | --- | --- | --- | --- | --- | ---
2026-06-29T13:59Z | save | <area-slug> | handoff | <working-branch> @ <host> | one-line summary | journal/2026-06-29-<slug>.md
```

## index.md

Catalog of topics — link, status, one-line summary, last-updated.
Updated by the distiller when a topic is created/retired or its canonical
summary changes — not on every save.

## The /miniwiki skill

Single skill, three modes (details in `skills/miniwiki/SKILL.md`):

- **save** — capture the session as one `inbox/` dump + changeset and
  commit it immediately; a background distiller folds it into
  journal/topics/index/log (see *The save pipeline*).
- **resume `<topic|entry>`** — drain any pending `inbox/` first, then read
  the topic's canonical summary + linked journal entries and produce a
  rehydration brief. Read-only otherwise.
- **groom** — drain `inbox/`, then run the staleness pass (semantics
  below). Always show the plan before moving anything.

## Conventions

- Timestamps: ISO-8601 UTC, minute precision (`date -u +%Y-%m-%dT%H:%MZ`).
- Topic slugs: kebab-case.
- Auto-derived per capture, from the **working worktree** (where the
  agent is invoked), never the miniwiki worktree:
  `branch = git branch --show-current`, `base_commit = git log
  --oneline -1` (hash + title — the title outlives a rebase that
  orphans the hash), `host = hostname`, `created/updated = date -u`.
- Locate the miniwiki directory from the plugin's per-host config
  (`~/.config/miniwiki/config.json`, or `$MINIWIKI_DIR`). Writes go there;
  the captured branch is the working one.
- Cross-cutting entry: `topics: [a, b]`; file under the primary topic,
  link it from the others.

## Groom semantics

- **drain `inbox/` first:** run the distiller on any pending dumps before
  assessing staleness, so the topic pages are current. Resolve any
  corrections the distiller **flagged** (anchor not found) against the
  live topic now.
- **journal entries:** if the branch still exists and is active → leave.
  If its content is already distilled into the topic page, or the path
  was abandoned → archive (record the abandoned path's lesson in the
  topic's *Paths not taken* before moving).
- **topic pages:** stay `active` across PR churn. A landed PR is normal
  mid-feature, **not** a signal to retire the topic. Retire (→ `done` /
  `abandoned`, then archive) only when the user says the feature is
  finished/dead, or after long inactivity — and only with confirmation.
- Also flag (Karpathy "lint"): contradictions between pages, stale
  claims a newer session superseded, topics with no recent journal
  activity.
