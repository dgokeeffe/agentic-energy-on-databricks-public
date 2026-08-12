---
marp: true
theme: databricks-agentic
paginate: true
size: 16:9
footer: '<img class="mark-light" src="assets/brand/databricks-logo-full-color.svg" alt="Databricks" /><img class="mark-dark" src="assets/brand/databricks-logo-white.svg" alt="Databricks" /><span>Agentic engineering workshop</span>'
---
<!-- _class: title -->

<div class="lockup"><img src="assets/brand/databricks-logo-white.svg" alt="Databricks" /></div>

# Agentic engineering on Databricks
## How to govern the work you hand to an agent

Four hours of hands-on work in two tracks, on one governed data foundation

<!--
Presenter notes:
Say the title out loud rather than reading the slide, and hold it for about
twenty seconds while the room settles. No joke, no apology, no housekeeping.
Then go straight to the promise on the next slide.
-->
---
<!-- _class: action -->

# What you take away from today

- You find the line where vibe coding ends and agentic engineering starts.
- You start in Omnigent, then work with a coding agent and the Databricks engineering stack.
- You run the whole agentic lifecycle once, inside four hours.
- You build a metric view and Genie Agent, then test them through Genie One and an approved MCP.

<div class="callout">Set the boundary. Check the evidence. Make the decision.</div>

<!--
Presenter notes:
This is the promise, and it is the reason to stay in the room. Say it as four
outcomes on real market data, with evidence you can show a colleague on Monday.
Then say that both tracks reach all four: Track B meets Genie One at the
cross-track exchange, and Track A works the same lifecycle without writing
production code. Writing a boundary and judging a run record are part of those
four rather than extras beside them. Read the line at the bottom once here and
tell the room it comes back twice more.
-->
---
<!-- _class: dense-agenda -->

# How the four hours run

Hands-on work starts at 00:20 and takes 153 of the 240 minutes.

| Time | Block | Mode |
|---|---|---|
| 00:00–00:08 | opening: the spectrum, the harness, the lifecycle, what compressed | present |
| 00:08–00:14 | the operating environment, with a live demo | demo |
| 00:14–00:20 | the challenge, the two tracks, the limits | present |
| 00:20–01:40 | section one: research, design, implement, deploy | hands-on |
| 01:40–01:55 | section one checkpoint and cross-track share | facilitated |
| 01:55–02:05 | break | |
| 02:05–02:20 | section two opens: a contract failure, then a live review demo | present and demo |
| 02:20–03:05 | section two: review and evals, data product and Genie One | hands-on |
| 03:05–03:15 | cross-track evidence exchange | facilitated |
| 03:15–03:22 | section three framing: cost, traces, gates, the instruction file | present |
| 03:22–03:50 | section three: harness improvement and self-evaluation | hands-on |
| 03:50–04:00 | close: share-out, round-up, and what to turn on | facilitated |

<!--
Presenter notes:
Spend thirty seconds here. The table is a landmark, so anyone who loses the thread
later can rejoin at it. Say three numbers out loud: hands-on
starts at 00:20, there is one break, and section one ends at 01:40 in whatever
state the work is in. This table and docs/coda-workshop-4h-agenda.md must always
agree, so if you change one, change the other.
-->
---
<!-- _class: stack -->

# What you will build today

Both tracks work the same governed foundation of public Australian
electricity-market data, published on NEMWEB. You use it as a working system, so
you do not need electricity-market expertise.

<div class="cards">
  <div class="card">
    <span class="label">Track A</span>
    <h3>A decision product</h3>
    <p>A metric view, a Genie Agent, Genie One, and an approved MCP around a question colleagues can reuse.</p>
  </div>
  <div class="card accent">
    <span class="label">Track B</span>
    <h3>A governed delivery loop</h3>
    <p>An approved work graph, a reviewed change, a deployment whose run you can reconcile.</p>
  </div>
</div>

<!--
Presenter notes:
Say what the vehicle is now, so the theory that follows has somewhere to land.
This is public market data, and it carries the rules and the failure modes the
market itself produces. By the close, both tracks defend their work against the
same questions. The full brief comes at 00:20, so resist taking questions about
the challenge here.
-->
---
<!-- _class: opening-map -->

# From vibe coding to agentic engineering
## How much you delegate is a choice you make one task at a time.

<div class="engineering-envelope">
  <div class="envelope-label"><strong>Agentic engineering</strong><span>design the goal, limits, checks, evidence, and human decision around delegated work</span></div>
  <div class="opening-spectrum">
    <div class="opening-stop"><strong>Software engineering</strong><span>you define every path</span></div>
    <div class="opening-stop"><strong>AI-assisted coding</strong><span>the system suggests a step</span></div>
    <div class="opening-stop"><strong>Vibe coding</strong><span>you iterate from prose</span></div>
    <div class="opening-stop accent"><strong>Agentic coding</strong><span>the system plans and acts across steps</span></div>
  </div>
  <div class="opening-axis"><span>people choose the next action</span><span>more actions are delegated</span></div>
</div>

<div class="callout">The stakes decide the position, and most teams work at several of these points in the same week.</div>

<!--
Presenter notes:
Trace the spectrum once, left to right, then step out to the frame around it.
Say that vibe coding suits a prototype and carries risk in a shared system.
Then draw the fence: agentic engineering is the design work around delegated
work, which is the goal, the limits, the checks, the evidence, and the human
decision. A more impressive prompt does not get you there, and neither does more
autonomy on its own. These are not rigid categories, so skip the maturity-model
reading, and do not ask anyone to place themselves out loud yet.
-->
---
<!-- _class: concept -->

# The agent is a model inside a harness

<p class="arch-lead">A harness is everything around the model that lets it finish work.</p>

<div class="harness-arch">
  <div class="arch-plane"><strong>Control plane</strong><span>Omnigent sits above any harness for policy, sandboxing, cost, and sharing</span></div>
  <div class="arch-harness">
    <div class="arch-label"><strong>Harness</strong><span>Pi, OpenCode, or another agent you run from a terminal</span></div>
    <div class="arch-parts">
      <div class="node core"><strong>Model</strong><span>one input into the run, and the easiest part to swap</span></div>
      <div class="node"><strong>Instructions</strong><span>rule files and skills</span></div>
      <div class="node"><strong>Tools</strong><span>MCP servers and scripts</span></div>
      <div class="node"><strong>Sandbox</strong><span>where its code runs</span></div>
      <div class="node"><strong>Orchestration</strong><span>sub-agents and routing</span></div>
      <div class="node"><strong>Hooks</strong><span>checks that fire on an edit</span></div>
      <div class="node"><strong>Observability</strong><span>traces, cost, and evals</span></div>
    </div>
  </div>
  <div class="arch-rail"><strong>AI gateway</strong><span>model calls leave through it: routing, per-identity attribution, budget, and a hard cap</span></div>
</div>

<p class="arch-note">The same model in two harnesses behaves differently, so the harness is the part you own.</p>

<div class="source">Harness anatomy after Osmani, Saboo and Kartakis, The New SDLC With Vibe Coding, May 2026.</div>

<!--
Presenter notes:
Name this before any tool appears on screen, because it is what the room works
inside for the next three hours. Walk the diagram from the middle out. Point at
the dark tile and say that an agent is a model plus a harness, and that a model
becomes an agent once something around it gives it state, tool execution,
feedback loops, and constraints it cannot cross. Then point at the six tiles and
say that every one of them is yours to write. Then the band above, which is where
a control plane sits when more than one harness is in use, and the rail below,
which is where the model calls actually leave. The gateway is worth one sentence
here and no more: it is the one place model traffic can be routed, attributed to
an identity, budgeted, and capped, which is why cost is a governed property
rather than a surprise on an invoice. It comes back twice, in the run row of the
environment slide and as the number you move on the context slide. Give one
concrete difference between harnesses. OpenCode loads every configured MCP server's tool
definitions at session start, and its own documentation tells you to keep that
list short, while other harnesses index the tools and load a schema on demand.
Same model, different day's work. On Omnigent, say what it does and stop:
public sources describe the open-source project as alpha, and Omnigent on
Databricks as beta behind a workspace preview, so present it as a direction
rather than as something you can buy today. The harness anatomy here follows
Osmani, Saboo and Kartakis, The New SDLC With Vibe Coding, May 2026.
-->
---
<!-- _class: action -->

# Improving the harness is the engineering work

Tuning a harness means changing one thing you own, then reading what it did to
the run.

- Track A tunes instructions, skills, saved questions, and scheduled checks.
- Track B tunes scorers, gates, and budgets.
- Both declare the metric the change should move, and the revert point, before running it.

<div class="callout">One team moved a coding agent from outside the Top 30 to the Top 5 on Terminal Bench 2.0 by changing only the harness.</div>

<!--
Presenter notes:
Say where this work lands. Section three at 03:15 is this slide as an exercise,
and both tracks turn one repeated failure into a durable change there. Read the benchmark line
and then add the second one: a separate study raised a coding agent's score on
the same benchmark by 13.7 points by changing only the system prompt, the tools,
and the middleware around a fixed model. Both come from Osmani, Saboo and
Kartakis, May 2026. The conclusion to say out loud is that most agent failures
trace back to the harness, to a missing tool, a vague rule, an absent guardrail,
or a context window full of noise, which is why reaching for a different model is
usually the wrong first move. The green return line on the next figure is this
same loop.
-->
---
<!-- _class: visual -->

<div class="lifecycle">
  <div class="lc-titleblock">
    <div>
      <div class="lc-title">The agentic SDLC on Databricks</div>
      <div class="lc-subtitle">the agent drafts, a human approves, every failure becomes harness</div>
    </div>
    <span class="lc-legend"><span class="lc-key-agent">agent drafts</span><span class="lc-key-human">your decision</span><span class="lc-key-evidence">evidence and return</span></span>
  </div>
  <div class="lc-band">
    <span class="lc-band-label">Harness</span>
    <div class="lc-band-items">
      <span class="lc-chip">instructions and rule files</span>
      <span class="lc-chip">tools</span>
      <span class="lc-chip">sandbox</span>
      <span class="lc-chip">policy</span>
    </div>
  </div>
  <div class="lc-row">
    <div class="lc-step lc-drafted"><strong>Brief</strong><span>criteria, scope, evidence</span></div>
    <div class="lc-step lc-drafted"><strong>Plan</strong><span>files, contracts, stops</span><em>you approve</em></div>
    <div class="lc-step lc-drafted"><strong>Dispatch</strong><span>bounded run, draft pull request</span></div>
    <div class="lc-step lc-drafted"><strong>Review</strong><span>the record, not the recap</span><em>you decide</em></div>
    <div class="lc-step lc-drafted"><strong>Prove</strong><span>tests, checks, evals</span></div>
    <div class="lc-step lc-evidence"><strong>Observe</strong><span>traces, cost, behaviour</span></div>
    <div class="lc-step lc-evidence"><strong>Improve</strong><span>hooks, skills, gates, evals</span></div>
  </div>
  <div class="lc-return">Every failure returns as a test, a hook, a policy, or an eval case, so the next run cannot repeat it.</div>
  <div class="lc-band lc-record">
    <span class="lc-band-label">Record</span>
    <div class="lc-band-items">
      <span class="lc-chip">traces</span>
      <span class="lc-chip">manifests</span>
      <span class="lc-chip">cost</span>
      <span class="lc-chip">the recorded decision</span>
    </div>
  </div>
  <div class="lc-legacy">the old phases all survive, rephrased: requirements, design, implementation, testing, review, release, maintenance</div>
</div>

<!--
Presenter notes:
Say nothing for fifteen seconds while the room reads, then give it one sentence:
the phases all survived, and so did the human gates. Point at two things only.
The five steps in lava, because the agent drafts the brief, the plan, the code,
the tests, and the evidence, and prove is in there because where you can, you
give the agent a way to validate its own delivery. Then the two navy chips,
because that is where your judgment now lives: you approve the plan before the
run, and you decide on the evidence after it. Everything else can wait for a
question. If one comes, the return line is the answer to most of them: every
failure worth codifying comes back as a test, a hook, a policy, or an eval case,
and that covers any failure in the run rather than only an incident in
production. The last line is worth reading out if the room is senior: the old
phases all survive, so nobody has to throw away the lifecycle they run today.
-->
---
<!-- _class: compact -->

# What compressed, and what did not

Implementation got faster. Judgement did not. The table shows where the split falls.

| Phase | Compressed | Unchanged |
|---|---|---|
| Requirements | drafting and prototyping | agreeing what is wanted |
| Architecture | exploring options | owning the tradeoff |
| Implementation | writing the change | guiding and verifying it |
| Testing | producing tests | judging the run behind the result |
| Review | the first pass | maintainability, design, risk |

<div class="callout">The bottleneck moved to intent and verification, which is where the rest of today sits.</div>

<!--
Presenter notes:
Osmani, Saboo and Kartakis report the same split: the making compresses faster
than the deciding. Put the consequence plainly for the room. Tests
check the system, and the run record checks the agent. If you are behind the clock, cut the middle rows and
keep the first and the last.
-->
---
<!-- _class: section -->

<!-- header: "**Environment** > Challenge > Section 1 > Section 2 > Section 3" -->

# Demo: one governed run

<!--
Presenter notes:
You have six minutes for this block, two slides inside it, and five minutes of
live screen at most, so narrate it against the agenda rather than against the
tool. Four beats. First, an Omnigent session opens against the approved repository, NEMWEB research
material, tools, and identity.
Second, model traffic appears in the gateway with per-identity attribution and a
cap. Third, source definitions sit in Lakebase, while Bronze, Quarantine, Silver,
and Gold sit in Unity Catalog. Fourth, the run leaves a manifest, lineage, and a
trace the room can query later. Linger on the fourth beat, because that is what
teams take home today. Say out loud that nothing in this demo merges or deploys
itself. If a step fails twice, switch to the prepared artefact and tell the room
it is prepared. Hold the Lakebase branch-and-migrate demo for section two.
-->
---
<!-- _class: checkpoint compact -->

# Name what is proven before anyone asks

| Capability | Status you may claim today |
|---|---|
| Deterministic local pipeline through Gold | proven, and it is the baseline everyone starts from |
| Omnigent session and NEMWEB research access | preflight, with a prepared research pack and Beads fallback |
| Lakebase control plane and seed snapshot | provisioned |
| Serverless dispatcher and deployment | required configuration, so prove it live or leave it unclaimed |
| Metric view, Genie Agent, Genie One, approved MCP, identity propagation | preflight, with prepared fallback artefacts |

<div class="callout">Set the boundary. Check the evidence. Make the decision.</div>

<!--
Presenter notes:
Say this before the challenge rather than after a failure. It models the
behaviour the whole day asks for, which is naming what is proven, naming what is
only configuration, and naming the fallback. Say one more thing while the table
is up: a convention is never an access control. This is the second time the room
hears the line at the bottom.
-->
---
<!-- _class: stack compact -->

# Reference solution: one control plane, one data path

The challenge starts with NEMWEB data. Lakebase holds the source contract, and a
dispatcher creates an immutable snapshot before a generic worker processes the run. A
metric view presents governed Gold data to Genie One.

<div class="stack-flow">
  <div class="stack-row">
    <span class="lane">Control plane</span>
    <div class="node accent"><strong>Lakebase</strong><span>source definitions, parser versions, and quality rules</span></div>
    <div class="node"><strong>Dispatcher</strong><span>validates the contract and writes an immutable snapshot</span></div>
    <div class="node"><strong>Run record</strong><span>run ID and metadata snapshot ID follow the work</span></div>
  </div>
  <div class="stack-row">
    <span class="lane">Data plane</span>
    <div class="node"><strong>NEMWEB data</strong><span>fixtures or live DISPATCHIS reports</span></div>
    <div class="node"><strong>Generic worker</strong><span>the same worker reads every selected source</span></div>
    <div class="node accent"><strong>Governed layers</strong><span>Bronze, Quarantine, Silver, and Gold</span></div>
    <div class="node"><strong>Metric view and Genie Agent</strong><span>shared measures and curated data instructions</span></div>
    <div class="node"><strong>Genie One and MCP</strong><span>questions through an approved tool boundary</span></div>
  </div>
</div>

<!--
Presenter notes:
This is the reference solution, not a prescribed participant answer. Walk the
control plane first. Lakebase holds the source contract, the dispatcher validates
it, writes an immutable snapshot, and carries that snapshot ID into the run
record. Then walk the data plane. NEMWEB data goes through one generic worker and
one governed path to Gold. The metric view defines shared measures, the Genie
Agent curates the data instructions, and Genie One reaches an approved MCP only
through its preflighted tool boundary. The next two slides set the evidence and
authority limits. Groups decide what they want to investigate or improve inside
this architecture.
-->
---
<!-- _class: checkpoint compact -->

<!-- header: "Environment > **Challenge** > Section 1 > Section 2 > Section 3" -->

# Both tracks meet the same evidence bar

| | Track A: data product | Track B: engineering |
|---|---|---|
| Surface | Omnigent, then metric view, Genie Agent, Genie One, approved MCP | Omnigent, coding agent, work graph, repo, Lakebase |
| Section one | Omnigent research, Beads requirements, approved frontier | Omnigent, graph, plan, change, deployment |
| Section two | metric view, Genie Agent, Genie One, approved MCP | evals, automated pull requests, independent review |
| Section three | instructions, saved checks, self-evaluation | scorers, gates, declared metric and revert |

<div class="callout">Choose one track at 00:20 and stay in it for the rest of the day.</div>

<!--
Presenter notes:
Read the column that matches the room's majority and summarise the other one.
Pair every Track A group with a Track B group before the hands-on starts, and
record one joint claim area and one joint decision owner while you do it, because
the 01:40 and 03:05 exchanges use those pairs.
-->
---
<!-- _class: checkpoint compact -->

# Know where your authority stops

Three limits hold for the whole exercise. Where the environment does not enforce
one of them, treat it as required configuration and say so out loud.

| Limit | Meaning in this exercise |
|---|---|
| Technical boundary | workshop files, data, and samples only; no production credentials or merge. Deploy only through the preflighted workshop path |
| Human approval | broader data, another repository, or a scope change needs a person |
| Exercise rule | request review, preserve tests and policy, return evidence |

<div class="callout">If the preflight fails, stop and use the facilitator fallback.</div>

<!--
Presenter notes:
Verify every technical-boundary claim against the live environment before you
deliver this. Where a limit is unenforced, present it as required configuration
rather than as a proven property, and remove the capability rather than relying
on anyone's restraint.
-->
---
<!-- _class: section handoff challenge-section -->

# Section one
## From a question to a change you can defend, in eighty minutes.

Both tracks start in Omnigent. Product pairs research NEMWEB and shape the
requirements; engineering pairs implement an approved frontier.

<!--
Presenter notes:
Read the clock out loud: hands-on until 01:40, then the checkpoint until 01:55.
Facilitators split now, one per track, and start with the pair whose setup looks
weakest.
-->
---
<!-- _class: compact -->

<!-- header: "Challenge > **Section 1** > Section 2 > Section 3 > Close" -->

# Section one work order

| Time | Track A: data product | Track B: engineering |
|---|---|---|
| 00:20–00:36 | open Omnigent; name the decision, owner, question, and evidence threshold with the paired engineering group | open Omnigent; prime the tracker, pour the molecule, shape 5–8 beads, human approves the frontier |
| 00:36–00:52 | research NEMWEB in Omnigent: baseline, grain, freshness, and uncertainty | research the source contract: timestamp, timezone, key, watermark, quality rules |
| 00:52–01:08 | turn the research into Beads acceptance criteria; iterate them with the paired engineering group | write the plan; get it approved before any file changes |
| 01:08–01:24 | approve one ready requirement, with its evidence and boundary | implement one motivated change; deterministic tests; draft pull request |
| 01:24–01:40 | save the NEMWEB research, verified SQL, and Gold window; hand over the approved Beads requirement | deploy from a metadata snapshot and reconcile the manifest |

Return per track: one result, its evidence, one gap, and one named decision.

<!--
Presenter notes:
Point at the 00:52 row and say that it prepares the engineering change. A product
pair that skips it gives engineering an unbounded requirement rather than a ready
Beads frontier. Track B's 01:24 row is optional where the workspace preflight
failed: run the deterministic profile and present the deployment as required
configuration.
-->
---
<!-- _class: action -->

# Track B: shape the graph before you dispatch

A reviewer can judge a work graph when it has all four of these:

- 5 to 8 beads, each with an observable output and its evidence
- real dependencies only, no cycles, at least two safe parallel beads
- one human gate before anything write-capable runs
- one bead that reconciles the parallel outputs

<div class="callout">The person who proposes the graph does not approve it.</div>

<!--
Presenter notes:
Say where the boundary sits: drainers claim inside the team molecule or the
parent only, and the global ready queue is out of bounds. Done is not the same as
closed. Implementation closes only once checks, review, approval, and merge are
all recorded.
If a molecule comes up cyclic or empty, open the prepared clean molecule and
record the blockage as a returned bead.
-->
---
<!-- _class: action -->

# Track A: frame the requirement before you research

A product requirement worth implementing names four things:

- the decision and the person who owns it
- the operational or commercial value of answering it
- the NEMWEB fields, region, and time grain you need
- the evidence that would change the decision

<div class="callout">Write the requirement in a bead before the engineering pair starts implementation.</div>

<!--
Presenter notes:
Push back on technology-shaped questions, because "can someone query the table"
is not a decision. Agree the evidence threshold before the data arrives, or the
research drifts towards whatever it happens to show. If a group cannot name the
owner, that is the first thing to fix.
-->
---
<!-- _class: dense-list -->

# Research gives the requirement evidence

Track A researches NEMWEB in Omnigent and records the baseline, definitions,
time window and region, freshness and known gaps, and competing explanations.

Track B records the event timestamp and timezone, the natural key, the watermark,
the parser, the quality and quarantine rules, and whatever must stay unchanged.

<div class="callout">Both tracks answer one question first: what would make this result wrong?</div>

<!--
Presenter notes:
Sixteen minutes of research feels slow to a room that wants to dispatch, so say
what it buys: it gives the requirement evidence an engineering pair can review.
Ambiguity here costs minutes, and the same ambiguity in review costs hours.
-->
---
<!-- _class: dense-list -->

# The approved plan sets the boundary

This is Track B's plan, and everything the agent may do is in it.

```text
Work item:
Defect: processed timestamps are not normalised to UTC

Allowed context:
- the pipeline module and its tests
- run the named local timezone normalisation test
- leave acquisition, metadata, merge, and deploy untouched

Stops and evidence:
- Review request only; no merge
- Return changed lines, test output, and the run record
- Do not weaken a test to make it pass
- Stop on secrets, other repositories, unapproved data, or deploy access
```

<!--
Presenter notes:
Say what a bounded run is: an approved job with visible limits, stop conditions,
and a required review bundle, rather than a polished prompt. Track A's equivalent
has the same shape: the Beads requirement names the question, the NEMWEB evidence,
the boundary, and the stop condition before engineering starts.
-->
---
<!-- _class: action -->

# Track A: turn research into a ready requirement

Work in Omnigent with the paired engineering group.

1. Attach the NEMWEB evidence, baseline, freshness, and uncertainty to the bead.
2. State the result the change must produce and the evidence that proves it.
3. Name the files, data, or access the engineering pair must leave untouched.
4. Refine the bead until the owner approves its frontier.

<div class="callout">A ready bead gives engineering a bounded change to implement and a result to prove.</div>

<!--
Presenter notes:
This is where product research becomes an engineering boundary. The product pair
owns the decision, evidence threshold, and uncertainty. The engineering pair
owns the implementation plan. Refine the bead together until both can say what
must change, what must stay fixed, and how the result will be judged. The
approved document source belongs in section two, when the data product is built.
-->
---
<!-- _class: evidence -->

# Track B: deploy, then reconcile the run

The dispatcher reads a versioned metadata snapshot rather than live metadata.

| Reconciliation | Must hold |
|---|---|
| source definitions read | equal to definitions selected |
| Bronze rows | accepted rows plus quarantined rows |
| accepted rows | Silver rows plus declared deduplication |
| replay of the same snapshot | unchanged keys and counts |

<div class="callout">Sources are metadata rather than pipelines, so adding a source must not add a workflow.</div>

<!--
Presenter notes:
Start with the line at the bottom, because it is the architectural fact this
whole block depends on. Where the workspace preflight failed, run the
deterministic profile locally and present the deployment as required
configuration, and remind the room that a live run is never deterministic. The
manifest is the evidence, so reconcile it line by line and say which counter
failed when it does not balance. Declare the metric and the revert point before
the agent starts. Never put credentials in the repository or in a prompt. Preflight must
establish how the approved connection handles identity and credentials.
-->
---
<!-- _class: checkpoint compact -->

# Section one checkpoint

| Track | What exists at 01:40 |
|---|---|
| A | the question and owner, the NEMWEB research record, an approved Beads requirement, and the saved Gold window |
| B | the approved plan, changed files, test output, a reconciled manifest or the reason it failed |
| Both | one gap you did not close, and one named human decision |

<div class="callout">Name the decision out loud: accept, send back, reject, or stop.</div>

<!--
Presenter notes:
Two minutes per pair, and no live debugging. Record blockers here so they get
fixed before section two rather than during it. A pair with no Gold window or no
ready frontier moves to the fallback now, not after the break.
-->
---
<!-- _class: section handoff challenge-section -->

# After the break
## Section two builds. Section three improves what you built.

Track A builds the data product. Track B builds the review process.
Section two opens with a failure worth studying, then a live review demo.
Then both tracks improve the harness they just used.

<!--
Presenter notes:
Hold this slide over the break. Section two starts on the clock at 02:05 with
eight minutes of story and control points, so be back in the room before that.
Cycle the line once more before the room leaves: set the boundary, check the
evidence, make the decision.
-->
---
<!-- _class: section handoff challenge-section -->

<!-- header: "Section 1 > **Section 2** > Section 3 > Close" -->

# Section two
## Prove the work before you accept it.

Track A builds the data product. Track B builds the review process.
Eight minutes of story, a live demo, then forty-five minutes of hands-on.

<!--
Presenter notes:
Read the clock: story and control points until 02:13, demo until 02:20, hands-on
until 03:05, then the cross-track exchange. Then say what changed over the break.
Section one produced work. Section two decides whether that work can be accepted,
and builds the thing that decides it. Facilitators split by track again after the
demo.
-->
---
<!-- _class: stack -->

# Routine tickets are the first place to automate

A platform team automated routine work: adding instance types, adding cluster
events, and cleaning up feature flags.
The work is clear and bounded, which is what makes it a fit for an agent. The
pipeline takes a ticket identifier and returns a pull request with tests.

<div class="stack-flow">
  <div class="stack-row">
    <span class="lane">Pipeline</span>
    <div class="node"><strong>Ticket</strong><span>bounded work with a clear definition of done</span></div>
    <div class="node accent"><strong>Plan</strong><span>a human approves it before anything runs</span></div>
    <div class="node"><strong>Agent run</strong><span>no human review anywhere inside it</span></div>
    <div class="node accent"><strong>Pull request</strong><span>code and tests, and a human reads it</span></div>
  </div>
</div>

<div class="callout">Two human decisions: the plan going in, and the pull request coming out.</div>

<!--
Presenter notes:
This is a production-shaped pipeline story, and it is the good case rather than
the cautionary one, so say that first. Routine tickets with a clear
definition of done are exactly where you start. Point at the two coral boxes and
name them: a human approves the plan, and a human reads the pull request. The next
slide only makes sense once the room can see that nothing checks the work between
those two points.
-->
---
<!-- _class: warning -->

# Correct code can still break the contract

A contract is a rule the system must preserve while the code around it changes.

On one ticket the contract was a single end-to-end test, and the run returned:

- a correct implementation
- three agents acknowledging the required test in their comments
- a pull request with no end-to-end test in it
- a gatekeeper agent that passed it, because it was checking code quality

<div class="callout">Nothing in that pipeline compared the requirement to its proof.</div>

<!--
Presenter notes:
Ask the room first: the last time you accepted an agent's changed files, what did
you verify? Wait seven seconds and take two answers. Then walk the four lines
slowly. The agent chose files, tools, and tests between the two human decisions
on the previous slide, and every one of those choices looked reasonable in the
summary. The pipeline had no enforced link between the required test and the
evidence that it existed. The UTC normalisation defect
in section one's plan is a contract of exactly this kind.
-->
---
<!-- _class: action compact -->

# They fixed the harness, not the prompt

- Plan requirements now carry machine-readable labels, `[REQUIRED]`, `[RECOMMENDED]`, and `[OPTIONAL]`, rather than prose an agent can acknowledge and then ignore.
- A plan-compliance gate reads the pull request against the approved plan before a human sees it, and returns `REQUEST_CHANGES` when a required item has no evidence.
- Metrics come from build output, coverage, and continuous integration rather than from the agent's own assessment.
- The decision journal is append-only, and it records who decided what, on what evidence.

On the next run the gate caught the missing test and sent the work back. The agent
added the test, the gate cleared it, and a human reviewed a pull request that had
already passed its own contract.

<div class="callout">Does this change prove what the ticket asked for? A gate answers that now.</div>

<!--
Presenter notes:
Say the headline twice, because it is the whole lesson: the prompt was not the
problem. Read the four repairs at pace, then slow down for the outcome, then read
the callout and say where that question used to live, which is in the head of one
senior engineer who had to remember to ask it.
The first repair is the one people underestimate, so put it plainly. Prose an
agent can acknowledge is not a requirement, and a label a gate can read is. If
somebody objects that this is a lot of machinery for routine tickets, agree, and
say it was built once and now runs on every ticket.
-->
---
<!-- _class: checkpoint compact -->

# Put checks where they change the outcome

| Phase | Enforced control |
|---|---|
| Requirements | name the criteria, the scope, and the evidence |
| Design | set the repo, tools, data, spend, and stops |
| Plan | require a named approval before files change |
| Implementation | run on an isolated branch, open a draft pull request |
| Testing | run the tests and the static and runtime checks |
| Review | judge the outcome and the conduct |
| Release | keep the merge and the deploy human-owned |

<div class="callout">A warning is not a control point.</div>

<!--
Presenter notes:
Ask which of their current review steps would catch the missing test, and wait
seven seconds. Then use two rows only, Plan and Release. Intent is cheapest to
change before code exists, and a green check is not an approval. The four repairs
on the previous slide are all instances of this table, so tie them back one at a
time if the room wants the mapping. Tell them this is the one rule to carry all
day.
-->
---
<!-- _class: evidence -->

# Decide from the run record

The record is everything the run captured, the review bundle is what somebody
selected from it, and the recap is the agent's own summary.

| Question | Evidence |
|---|---|
| Did the change land correctly? | changed lines, tests, automated checks |
| Did the run stay inside limits? | identity, plan, files, tools, data, policy |
| What did it cost? | model use, tools, time, retries |

<div class="callout">The decision is one of four: accept, send back, reject, or stop.</div>

<!--
Presenter notes:
Only the first question is about code. Say that a correct change still gets
rejected when the agent crossed a data or tool boundary. Every decision needs a
named owner and a link to the evidence that owner read, and if all you have is
the recap, say so, because weak evidence limits the claim you can make.
-->
---
<!-- _class: checkpoint compact -->

# Every program needs its own harness

The shape travels between teams. The content does not, because the contracts, the
definition of done, and the boundaries are yours.

| What you can copy | What you have to write |
|---|---|
| requirements labelled by force | the labels your definition of done needs |
| a gate that reads the approved plan | the checks that gate runs, contract by contract |
| metrics taken from the build | the signals your build already emits |
| an append-only decision journal | who owns each decision on your team |
| stop conditions inside the contract | the boundaries that must halt a run |

<div class="callout">A schema change, broader access, or a production exception must halt the run.</div>

<!--
Presenter notes:
This is the bridge into the exercise, so keep it to a minute. The left column is
what you can lift from another team or from anyone else. The right column is
why nobody can hand you a harness. Read the callout as the stop-condition rule:
work that turns out to need a schema change, broader access, or a production
exception returns to the owner instead of letting the agent improvise through the
boundary. Then
say what happens next: the demo shows one of these gates running, and in
forty-five minutes each track builds the first version of its own.
-->
---
<!-- _class: section -->

# Demo: review, evals, and Genie One

<!--
Presenter notes:
Seven minutes, and you build this demo yourself, so here is what it has to show
rather than how to drive it. Four beats. First, acceptance criteria as an eval
suite, with each criterion labelled by force, so the room sees a requirement that
a machine can check. Second, the agent opens a draft pull request and the
plan-compliance gate returns a change request on a missing required item, which is
the repair running live. Third, a reviewer that differs from the author,
reading the record: changed lines, test output, cost, and the decision with a
named owner. Fourth, Track A's half: a metric view, a Genie Agent grounded in it, a Genie One
question, and one approved MCP with its access boundary. Show one question the
experience declines to answer. If the clock allows, add
the Lakebase beat: branch the control plane, apply a migration on the branch,
verify with the same tests and counters, then discard the branch. Say the four
conditions out loud while that branch is up, because section three depends on
them: verifiable, reversible, short horizon, bounded scope. Never debug for more
than two minutes. Switch to the prepared artefact and say that it is prepared.
-->
---
<!-- _class: compact -->

# Section two work order

| Time | Track A: data product | Track B: review and evals |
|---|---|---|
| 02:20–02:35 | create a metric view over the Gold window; name the measures and dimensions it exposes | turn the acceptance criteria into evals, each one labelled required, recommended, or optional |
| 02:35–02:50 | create a Genie Agent grounded in the metric view; record its scope and instructions | run the agent to a draft pull request; let the gate check it against the approved plan |
| 02:50–03:05 | use the agent in Genie One; add an approved MCP and record its identity and access boundary | review with a reviewer that differs; record the decision and the evidence you read |

Return per track: one artefact, the evidence behind it, one refusal, and one named decision.

<div class="callout">Keep the existing boundary: no merge, no deploy, no unapproved data, and no weakened test.</div>

<!--
Presenter notes:
One minute on this, then get out of the way. Two asks are easy to lose, so say
them out loud. Track A owes a refusal: one question the product will not answer, and the reason.
It also owes a metric view, a scoped Genie Agent, and an approved MCP whose access
boundary it can name. Track B owes a verdict from the gate before the human
decision, because a gate nobody has seen reject anything is not yet a control.
Where a preflight failed, run the fallback and label it, and use the time on the
review instead. The 02:50 row is what section three improves, so tell groups not
to polish it.
-->
---
<!-- _class: action -->

# Build it in this order

Same forty-five minutes, two different jobs. Read your own column.

<div class="cards">
  <div class="card">
    <span class="label">Track A</span>
    <h3>A governed data experience</h3>
    <ul>
      <li>create a metric view over the Gold window, with named measures and dimensions</li>
      <li>create a Genie Agent grounded in that metric view and its declared scope</li>
      <li>use the agent in Genie One, then add one approved MCP</li>
      <li>record the MCP identity and access boundary, then save one question it refuses</li>
    </ul>
  </div>
  <div class="card accent">
    <span class="label">Track B</span>
    <h3>A review that runs without you</h3>
    <ul>
      <li>write the criteria first, and label each one by force</li>
      <li>let the agent open the draft pull request, and do not fix it by hand</li>
      <li>run the gate before you read the diff</li>
      <li>give the review to somebody, or something, that did not write it</li>
    </ul>
  </div>
</div>

<!--
Presenter notes:
Leave this up while they work, because it is the reference sheet for the block
rather than a slide to present. Read the column that matches the majority, say one
sentence about the other, and stop. The last bullet in each column is the one people skip. Track A adds an MCP
without recording who can use it or what it can reach. Track B reviews its own
change, which is the failure from the story at the top of this section, where
nothing compared the requirement to its proof. If a pair is stuck on Track A's
third bullet, that is a preflight failure rather than theirs, so hand them the
fallback and keep them moving.
-->
---
<!-- _class: checkpoint compact -->

# Section two checkpoint

| Track | What exists at 03:05 |
|---|---|
| A | a metric view, scoped Genie Agent, Genie One question, MCP access boundary, and one question it refuses |
| B | the labelled criteria, the gate's verdict on a required item, the independent review, and the decision |
| Both | one thing the harness now prevents, and one named human decision |

<div class="callout">Bring the gate's verdict, not the agent's summary.</div>

<!--
Presenter notes:
Two minutes per pair, in the pairs you formed at 00:20, and no live debugging.
Ask each pair the same closing question: what can your harness now stop that it
could not stop an hour ago? Write the answers down, because they are the input to
section three. A pair with nothing the harness prevents goes into section three
with that as its first job.
-->
---
<!-- _class: section handoff challenge-section -->

<!-- header: "Section 2 > **Section 3** > Close" -->

# Section three
## Make the data experience useful, then test the agent behind it.

Seven minutes on cost, traces, and gates, then twenty-eight minutes of hands-on.
Track A builds an AI/BI dashboard or Databricks App and benchmarks its Genie Agent.
Track B turns one failure into a durable control, with a metric and a revert point.

<!--
Presenter notes:
Thirty-five minutes, and it is the section people remember, because it is the one
they can repeat at work on Monday. Read the clock: four slides until 03:22,
hands-on until 03:50, then the close. Track A makes the metric view usable in an
AI/BI dashboard or Databricks App, then creates benchmark cases for the Genie
Agent and tries a Genie One skill. Track B names the metric it should move and the
point it reverts to. The four slides are cost, traces, gates, and the instruction
file, and the last two come from a Databricks application that runs all of this in
production, so speak from that rather than from theory.
-->
---
<!-- _class: action -->

# Context is the budget you spend

The cost line on a run record moves when you change what the agent carries.

- Decide what loads in every session and what the agent fetches on demand.
- Keep stable material early and volatile material late, so the cached prefix survives.
- Read cache writes, cache reads, and turns in the trace before you argue about the model.

<div class="callout">Declare cost per accepted change as the metric, and the previous instruction file as the revert point.</div>

<!--
Presenter notes:
This answers the third question on the run record, the one about what a run cost,
so tie it back to that slide rather than starting fresh. Say the two levers
plainly. First, static context is
what loads in every session and dynamic context is what the agent fetches when
the task calls for it, and deciding which is which is a design decision you
review like any other configuration. Second, a cached prefix survives only while
the front of the prompt stays still, so changing tool definitions or system
instructions mid-session is a harness change rather than a casual tweak. If
somebody asks for numbers, the distillation in
notes/prompt-caching-distillation.md has them from Anthropic's prompt caching
documentation, a five-minute cache write at 1.25 times base input, a read at a
tenth, and a five-minute lifetime refreshed on reuse. Say that prices and
lifetimes move, and point at the provider page rather than quoting a figure you
cannot check in the room. Then close the loophole: cheaper context never widens
the boundary, and a run that reaches for unapproved data is still rejected. Ninety
seconds here, because three more slides follow before the room starts working.
-->
---
<!-- _class: evidence -->

# Read the trace before you argue about the model

A trace is the run's own account of itself, and it answers questions no summary can.

| Question | Where the trace answers it |
|---|---|
| What did it actually do? | the spans: tools called, files touched, commands run |
| Did it stay inside the envelope? | identity, granted scope, and every policy denial |
| Why was it slow or expensive? | turns, tokens, cache reads and writes, retries |
| Would you accept this trajectory? | stop conditions honoured, or improvised past |

<div class="callout">Read the trace before deciding whether the run is acceptable.</div>

<!--
Presenter notes:
Say the pairing again: tests check the system, and traces check the agent. The
table answers the run-record questions with the fields that settle them. For cost,
read turns, tokens, cache reads and writes, and retries before arguing about the
model. If a pair has no trace for its run, it has found the harness gap to improve
next. The supporting cache mechanics and current provider numbers are in
notes/round3-economics-briefing.md; use them only for questions.
-->
---
<!-- _class: checkpoint compact -->

# Build gates that can say no

These layers are from a Databricks application in production, in the order they were built.

| Gate | What it catches |
|---|---|
| static guards and semgrep rules | the risky shape you already fixed once |
| unit and contract tests | behaviour you can assert without deploying |
| golden cases run against a live target | a number that moves with no code change |
| a browser test before deploy | the path a user takes, broken by a green build |
| the same evals again after deploy | drift that only the deployed system shows |
| a scheduled run, built last | the failure nobody was watching for |

<div class="callout">Allowlist the debt you have and fail anything new, or no guard ever lands.</div>

<!--
Presenter notes:
The order is the lesson, so say it plainly: do not build the scheduled loop until
the gates underneath it can say no. Two facts from that codebase are worth saying
out loud. The golden cases were frozen from real estimates that had already burned
the team, so the suite is a record of past bugs rather than a generic starter kit.
And the scheduled layer never merges, never deploys, and never escalates past a
recommendation, with a per-run and a daily token cap set before its first
unattended run rather than after the first surprising bill. If somebody asks where
model judges fit: a cost estimate is a pure function of its inputs, so an
assertion beats a judge, and a judge would add nondeterminism to a system that has
none. Judges earn their place on the one surface that is judge-shaped, which here
is the sizing agent. The workshop uses prepared benchmark artifacts for this example. Keep the detailed
provenance with facilitators rather than in participant materials.
-->
---
<!-- _class: warning -->

# Your instruction file is an untested claim

Every session loads it, and every line in it is supposed to change what the agent
does. That is a claim you can measure, and one team measured it.

- 25 probes, each one a failure that team had already made twice
- every probe cites the commit, guard, or incident it came from, or it does not count
- scored against a placeholder file, because the gap is what your file buys
- one section of the file made agents worse than no file at all

<div class="callout">At one sample per probe, twelve rules looked dead. At three, only four were.</div>

<!--
Presenter notes:
This is the slide that makes the subject of section three concrete: the thing
under test is the harness, not the model and not the app. Read the last bullet
slowly, then wait, because it lands on anyone who has written an instruction file
and never checked it. Two traps if a group wants to build this. First, grading
that cannot read negation inverts the result, because "never edit this file" is
the correct answer and a naive check scores it as a violation, and an optimiser
pointed at that metric learns to stop mentioning the anti-pattern, which buys
nothing and looks like progress. Second, one sample is below the noise floor,
which is what the callout is about. On the optimiser: it moved the held-out score
from 0.944 to 0.959, which is noise, so treat that class of tool as a gap finder
rather than an author. The workshop uses prepared benchmark artifacts for this example. Land the plane
here: this is why the next half hour asks you to name the metric and the revert
point before you change anything.
-->
---
<!-- _class: compact -->

# Section three work order

| Time | Track A: data product | Track B: review and evals |
|---|---|---|
| 03:22–03:36 | build an AI/BI dashboard or Databricks App from the metric view; show the owner, source, and freshness | pick one failure; write the guard, scorer, or gate that prevents it; freeze one golden case from a run you already trust |
| 03:36–03:50 | create Genie Agent benchmark cases from real questions; try a Genie One skill and record the result, refusal, or fallback | rerun the same ticket; compare the trace, the gate's verdict, and the cost per accepted change; keep it or revert |

Return per track: Track A returns the dashboard or app, benchmark cases, the skill attempt, and the decision; Track B returns the failure, change, metric, before and after, and keep-or-revert decision.

<div class="callout">A benchmark is a real question with an expected answer, evidence, or refusal.</div>

<!--
Presenter notes:
Track A starts with the metric view created in section two. The dashboard or app
must show the owner, source, and freshness, then the pair creates benchmark cases
from questions it actually asked today. The Genie One skill is an attempt, not an
unverified promise: record whether creation worked, what it did, or the fallback
used. Track B works from a failure it actually hit today, not one it can imagine.
Send anyone who is stuck to the blockers you wrote down at 03:05. Two shapes of
cheating to name early: loosening a check until it passes, and rerunning a
different task.
-->
---
<!-- _class: action -->

# Improve it in this order

Track A makes the data experience useful and tests the agent behind it. Track B
builds a control from a failure it observed.

<div class="cards">
  <div class="card">
    <span class="label">Track A</span>
    <h3>A data experience people can use</h3>
    <ul>
      <li>build an AI/BI dashboard or Databricks App from the metric view</li>
      <li>put the owner, source, and freshness on the surface</li>
      <li>create Genie Agent benchmark cases from real questions</li>
      <li>try a Genie One skill, then record the result, refusal, or fallback</li>
    </ul>
  </div>
  <div class="card accent">
    <span class="label">Track B</span>
    <h3>A gate that earns its place</h3>
    <ul>
      <li>name a failure from today, and the trace that shows it</li>
      <li>write the guard, scorer, or gate that catches it</li>
      <li>freeze one golden case from a run you already trust</li>
      <li>rerun the same ticket, and compare trace, verdict, and cost</li>
    </ul>
  </div>
</div>

<!--
Presenter notes:
Spend Track A facilitation on the benchmark cases. They need to come from questions
someone actually asked, with an expected answer, evidence, or refusal. Spend Track
B facilitation on the first bullet. A failure they invented is worth nothing here,
so send them to the blockers recorded at 03:05 and make them pick one that actually
happened. Track B freezes a case so the failure cannot come back quietly. If a pair
finishes early, Track A adds a benchmark case and Track B adds a second case rather
than a second change.
-->
---
<!-- _class: recap compact -->

<!-- header: "Section 3 > **Close**" -->

# Keep these five when you get back

- Implementation compressed and judgement did not, so your work moved to the boundary you set and the evidence you read.
- The agent is a model inside a harness, and the harness is the part you engineer.
- A gate nobody has watched reject anything is not yet a control point.
- The record answers what a recap cannot, so the decision belongs to a named person who read it.
- Every program needs its own harness, and an improvement nobody measured is a preference.

<div class="callout">Choose the workflow that gets its first governed run.</div>

<!--
Presenter notes:
Run the share-out first, with the work order still on screen, because pairs report
against its return list rather than against a new artefact: the failure, the
change, the metric, the before and after, and the decision. Four pairs, ninety
seconds each, picked while they work and picked for contrast rather than polish.
One that reverted, one whose gate caught something, one Track A refusal, and one
that never got its deployment working. Ninety seconds means you interrupt, so say
that before the first pair starts.
Then put this slide up and read the five lines without elaborating on any of them.
Point back at the promise from the second slide of the day while you do it, because
this is the same list with the day's evidence behind it. If the room is quiet,
leave it up and say nothing for ten seconds. Then go to the pilot.
-->
---
<!-- _class: action compact -->

# Turn this on in a workflow you already own

Pick the row that matches your work. Run your first governed session in one
workflow you already own, inside a fortnight.

| Your work | Turn on | What you get in week one |
|---|---|---|
| You delegate code | Omnigent, with Unity AI Gateway in front of it | a governed session with policy and sandbox, and every model call routed, attributed, budgeted, and capped |
| You answer questions with data | Genie One, on a table you already trust | a governed answer carrying its source and freshness, saved so a colleague can rerun it |

Before you leave, name the workflow, the owner, the evidence you will demand, and
what stops it.

<div class="callout">Set the boundary. Check the evidence. Make the decision.</div>

<!--
Presenter notes:
This is the outcome the four hours exist to produce. Ask the room to name a
workflow rather than a general intention to explore agentic tools. Most rooms
split along the track people chose at 00:20, so read the row that matches the
majority and name the other one. Ask for a date: the fortnight it runs in, and the
person who owns the decision to accept or stop the work. Pause before the last
line, then read it slowly, because those four things are the whole day in one
sentence.
Two caveats belong here. Check what is actually enabled in the customer's account
before anyone promises a capability, because what Unity AI Gateway can do, and
whether it is still in preview, varies by account, and the Omnigent status hedge
from the harness slide still applies. Where something is not enabled, make a named
enablement request with an owner and a date.
docs/pilot-canvas.md is the handout, and the longer five-line version of this ask
is on it. Then say the line for the third and last time, and stop talking.
-->
---
<!-- _class: evidence compact -->

<!-- header: "Appendix" -->

# Appendix: telling shown from proven

| | Claimed | Shown | Proven |
|---|---|---|---|
| The result | described in a summary | the artefact exists and opens | somebody else reran it and got it |
| The boundary | assumed | written down | enforced, and the denial is in the record |
| The decision | implied by the merge | a named owner | the owner, plus the evidence they read |

<div class="callout">The right-hand column is what today is asking you to produce.</div>

<!--
Presenter notes:
This replaces the points-based scorecard, which came out of the deck because there
is not enough time to run it properly and a half-run scoring scheme is worse than
none. There are no points, no penalties, and no contention. Use this only if a
group asks how they are being judged: read one row, say that the right-hand column
is the bar, and go back to the work. It is also a useful closing frame at 03:50,
because most teams arrive in the middle column and can name what would move them
right.
-->
