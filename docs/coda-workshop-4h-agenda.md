# Agentic engineering workshop: four-hour run of show

Facilitator source of truth for timing. The deck
(`docs/coda-workshop-deck.md`), the talk track, and every participant handout
must agree with this file. When they disagree, this file wins and the others get
corrected.

Vehicle: this repository's NEMWEB market-data foundation. Do not reintroduce the
retired promotional-pricing vehicle.

## Shape

Four hours, 240 minutes. Fourteen minutes of presenting at the front, six to
introduce the challenge, a 153-minute hands-on middle in two tracks, and a
10-minute close. Sections one to three are hands-on. Only the opening, the
environment demo, the challenge brief, section two's front block, and section
three's four framing slides are delivered as presentation.

| Time | Minutes | Block | Mode |
|---|---:|---|---|
| 00:00–00:08 | 8 | Opening: promise, the spectrum, the harness, the lifecycle, what compressed | Present |
| 00:08–00:14 | 6 | The operating environment, with a live demo | Present and demo |
| 00:14–00:20 | 6 | The challenge, the two tracks, the limits | Present |
| 00:20–01:40 | 80 | Section one: research, design, implement, deploy | Hands-on |
| 01:40–01:55 | 15 | Section one checkpoint and cross-track share | Facilitated |
| 01:55–02:05 | 10 | Break | Break |
| 02:05–02:13 | 8 | Section two front block: the contract failure and the harness repairs | Present |
| 02:13–02:20 | 7 | Demo: review, evals, and Genie One | Demo |
| 02:20–03:05 | 45 | Section two: review and evals, data product and Genie One | Hands-on |
| 03:05–03:15 | 10 | Cross-track evidence exchange | Facilitated |
| 03:15–03:22 | 7 | Section three framing: cost, traces, gates, the instruction file | Present |
| 03:22–03:50 | 28 | Section three: harness improvement and self-evaluation | Hands-on |
| 03:50–04:00 | 10 | Close: share-out, round-up, and what to turn on | Facilitated |

## Two tracks

Both tracks run for the whole day on the same governed data foundation. A
participant chooses a track once, at 00:20, and stays in it.

| | Track A: data product | Track B: engineering |
|---|---|---|
| Who | Analysts, operators, market and commercial roles | Software and data engineers |
| Primary surface | Omnigent for NEMWEB research and shared Beads requirements in section one; Genie One, AI/BI, and a governed context connection in section two | Omnigent, coding agent, Beads work graph, repository, Databricks Asset Bundle, Lakebase |
| Section one | Research NEMWEB in Omnigent, turn the evidence into Beads requirements with the paired engineering group, and approve a ready frontier | Start in Omnigent, shape the shared work graph, research the source contract, get a plan approved, implement one change, deploy and reconcile |
| Section two | Build the governed data experience: metric view, Genie Agent, Genie One, and one approved MCP with a recorded access boundary | Build the review process: acceptance criteria as evals, automated draft pull requests, reviewer that differs |
| Section three | Improve the harness: instructions, skills, saved questions, scheduled checks, self-evaluation | Improve the harness: scorers, gates, budgets, declared metric with keep-or-revert |

Pair each Track A group with a Track B group at 00:20 and record one joint claim
area and one joint decision owner. The 01:40 and 03:05 exchanges use those
pairs.

## Section one, 00:20 to 01:40

Objective: one approved, evidence-backed requirement from the product pair and one
bounded engineering change from the engineering pair, with evidence someone else
can inspect.

| Time | Track A: data product | Track B: engineering |
|---|---|---|
| 00:20–00:36 | Open Omnigent; name the decision, owner, question, and evidence threshold with the paired engineering group | Open Omnigent; `bd prime`, pour the team molecule, shape 5–8 beads, human approves the frontier |
| 00:36–00:52 | Research NEMWEB in Omnigent: baseline, grain, freshness, and uncertainty | Research the source contract: event timestamp, timezone, natural key, watermark, quality rules |
| 00:52–01:08 | Turn the research into Beads acceptance criteria; iterate them with the paired engineering group | Write the plan: files that may change, contracts held fixed, tests as proof, stop conditions; get it approved before code |
| 01:08–01:24 | Approve one ready requirement, with its evidence and boundary | Implement one motivated change agentically; deterministic tests; draft pull request |
| 01:24–01:40 | Save the NEMWEB research, verified SQL, and Gold window for section two; hand over the approved Beads requirement | Deploy: dispatcher reads a Lakebase metadata snapshot, then reconcile the run manifest |

Track A's 00:52 block is deliberate setup for the engineering change. A product
pair that skips it gives engineering an unbounded requirement rather than a ready
Beads frontier.

Section one runs 80 minutes rather than 75 because three slides moved out of the
opening and into section two, where the review story belongs. The extra time sits
in research and implementation, which is where pairs ran out of it in rehearsal.
Later block boundaries do not move.

Section one is not complete without a named human decision: approve the
requirement, accept, send back, reject, or stop.

## Section one checkpoint, 01:40 to 01:55

Each pair shows, in two minutes:

- Track A: the question, the NEMWEB research record, the approved Beads requirement, the saved Gold window, and the decision.
- Track B: the approved plan, the changed files, the test result, the reconciled manifest or the reason it did not reconcile, and the decision.

Record blockers here. A pair that cannot show a Gold window or a ready frontier
moves to the prepared fallback before the break, not during section two.

## Section two, 02:05 to 03:05

Both tracks in the room for the first fifteen minutes, then split by track.

| Time | Block |
| 02:05–02:13 | Six slides: the routine-ticket pipeline, the contract that broke, the four harness repairs, the enforced control points, the run record, and why every program needs its own harness |
| 02:13–02:20 | Facilitator demo: acceptance criteria as evals, a plan-compliance gate returning a change request, a reviewer that differs, a saved Genie One question and one it declines |
| 02:20–03:05 | Hands-on, three blocks of fifteen minutes |

Theory in section two is capped at those eight minutes. The story is the vehicle
and the four repairs are the payload. If the clock slips, cut the run-record slide,
then the control-points table, and keep the repairs.

The Lakebase branch, migrate, verify, discard beat is now optional inside the
demo rather than a block of its own. Keep it if the clock allows, because it is
where the four conditions of a repeatable loop get named out loud: verifiable,
reversible, short horizon, bounded scope. Section three builds on those, so if the
beat is cut, name the four conditions anyway.

The pipeline story is a production-shaped example: routine tickets, one required
end-to-end test that was absent from the first pull request, then four harness
repairs. Tell it in the room without naming a team, repository, or customer.
Present it as the good case that needed a harness repair rather than as a
cautionary tale.

| Time | Track A: data product | Track B: review and evals |
| 02:20–02:35 | Create a metric view over the Gold window; name the measures and dimensions it exposes | Turn the acceptance criteria into evals, each labelled required, recommended, or optional |
| 02:35–02:50 | Create a Genie Agent grounded in the metric view; record its scope and instructions | Run the agent to a draft pull request; let the gate check it against the approved plan |
| 02:50–03:05 | Use the agent in Genie One; add an approved MCP and record its identity and access boundary | Review with a reviewer that differs; record the decision and the evidence read |

Return per track: one artefact, the evidence behind it, one refusal, and one named
decision. Track A owes a metric view, a scoped Genie Agent, an approved MCP with a
recorded access boundary, and a question the product will not answer. Track B owes
a verdict from the gate before the human decision, because a gate nobody has
watched reject anything is not yet a control.

The deck carries a side-by-side reference slide, "Build it in this order", which
stays on screen through the block. Both columns in working order:

| Track A: a governed data experience | Track B: a review that runs without you |
| Create a metric view over the Gold window, with named measures and dimensions | Write the criteria first, and label each one by force |
| Create a Genie Agent grounded in the metric view and its declared scope | Let the agent open the draft pull request, and do not fix it by hand |
| Use the agent in Genie One, then add one approved MCP | Run the gate before reading the diff |
| Record the MCP identity and access boundary, then save one question it refuses | Give the review to somebody, or something, that did not write it |

The last row in each column is the one pairs skip. Track A saves a question nobody
scheduled, so it dies with the session. Track B reviews its own change, which is
the nodding loop from the section two story.

## Cross-track evidence exchange, 03:05 to 03:15

Two minutes per pair, in the pairs formed at 00:20. Each pair answers one closing
question: what can your harness now stop that it could not stop an hour ago?
Record the answers, because they are the input to section three. A pair with
nothing the harness prevents starts section three with that as its first job.

## Section three, 03:15 to 03:50

Four framing slides, seven minutes, then the work.

| Time | Slide | Job |
| 03:15–03:17 | Context is the budget you spend | Static context against fetched context, the cached prefix, and cost per accepted change as the declared metric. Ninety seconds. |
| 03:17–03:18 | Read the trace before you argue about the model | The four questions a trace settles, and where cost observability lives. |
| 03:18–03:20 | Build gates that can say no | Six layers in the order they were built, and the rule that the scheduled loop comes last. |
| 03:20–03:22 | Your instruction file is an untested claim | The harness itself under test, and why one sample per probe lies. |

Provider prices and cache lifetimes belong in the presenter notes with their
source, never on a slide. The same goes for the eval scores quoted in the notes.

The last two framing slides use a production-shaped harness example. The detailed
provenance is facilitator material. Public slides and participant materials must
contain only claims that can be checked in this repository or in prepared workshop
artifacts. Do not add private repository paths, team names, or customer details to
the deck.

Track A turns its metric view into something people can use, then tests the Genie
Agent behind it. Track B converts one failure it actually hit today into a durable
control, declares the metric and revert point, and reruns to compare.

| Time | Track A: data product | Track B: review and evals |
| 03:22–03:36 | Build an AI/BI dashboard or Databricks App from the metric view; show the owner, source, and freshness | Pick one failure; write the guard, scorer, or gate that prevents it; freeze one golden case from a run already trusted |
| 03:36–03:50 | Create Genie Agent benchmark cases from real questions; try a Genie One skill and record the result, refusal, or fallback | Rerun the same ticket; compare the trace, the gate's verdict, and the cost per accepted change; keep it or revert |

Return per track: Track A returns the dashboard or app, benchmark cases, the skill
attempt, and the decision; Track B returns the failure, change, metric, before and
after, and keep-or-revert decision. Keep the same question when comparing a
benchmark. Two shapes of cheating to name early: loosening a check until it
passes, and rerunning a different task.

The deck carries the matching side-by-side reference slide, "Improve it in this
order":

| Track A: a data experience people can use | Track B: a gate that earns its place |
| Build an AI/BI dashboard or Databricks App from the metric view | Name a failure from today, and the trace that shows it |
| Put the owner, source, and freshness on the surface | Write the guard, scorer, or gate that catches it |
| Create Genie Agent benchmark cases from real questions | Freeze one golden case from a run already trusted |
| Try a Genie One skill, then record the result, refusal, or fallback | Rerun the same ticket, and compare trace, verdict, and cost |

Spend the facilitation on Track A's benchmark cases and Track B's first row. A
failure or question somebody invented is worth nothing here, so send them to the
blockers recorded at 03:05.

## Appendix

One slide, held at the back: a three-by-three matrix separating claimed from shown
from proven, across the result, the boundary, and the decision. It replaces the
points-based scorecard, which was cut because there is not enough time to run it
properly and a half-run scoring scheme is worse than none. No points, no
penalties, no contention. Use it if a group asks how it is being judged, and as
the closing frame at 03:50.

## Close, 03:50 to 04:00

Three beats in ten minutes: the share-out, the round-up, the call to action.

| Time | Beat | On screen |
| 03:50–03:56 | Share-out: four preselected pairs at 90 seconds each | The section three work order, because pairs report against its return list |
| 03:56–03:57 | Round-up: the five things worth taking back | Keep these five when you get back |
| 03:57–04:00 | The call to action: activate one path in a workflow they own | Turn this on in a workflow you already own |

There is no separate evidence card and no separate section three checkpoint. Both
were one slide that asked pairs to transcribe what the work orders already told
them to produce, so pairs now report against the section three return list: the
failure, the change, the metric, the before and after, and the decision to keep or
revert.

Pick the four pairs while they work, and pick for contrast rather than polish: one
that reverted, one whose gate caught something, one Track A refusal, one that never
got its deployment working. Ninety seconds means you interrupt, so say so before
the first pair starts.

The round-up is the promise from the second slide of the day, delivered, so point
back at it. Read the five lines and do not elaborate on any of them.

The call to action is activation, and it is the outcome the four hours exist to
produce. Two paths, matching the two tracks:

| Audience | Turn on | What they have in week one |
| Engineers who delegate code | Omnigent, with Unity AI Gateway in front of it | A governed session with policy and sandbox, and every model call routed, attributed, budgeted, and capped |
| Analysts and operators who answer questions with data | Genie One, on a table they already trust | A governed answer carrying its source and freshness, saved so a colleague can rerun it |

The ask is a workflow they already own, not a sandbox, running inside a fortnight.
Four things get named before anybody leaves: the workflow, the owner, the evidence
they will demand, and what stops it. Ask for the date, not the intention.

Check what is actually enabled in the customer's own account before promising a
capability. What Unity AI Gateway can do, and whether it is still in preview, varies
by account, and the Omnigent status hedge from the harness slide still applies. Where something
is not enabled, the ask becomes a named request to enable it, with an owner and a
date, rather than nothing.

`docs/pilot-canvas.md` is the handout, and the longer five-line version of the ask
is on it. The day ends on the line for the third time: set the boundary, check the
evidence, make the decision.

## Preflight this agenda depends on

From `docs/coda-workshop-4h-agl-open-decisions.md`. None of these may be
presented as proven without current evidence from the target workspace.

| Item | Needed by | Fallback if it fails |
|---|---|---|
| Omnigent session, approved NEMWEB research material, and a shared Beads frontier for every pair | 00:20, both tracks | Facilitator-provided research pack and prepared Beads frontier |
| Historical Gold analysis window with regional and time variation | 00:36, Track A | Facilitator-provided cited pack |
| Metric-view creation over the Gold projection, with named measures and dimensions | 02:20, Track A | Facilitator-provided metric-view definition and result |
| Genie Agent can use the metric view with its declared scope and instructions | 02:35, Track A | Prepared agent transcript, labelled as prepared |
| Genie One and one approved MCP expose the expected identity and access boundary | 02:50, Track A | Prepared transcript and recorded boundary, labelled as prepared |
| Fresh Beads molecule per pod, clean `bd dep cycles`, steward can push | 00:20, both tracks | Prepared clean molecule; record the blockage as a returned bead |
| Unity Catalog catalog, schema, and Volume; serverless Jobs permissions; Lakebase metadata snapshot readable by the dispatcher | 01:24, Track B | Run the deterministic local profile and present the deployment as required configuration |
| A plan-compliance gate that visibly rejects a required item with no evidence | 02:13 demo | Prepared transcript of the rejection, labelled as prepared |
| Lakebase project with branch-and-discard rights, and a migration that runs on a branch | 02:13 demo, optional beat | Cut the beat; it is the first thing to drop |
| AI Gateway usage and budget view | 00:08 demo | Prepared screenshot, labelled as prepared |
| AI/BI dashboard or Databricks App creation from the metric view | 03:22, Track A | Prepared dashboard or app, labelled as prepared |
| Genie Agent benchmark workflow and Genie One skill creation | 03:36, Track A | Prepared benchmark transcript and skill attempt, labelled as prepared |

## Opening structure, 00:00 to 00:08

Built on Patrick Winston's rules (`notes/how-to-speak-winston-distillation.md`):
the empowerment promise comes first, the central term gets a fence, the agenda is
verbal punctuation, and the claim cycles three times.

| Slide | Job |
|---|---|
| Agentic engineering on Databricks | Let the room settle. No joke, no housekeeping. |
| What you take away from today | The promise, stated as four outcomes: the vibe-coding-to-agentic-engineering distinction, hands on coding agents and the Databricks software engineering stack, the whole lifecycle inside four hours, and Genie One. First cycle of the line. |
| How the four hours run | The landmark anyone can rejoin later. |
| What you will build today | Prelude to the challenge, so the theory has somewhere to land. |
| From vibe coding to agentic engineering | The spectrum, and the fence around the term, spoken. |
| The agent is a model inside a harness | Name the thing the room works inside, and the three harnesses it will meet: Pi, OpenCode, Omnigent. |
| Improving the harness is the engineering work | What tuning a harness means per track, and the benchmark that sizes the effect. Points at section three. |
| The lifecycle figure | Fifteen seconds of silence, then one sentence. Two pointers only. |
| What compressed, and what did not | Implementation got faster; judgement did not. |

Nine slides in eight minutes. The title and the figure take twenty seconds each,
and that leaves about sixty seconds for each of the other seven.

The review story, the enforced control points, and the run record used to sit here
and now open section two, where the room has produced work worth reviewing. Two
slides were retired outright: where delegated work runs, whose content survives in
the harness diagram and the demo notes, and the points-based scorecard, which is
now an appendix matrix.

The environment block that follows is two slides in six minutes: the demo itself
and what may be claimed as proven. The demo slide carries four words; its four
beats live in the presenter notes, and the live portion is five minutes at most.
Lakebase branching is held back for the section two demo.

The challenge block is three slides in six minutes: the challenge, the evidence
bar, and the limits.

## Timing discipline

- The opening ends at 00:08 and the demo at 00:14. If the opening runs long, cut the middle rows of the lifecycle table, then the harness improvement slide.
- The challenge brief is six minutes for three slides. The limits are a handout as well as a slide, so read the headline and move.
- Hands-on starts at 00:20. Every pair opens Omnigent before splitting into its work. Every minute reclaimed at the front belongs to section one.
- Section two's front block ends at 02:20 whatever happens, capped at eight minutes of slides and seven of demo.
- Section three's framing ends at 03:22. If it runs long, cut the gates table and let the trace slide carry the argument, because the instruction-file slide is the one that produces the work.
- The close needs its full ten minutes. If the day is behind at 03:50, drop the fourth presenting pair rather than the pilot decision.
- Do not read the lifecycle figure aloud. It is exposure, not instruction.
- Never debug a live demo for more than two minutes. Switch to the fallback and say so.
- Section one ends at 01:40 whatever state the work is in. The checkpoint is the moment that counts, not completion.
- The break is 10 minutes and it starts on time.
