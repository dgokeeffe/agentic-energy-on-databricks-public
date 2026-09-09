---
name: miniwiki
description: User's personal cross-session, cross-host dev log-book (Karpathy LLM-wiki pattern). Invoke for "/miniwiki", or when the user wants to save the current session/feature/problem/idea to their wiki, resume work from a saved topic or handoff, or groom stale entries. Captures timestamp + working branch + host into the markdown wiki in the user's configured miniwiki directory.
---

# /miniwiki

A personal dev log-book that persists across sessions, hosts, and branch
resets. The wiki content and its full schema live in a git-branch checkout
the user picks; this skill locates it from a per-host config pointer
(`~/.config/miniwiki/config.json`). **This skill is thin — the schema file
(`WIKI.md`) in that directory is the source of truth.** In particular, read
its *Maintenance principles*, *The save pipeline*, and *inbox/ dump format*
before a `save`.

## Save vs resume optimize opposite things

`save` and `resume` optimize **opposite** things; keep them distinct:

- **`save` optimizes latency.** It runs inside a busy session whose
  context is being *dumped anyway*, so protecting that context buys
  nothing — the cost that matters is the wall-clock seconds you wait. So
  the session agent does the **minimum**: write one raw `inbox/` dump,
  commit+push just that file, return. The slow work — editing living
  topic pages — is handed to a **fresh background distiller** (small
  context = fast read-modify-write) and you never wait for it. Do **not**
  spawn subagents for sync/locate on a save; they are pure round-trip
  latency. Do **not** edit topic pages from the session agent.
- **`resume` optimizes context.** It runs at the *start* of a fresh
  window where context is precious, so it retrieves **narrowly** (canonical
  summary first, drill only as needed).

See `WIKI.md` → *The save pipeline* for the full rationale.

## Locate the wiki (all modes)

Resolve the miniwiki directory inline (one command, no subagent):
`WIKI="${MINIWIKI_DIR:-$(jq -r '.wiki_dir // empty' ~/.config/miniwiki/config.json 2>/dev/null)}"`.

If `$WIKI` is empty or not an existing directory → **run First-run bootstrap
(below)** and stop for that turn unless the user has just given a path to
continue with. Otherwise `$WIKI` **is** the wiki root (the user chose the
exact dir — no `dev-miniwiki` suffix to append).

**Sync only when the branch has an upstream.** The wiki works fully
local-only (a plain `git init` dir, no remote); pull/push apply only when a
remote is set. Treat this as the guard everywhere below — `pull`, `push`,
and `push` on the distiller are all conditioned on it:
`git -C "$WIKI" rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1`. If it
succeeds, `git -C "$WIKI" pull` inline (one fast command — no subagent);
resolve any conflict fully before continuing. If it fails (no upstream),
skip the pull — the local checkout is the source of truth.

Working context is auto-derived inline from the **current** worktree
(where the skill was invoked, *not* the miniwiki directory):
`branch=$(git branch --show-current)`,
`commit=$(git log --oneline -1)` (hash **and** title — the title survives
a rebase that orphans the hash), `host=$(hostname)`,
`now=$(date -u +%Y-%m-%dT%H:%MZ)`.

## First-run bootstrap (config missing or dir gone)

Runs when no miniwiki directory is configured on this host. **This host
only** — the config is per-host, because each machine checks out the branch
to its own local path.

Let `SEED="$(git rev-parse --show-toplevel)/.claude/skills/miniwiki/seed/dev-miniwiki"`.

1. **Get the path.** Ask the user for the **absolute path** to a git
   directory they own — any branch, any location. **When you ask, warn them
   plainly:** the skill will run `git commit` on that branch **by itself,
   without confirming each time** (and `pull`/`push` too, *if* it has a
   remote) — so it must be a branch they own and don't share (never `main`,
   never their working feature branch). Let `$WIKI` be that path. The skill
   does **not** create the branch/repo itself, but if the user doesn't have
   one yet, **guide** them (they run the commands) to whichever fits:
   - **Local-only** (simplest — no remote, no cross-host sync): any empty
     dir they `git init`. Sync is off until they add a remote later.
   - **Sibling worktree** (personal repo, with sync): orphan branch +
     worktree —
     `git switch --orphan "$B" && git commit --allow-empty -m init && git push -u origin "$B"`,
     then `git worktree add ../miniwiki "$B"`; give us `../miniwiki`.
   - **Shared monorepo (e.g. universe with `git pp`):** make a branch named
     per the repo's convention, push it however they normally do (e.g. `git
     pp` opens a PR — they close the PR but keep the branch), then check that
     branch out to a directory of their own and give us that.
   On a shared repo the branch name must not collide with other people's —
   follow **that repo's own branch-naming convention** (ask the user; don't
   assume a format); `$B` is whatever name they choose. Either way we only
   need the final directory; we don't care how the repo was made.
2. **Inspect `$WIKI` and act by case — the empty-vs-non-empty check is a
   destructive-safety guard, get it right:**
   - **`$WIKI/WIKI.md` exists** → existing wiki, do **not** overwrite.
     **Record it** (step 3), then sanity-check the expected structure
     (`inbox/ journal/ topics/ archive/`, `index.md`, `log.md`). If any are
     missing, **report exactly which** and offer to create only those from
     `$SEED` (never clobber existing files).
   - **`$WIKI` is empty or does not yet exist** → **tell the user plainly you
     will create `WIKI.md` and the seed layout at `$WIKI`**; after they're on
     board, `mkdir -p "$WIKI" && cp -R "$SEED/." "$WIKI"/`, then commit:
     `git -C "$WIKI" add -A && git -C "$WIKI" commit -m "miniwiki: scaffold"`,
     then push per the upstream guard from *Locate* (local-only dirs have no
     upstream — nothing to push, the commit is still safe).
   - **`$WIKI` is non-empty but has no `WIKI.md`** → **stop and complain.** Do
     not dump seed files on unrelated content. The user likely expected a
     *subdirectory*: ask whether to use `$WIKI/miniwiki` (or another subdir
     they name), then re-run this bootstrap against that path.
3. **Record the path** for next time:
   `mkdir -p ~/.config/miniwiki && printf '{"wiki_dir": "%s"}\n' "$WIKI" > ~/.config/miniwiki/config.json`.
   Confirm to the user where it was recorded.

After bootstrap completes, proceed with the requested mode.

## Modes

### `save [topic]` (default when given a description)

**Stage 1 — capture (foreground, fast — this is all the user waits for):**

1. Locate the wiki + derive working context (above).
2. **Altitude check (blocking — only if this save follows a review or
   investigation of a specific artifact: a PR, ticket, design doc, bug).**
   Such a session holds both the artifact's specifics and durable
   knowledge, and only the user knows why they were looking — so **stop
   and ask**: save *this artifact's specifics*, *the general knowledge*,
   or *both*? A blocking question, never a passing mention (mentions get
   skimmed). Ordinary development-session saves skip this and capture
   normally. **If the question times out, wait — don't auto-continue** (see
   Notes → *A timeout is not an answer*). See WIKI.md → *What belongs here
   — pattern, not event*.
3. Write **one** dump to `$WIKI/inbox/<now>-<slug>.md` in the *inbox/ dump
   format* from WIKI.md: a terse brain-dump plus **distill hints**
   (`new` / `correction` / `summary-delta` / `path-not-taken` /
   `new-topic`). Infer `kind` and `topics`. You are the only agent that
   holds both the new info and your memory of what the wiki said at
   startup, so emit **anchored corrections** for anything the session
   proved stale — quote the stale snippet + name the topic/section — but
   only for topics you actually read this session. Fragments, not prose.
   **Also self-scan the session for corrections the user gave you and fold
   them into the dump without being told** (WIKI.md → *Self-scan for
   corrections on every save*): (a) corrections to *how you worked*
   (coined a synonym, wrong diff base, …) → a `code-guardrails` change,
   **integrated not appended** (merge into the closest existing guardrail
   when it's the same rule on a new axis; new entry only for a new axis);
   list these in the confirmation so the user can veto. (b) corrections to
   *a wiki/design fact* → an anchored correction (never silently applied;
   the distiller matches-or-flags). Only generalizable rules become
   guardrails — a one-off is not one.
4. Commit just that file, foreground:
   `git -C "$WIKI" add <dump> && git -C "$WIKI" commit -m "capture: <topic> — <short>"`,
   then **push if an upstream exists** (the guard from *Locate*) —
   `git -C "$WIKI" push`. The commit is durable locally either way; the push
   makes it durable on the remote when there is one. (Confirm `kind`/`topics`
   with the user if unsure — cheap, doesn't block durability.)

**Stage 2 — distill (background, fire-and-forget):**

5. Spawn **the distiller** (below) as a background Sonnet subagent. Do
   **not** wait on it; return control to the user. It pings only on
   conflict/failure.

### `idea <text>`

Lightweight capture: one short `inbox/` dump, `kind: idea`, usually no
distill hints (a spark, not a changeset). Same instant capture commit.
The distiller files it as a journal idea entry and normally leaves topics
untouched.

### `resume <topic|entry>`

1. Locate the wiki + `pull` (above).
2. **Drain `inbox/` first and wait:** if any dumps are pending, run the
   distiller synchronously so topics are current — resuming off stale
   topics is wrong. Skip if `inbox/` is empty.
3. Read the topic's **canonical summary**; drill into its sections and
   linked journal entries only where that's insufficient (narrow
   retrieval — keep the fresh window clean).
4. Produce a rehydration brief: goal, current state, open threads, paths
   already ruled out, next concrete step. **Read-only** otherwise.

### `groom`

1. Locate the wiki + `pull`; **drain `inbox/`** via the distiller, and
   resolve any corrections it **flagged** (anchor not found).
2. Run the staleness pass per WIKI.md *Groom semantics* (branch liveness,
   distilled-vs-abandoned journal entries, topic retirement only on
   feature done/abandoned or long inactivity, contradiction/stale-claim
   flags). **Always show the plan and get confirmation before moving or
   editing anything.**

## The distiller (background Sonnet subagent)

A **fresh, small-context** agent — it has none of the session and must
not try to reconstruct it. It works only from the `inbox/` dumps + the
live wiki. Spawned fire-and-forget by `save`, and drain-and-wait by
`resume`/`groom`. Its job:

1. **Drain `$WIKI/inbox/*.md`, oldest first** (batch them in one pass). If
   the inbox is already empty (another distiller drained it), exit.
2. For each dump:
   - Write/refine the polished `$WIKI/journal/` entry from the brain-dump.
   - Apply the **distill hints** to `$WIKI/topics/` with **targeted
     `Edit`s, never whole-page rewrites** (WIKI.md *Maintenance
     principles*): add `new` facts to their sections, append
     `path-not-taken`, refresh the ≤5-line canonical summary on
     `summary-delta`, create a topic on `new-topic`.
   - **Corrections:** locate the anchor (section header + quoted snippet)
     in the **live** file. Match → apply the replacement. No match (stale
     memory / file moved on) → **flag it** (leave a `> [groom] flagged:
     …` note in the topic) and do **not** edit. Never guess.
   - Append the `$WIKI/log.md` row; update `$WIKI/index.md` only if a
     topic was created/retired or its summary changed.
   - Delete the drained `inbox/` file.
3. **Secret-scan the diff** — it is the fresh reviewer: secrets, tokens,
   private/internal URLs, hostnames beyond short labels, PII. (The repo's
   git hooks also scan at commit/push, but this is the judgment layer.) If
   anything is questionable, **stop, leave the inbox file in place, and
   report back** instead of committing.
4. If clean, commit `git -C "$WIKI" add -A && commit -m "distill: <topics> — <short>"`, then **push if an upstream exists** (the guard from *Locate*). On push reject, `pull --rebase` (resolve fully) and push again. No upstream → the commit stays local, nothing to push.

## Notes

- **A timeout is not an answer — blocking questions stay blocking.** This
  skill deliberately splits questions into *blocking* ("stop and ask" — the
  altitude check, the `groom` confirmation) and *mention-and-go*. If a
  blocking `AskUserQuestion` times out (the harness returns "No response
  after Ns…" and suggests proceeding on best judgment), do **not** take the
  suggestion: silence means "not answered yet," not "decide for me."
  **Stop and wait** — take no wiki-mutating action, hold, and let the user
  answer when they return (re-ask if useful). Auto-continuing on timeout
  would collapse a blocking question into mention-and-go and undo the very
  distinction this skill drew. (Only the harness controls the timeout
  length; what happens *after* it fires is this skill's call, and the call
  is: wait.)
- **Never block the user on distillation.** The capture commit already
  saved their session; the distiller is gravy layered on top.
- Two commits per save: `capture:` (instant, durable) then `distill:`
  (async). The capture commit is the safety net — if the distiller dies,
  the dump survives in `inbox/` and the next invocation re-drains it.
- **Config is per-host.** `~/.config/miniwiki/config.json` records where
  the wiki lives on *this* machine; each host points at its own checkout.
  It survives plugin updates (it lives outside the plugin dir).
