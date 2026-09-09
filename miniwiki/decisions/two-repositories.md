# Two repositories, and which one is canonical

## Decision

**`dgokeeffe/agentic-energy-on-databricks-public` is canonical.** The private
`dgokeeffe/agentic-energy-on-databricks` is historical: keep it for the issue
history and the original discussion, but do not develop in it.

## What happened

Two repositories exist and they **share no Git history**.

| | private `agentic-energy-on-databricks` | public `…-public` |
|---|---|---|
| Created | 2026-08-10 | 2026-09-07 |
| Last push | 2026-09-05 | 2026-09-09 |
| Root commit | `34980e0` "bd init: initialize beads issue tracking" | `2f15794` "Initial clean repository snapshot" |
| Issues | 21, including 6 `workshop-ready` | 0 before migration |
| Track C app, fuel value capture | absent | present |
| Self-contained tracks | absent | present |
| Facility-dimension defect and fix | absent | present |

The public repository was started as a clean snapshot rather than a fork, so no
commit is common to both. `gh api …/commits/<sha>` returns 422 for every private
head SHA queried against the public repository. This is not drift that a merge can
reconcile.

The consequence nobody noticed until asked: **GitHub issues are repository
metadata, not Git objects.** They do not travel with a push, a clone, or a
snapshot. The code moved to the public repository; the exercises did not.

## Migration, 2026-09-09

Five of the six `workshop-ready` issues were recreated in the public repository
with their title, body, and labels verbatim, each carrying a note naming its
original private number.

| Private | Public | Title |
|---|---|---|
| #5 | **#2** | Fail loudly when facility enrichment context is missing |
| #6 | **#3** | Add a governed regional dispatch-price spike detector |
| #7 | **#4** | Expose and explain corrected NEMWEB intervals |
| #8 | **#5** | Separate source publication delay from pipeline freshness |
| #9 | **#6** | Strengthen Genie supported-answer and refusal benchmarks |
| #12 | **#7** | *Rewritten* — see below |

All 13 workshop labels were recreated first, so the label vocabulary matches.

**Numbers changed and are not portable.** Public #1 is the redesign pull request,
so the issue numbering is offset from the private repository by an amount that is
not constant. Any number quoted in a commit message, a miniwiki page, or a README
may refer to the private repository. Resolve an exercise by title and label.

### Private #12 was stale and was rewritten, not copied

It asked to *build* the NEM regional operations AppKit screen. That screen exists
and has since been redesigned twice — first as a price-trust screen, then reframed
around fuel value capture. Its acceptance criteria were met before the public
repository existed, so copying it verbatim would have handed a participant finished
work.

Public #7 instead targets what is genuinely unfinished, found by grep rather than
by reading the decision pages:

- `registration_effective_at` is written by `silver_facilities.py` and **read by no
  Gold surface**, so a stale registration dimension cannot be detected downstream.
- `registration_enrichment_quality()` is called from **its own test and nowhere
  else** — no pipeline or evidence code enforces it.

Both matter to the value-capture figures, because `gold_nem_scada_generation_5min`
groups by `region_id` and `fuel_type` from that dimension. It is the same shape as
public #2 (private #5), one layer out.

Public #7 deliberately does **not** carry `workshop-ready`. The issue bodies
themselves require a facilitator to rehearse an exercise before that label is
applied, and this one has never been run.

### Not migrated

Private #13, #14, #18, #19, #20 (investigation journal, governed Genie, integrated
journey, Lakebase synced tables, CDF streaming) are `difficulty: advanced` and were
never `workshop-ready`. Private #3, #4, #11, #21, #22 are closed setup tickets. The
`nemweb_app/README.md` entry-point table now names those areas without quoting an
issue number.

## Stale pointers repaired at the same time

Both would have sent a participant or agent down a dead end on a fresh clone:

- `.agents/skills/issue-navigator/SKILL.md` instructed an agent to *"List open
  GitHub issues carrying `workshop-ready`"*, which returned nothing. It now names
  the exact `gh` command, says to stop and tell the facilitator on an empty list
  rather than improvise a ticket, states that the route is optional, and warns that
  numbers are not portable between the repositories.
- `nemweb_app/README.md` cited #12, #13, #14 and #18 as entry points. None resolved.

## The participant path never depended on issues

Worth stating, because the missing issues looked more serious than they were.
`QUICKSTART.md` contains **no** reference to an issue, a ticket, or
`workshop-ready`. `AGENTS.md` already says a track is completed from its own
`Instructions.md` and an issue is only needed when work is contributed back. That
was the 2026-09-07 track restructure, recorded in
[`track-structure.md`](track-structure.md).

So the exercises are a contribution route, not the way an attendee starts. The
migration restores an optional path; it does not unblock the workshop.

## Open

- Whether the five migrated exercises are still the right exercises. They were
  written before the app redesign and the pipeline fix. #2 was verified as still
  genuinely open; #3, #4, #5, #6 were **not** re-read against the current code in
  detail, only spot-checked.
- Whether to archive the private repository, or leave it readable for its issue
  discussion. Archiving would preserve the history read-only and remove the
  ambiguity about where to work.
- The private repository has two unmerged branches,
  `chore/remove-beads-for-omni-sandbox` and
  `feat/participant-foundation-app-ml-ltap`. Nobody has checked whether either
  contains work absent from the public repository.
