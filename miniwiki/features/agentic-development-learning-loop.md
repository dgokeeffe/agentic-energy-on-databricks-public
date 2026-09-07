# Make the development process teach the workshop

Status: David approved the first local slice, now implemented in the shared skills,
pair record, participant playbook, and [read-only practice](../../workshop/agent-practice/README.md).
Native adapters and the standalone learning skill remain deferred. No runtime,
acceptance-floor, timetable, model-policy, or permission changes were made.
Facilitator placement, rehearsal, and actual agent baseline/replay evidence remain
pending; the fixtures and text/contract tests do not establish those results.

The design and earlier review below explain the implementation. This page responds
to David's request to make task-aware preparation, verification, structural review,
normal refinement, and reusable learning visible in the workshop itself.

## What is already here

The active participant route is the shared GitHub-issue lifecycle in
[QUICKSTART](../../QUICKSTART.md) and the
[participant playbook](../../docs/participant/workshop-playbook.md). The retained
business and engineering lane directories are historical; do not extend those as
though they were the active exercises.

The repository already has skills for requirements, planning, implementation and
tests, agentic evaluation, independent review, and PR preparation. It requires a
plan approved by a different person, preserves governed contracts, and keeps
participants out of deployment and workspace mutation.

The useful additions are more specific decisions and a visible learning loop, not
a parallel lifecycle or a large new agent team.

## Gaps identified before this slice

- [understand-requirement](../../.agents/skills/understand-requirement/SKILL.md) and
  [plan-change](../../.agents/skills/plan-change/SKILL.md) specify necessary contracts
  but do not explicitly vary preparation and proof with the kind of task.
- [agentic-eval](../../.agents/skills/agentic-eval/SKILL.md) asks for inspected evidence,
  but does not make an investigation distinguish an explanation ruled out from one
  not examined.
- [adversarial-review](../../.agents/skills/adversarial-review/SKILL.md) covers important
  correctness and safety topics, but does not explicitly review code structure as a
  separate question from passing tests.
- The [pair record](../../docs/participant/workshop-pair-record.md) records findings
  and repairs, but not the distinction between normal refinement, correction of an
  error, and abandoning an approach.
- The active playbook and [run of show](../../docs/facilitator/workshop-run-of-show.md)
  end with human disposition. They do not require a reusable lesson and a subsequent
  local check showing whether it helps. This leaves Observe and Improve less visible
  than the delivery stages.
- The repository-owned [verification skill](../../.agents/skills/agentic-verification/SKILL.md)
  still prescribes two reviewers for a small change, larger fixed ranges, and specific
  model names. It assumes role availability not supplied as repo-local native agent
  definitions. This differs from the current machine-level risk-based guidance and
  undermines a fresh-clone workshop. Preserve the repository's current verification
  floor in the first patch. Any change to reviewer counts or model policy is a separate
  decision for David, not an incidental consequence of adding portable roles.
- [The current-focus page](../now.md) still describes a seeded patch under a historical
  lane, while the active run of show says those lanes are not routed. Reconcile that
  pointer rather than using it to revive an old exercise.
- [Routing tests](../../tests/test_workshop_routing.py) mainly check file presence and
  keywords. They do not demonstrate source-aware investigation, structural review,
  or successful transfer of a lesson to another case.

## First slice: approved for local implementation

Pilot one prepared, read-only two-case exercise, add five explicit fields to the
existing pair record, and make the existing requirement/plan/eval/review skills use
them. Do this before adding a new learning skill or native agent adapters.

Implemented fixture paths:
`workshop/agent-practice/cases/zero-generation.json` and
`workshop/agent-practice/cases/missing-generation.json`, with a short source-contract
note and expected findings. Both are labelled synthetic/non-live. The first asks
whether zero SCADA output establishes unavailability; the second asks whether missing
SCADA establishes zero output or unavailability. Neither conclusion is supported.
The accepted issue must authorise the exercise; do not invent an issue number or
silently add an unrelated mandatory task.

Add these five fields to the pair record:

1. Task kind, preparation choice, and verification rationale.
2. Explanations ruled out with cited evidence, versus paths not investigated.
3. Refinement, defect correction, restart, or block, with a short reason when relevant.
4. Structural-review result, location, consequence, and remaining uncertainty; "no
   material issue found" or "not applicable" with a reason is valid and does not
   require manufacturing a defect.
5. Proposed lesson or "do not generalise", the original and second-case inputs/results,
   and a keep/revise/discard decision. Label actual agent output separately from
   facilitator-prepared output, and unrun steps as not-run.

The calibration demonstrates investigation and transfer; structural review applies
to the pair's actual approved code change and does not need another artificial defect.
A changed instruction for the calibration stays in the pair record and is replayed
read-only. It is not a post-review repository change. Converting that lesson into a
shared skill or regression test is a later reviewed task, unless explicitly included
in the original plan before implementation. A correct baseline is not a failed
exercise: retain it and record that no additional instruction was needed.

Proposed teaching placement: reserve ten minutes within the 13:35-14:05 agentic-eval
block for the two-case calibration, with the remaining time for the existing eval.
This requires facilitator approval and rehearsal before changing the clock source.
If it cannot fit without reducing a required gate, use a prepared facilitator demo
or defer it; do not consume review, repair, or human-disposition time silently.

Put the investigator and reviewer prompts needed for the calibration in its fixture
README, not a separate role catalogue. Use them in fresh conversations or already
available constrained subagents for this first slice. Do not claim a prompt alone enforces read-only access. A human
reviewer is the fallback when the intended agent tool restrictions cannot be proven.
Preserve the repository's existing reviewer floor and plan-approval requirements.

## Target approach after that pilot

### Strengthen existing skills

In `understand-requirement` and `plan-change`, identify what the task needs:

- Repetitive task: start from the relevant tested procedure and check that it still fits.
- Small repair: a short plan with an explicit regression case.
- New component or multi-step change: discuss the design, responsibilities, interfaces,
  and failure behaviour before implementation.
- Investigation: state plausible explanations, supporting and contrary evidence,
  paths not yet inspected, and what would settle the question.
- Translation or migration, when such a task is actually selected: compare behaviour
  against the reference and check dependency or language differences. Do not add a
  live migration exercise merely to illustrate this category.

These are preparation choices, not maturity levels or permission tiers. Every selected
workshop issue still goes through the existing human approval and required checks.
Maintainers use the same preparation, review, and learning discipline for repository
development, but their explicitly authorised tasks remain distinct from participant
activities. A task classification must never grant deployment or data-access permission.

In `agentic-eval`, distinguish normal refinement, defect correction, restart, and
blocked execution. Record a reason when relevant; do not create a target number of
turns or penalise useful refinement as failure.

In `adversarial-review`, require two explicit answers: does the implementation satisfy
the intended behaviour, and does its structure fit the existing design? A structural
finding should name the responsibility, dependency, duplication, or interface problem,
with a location and consequence. Do not manufacture a defect to fill a checklist.

### Package learning when the procedure has been exercised

After the first pilot, consider `.agents/skills/capture-learning/SKILL.md`, used by
maintainers and participants. This is a shared recipe for evaluating a lesson, not
a requirement for every participant to create a skill. Its proposed procedure is:

1. Select an observed difficulty or useful refinement, not an invented failure.
2. Decide whether it is reusable. Keep one-off context in the issue or session note.
3. Put reusable behaviour into a regression test, a repeated procedure into a skill,
   or a design convention into concise guidance.
4. If the new file or change is outside the approved plan, amend the plan and obtain
   approval before editing it. Never weaken a check to demonstrate improvement.
5. Rerun the original case and at least one variant or counterexample in an isolated
   local environment. Record outcomes and limitations; do not call one replay a
   general productivity measurement.
6. Keep, revise, or revert the proposed lesson through normal review. No automatic
   global instructions, commits, or permission changes.

### Supply portable specialist roles

After the prompt handoffs have been rehearsed, provide optional native adapters for
the supported harnesses. Keep the underlying role prompts repo-owned rather than relying on
David's global configuration. For Pi, the documented project location is
`.pi/agents/`; names should be distinct from builtins, such as:

- `workshop-investigator`: read-only, invoked when an investigation needs it; returns
  hypotheses, exact sources, contrary evidence, and unknowns, not a confident recap.
- `workshop-implementer`: receives the approved issue/plan and changes only the agreed
  files. Executes local checks and preserves their actual output. Cannot approve its
  own result or grant itself external actions.
- `workshop-reviewer`: fresh-context and read-only; checks behaviour, design structure,
  verification adequacy, and participant limits. Returns evidence-backed findings to
  the parent, which arranges reproduction and repairs.

Keep human planning and final disposition. Role definitions and reviewer counts are
different: one reviewer definition can run as several fresh instances with distinct
lenses. Preserve the current repository verification floor in the first patch,
including two reviewers for a small change and the existing requirements for larger
changes. Add an investigator when a particular unanswered question warrants it.
Resolve configured, approved models without introducing additional generation pins
or overriding provider restrictions. An adaptive reviewer-count/model policy is a
separate proposal requiring David's explicit approval. Preserve repository instruction
inheritance and explicit skill paths. Read-only tools must be restricted by the
supported harness, not merely requested in prose.

Document the same handoff for a fresh assistant conversation or human reviewer when
native subagents are unavailable. Verify any Omnigent adapter separately before
claiming it works; a Pi agent file does not configure every harness.

## What participants should experience

Fit these activities into the existing playbook rather than create another track:

- At planning, explain why this issue needs the chosen preparation and verification.
- During investigation, distinguish "ruled out" from "not investigated". A useful
  read-only example is whether zero SCADA generation establishes unit unavailability:
  the [repository contract](../../README.md) explicitly keeps actual output and
  authoritative availability separate. Use a labelled prepared case, not a claimed
  live observation, and associate any participant task with an actual selected issue.
- At review, see that green tests do not alone settle code organisation or test adequacy.
- In the approved calibration slot, record one proposed instruction change and replay
  the two read-only cases. The final report can explain what was learned. It must not
  start an unplanned repository change after independent review. A correct decision
  not to generalise is valid; do not incentivise useless skill additions.

Use the proposed agentic-eval slot above only after facilitator approval and rehearsal.
The 15:20-15:45 disposition/report block remains for its existing purpose.

## Acceptance for an implementation

- Existing lifecycle, participant limits, and governed semantics remain intact.
- Fresh-clone instructions do not depend on personal skills or globally named agents.
- Any native adapter added in a later stage is discovered and exercised in the intended
  supported harness; tool restrictions are verified, or that route is explicitly not
  demonstrated. No native adapter is required to complete the first slice.
- Local tests cover navigation and prompt/record requirements without pretending that
  keyword checks prove agent behaviour.
- The two-case calibration retains the input, actual or prepared output, expected
  finding, and an independent check against the source contract. Record where a
  conclusion exceeded the evidence and whether a revised instruction helped on the
  second case. Structural review records a result on the actual approved code change.
  Do not claim an unrun demo or a model's confident summary is proof.
- A participant can explain the preparation choice, verification method, refinement,
  review result, and retained or rejected lesson in the pair record.
- Run the repository-required local checks for the eventual change. Never run
  workspace-aware commands as part of this proposal review.

## Files and next action

The first patch would touch the existing requirement/plan/eval/review skills, the two
prepared cases and expected findings with their README prompts, the participant
playbook and pair record, and workshop tests. Tests should verify
specific evidence fields and fixture facts; semantic interpretation still needs an
independent check against the supplied contract. Update the facilitator clock only
with explicit approval. Native adapters, a standalone learning skill, and changes to
reviewer-count/model policy are later decisions, not bundled into this first patch.
Add navigation links only where needed and repair the stale current-focus pointer.

There are already unrelated uncommitted changes in the application, foundation,
Lakebase material, and Makefile. Do not overwrite them or add these changes to an
unrelated commit. Keep the first implementation local and separate from runtime work.

Next: review the local diff and agree facilitator placement and rehearsal before
using the exercise in a session. Retain actual baseline/replay outputs before claiming
a learning improvement. Native adapters, a new learning skill, model-policy changes,
and deployments still need their own approval; this implementation grants none.

## Review and validation of this proposal

Independent static review identified an implicit reviewer-floor reduction, an
under-specified exercise, and a risk of adding unplanned changes after review. The
proposal now preserves the existing review floor, names the two cases and five record
fields, keeps the calibration read-only, and defers native adapters and a new learning
skill. The proposed teaching slot still requires facilitator approval and rehearsal.
The workshop-practicality reviewer confirmed the revised proposal resolves those
teaching findings at plan level. No demonstration or application test was run in
preparing this note.

At proposal stage, only this page and its index entry changed. That validation was
limited to links and whitespace.

## Local implementation evidence

The first slice updates four existing lifecycle skills, the playbook and pair record,
and adds the practice README, two source-cited synthetic cases, a separate facilitator
answer key, and `tests/test_agent_practice.py`. The parent also repaired the historical
lane pointer in `now.md` and updated this page and the index.

The implementer reported 14 direct stdlib tests and 21 focused pytest checks passing,
plus miniwiki validation and path-scoped whitespace checks. These validate fixture
facts, malformed/missing representations, source links, and document integration;
they do not prove model behaviour or lesson transfer. The full `make validate-local`
gate was not run because it builds and installs against unrelated work in progress.
No live tests, deployment, workshop rehearsal, or timetable change was performed.

The worker observed concurrent changes in unrelated integration-evidence files and
left them unread and untouched. The Git index later changed during external integration
activity; the staged diff was empty when the parent checked, and these process changes
remained unstaged on the same branch. Do not attribute that integration activity to
this task or alter it to clear a gate.
