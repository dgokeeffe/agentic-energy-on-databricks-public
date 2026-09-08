# Read-only investigation practice

> A separate, shorter facilitator demonstration drawn from a real defect in this
> repository's own pipeline is in
> [green-tests-wrong-code.md](green-tests-wrong-code.md). It asks where a test suite
> touches the code that actually runs. It is not a participant exercise and shares
> the placement and rehearsal limits below.

This optional exercise asks a pair to investigate a supplied observation, check
its reasoning independently, and test whether a proposed instruction helps on the
original input and a variant. It is a small synthetic, non-live calibration, not
a blinded benchmark or a general productivity measure. No agent run or workshop
rehearsal is evidenced by these prepared files.

## Placement and limits

Placement and rehearsal are pending facilitator approval. Tracks are self-paced,
so this exercise adds no clock pressure, but use it only when the current track
stage and approved plan authorise it, and only if it fits without replacing any
required check. Otherwise defer it or use a labelled prepared facilitator
demonstration outside the required work.

The investigator and reviewer inspect supplied artefacts only: no repository
writes, commands, workspace access, external queries, or live data. The pair
records the result in its existing [track record](../track-record-template.md).
A prompt alone does not enforce read-only access. The facilitator must verify the
session's actual tool restrictions before using it. Use an already available
restricted assistant, or a constrained fresh session with only the supplied text
and no tools. If native agents are unavailable, the constrained fresh session is
sufficient; if restrictions cannot be verified, use a human reading the same
packet. Record the route and limitation, not an unproven agent capability.

Keep the existing human plan approval and independent-review requirements,
including the reviewer floor in
[agentic-verification](../../.agents/skills/agentic-verification/SKILL.md).
Fallbacks do not reduce that floor. This exercise's output check does not replace
the independent reviews of the actual change; unavailable reviewers leave that
gate incomplete. No native adapter, new skill, or model-policy change is required.

## Inputs and source contract

The facilitator prepares two investigator packets, one per case:

- Original: [zero-generation.json](cases/zero-generation.json).
- Variant: [missing-generation.json](cases/missing-generation.json), containing
  both a null field and an omitted field. They are two representations of missing
  input, not observations of real units.
- For each packet, include the investigator prompt below and the cited local
  source passages: the [repository introduction](../../README.md#governed-nemweb-analytics-on-databricks),
  [fixed data semantics](../../nemweb_foundation/README.md),
  and [report-to-subject contract](../../nemweb_foundation/README.md).
  The `source_refs` in the JSON are repository-relative, not relative to the case.

The documented distinction is SCADA `actual_generation_mw` versus authoritative
unit target/availability from the separate daily T+1 product. The inputs contain
no authoritative availability records or evidence explaining the observations.
They are teaching representations, not an ingestion schema or parser test. No
real unit identifiers, customer data, or live observations are included. Source
references justify interpretation; they are not provenance for invented rows.

## Answer-key separation

Give the investigator only its prompt, one case, and the cited source passages,
not this full README, the test file, previous outputs, reviewer notes, or
[expected-findings.json](expected-findings.json). The facilitator/reviewer keeps
that answer key separately until the output is retained. Do not ask the
investigator to copy an answer key. The independent reviewer must check the source
passages itself, rather than treating the key as authoritative evidence. The key
is facilitator-prepared output, not a captured model answer.

## Investigator prompt

Copy this prompt into the restricted fresh session or give it to the human
investigator with one case and its cited passages:

```text
Investigate the question in this synthetic/non-live case using only the supplied
case and repository source passages. Do not use tools or request live access.
State the task kind, preparation choice, and verification rationale. Inspect each
observation without filling in absent values. Return:
1. The case ID and exact observations used, with source citations.
2. Plausible explanations and supporting/contrary evidence for each.
3. Explanations or inferences ruled out with cited evidence, separately from
   paths not investigated. Do not present lack of evidence as disproof.
4. What the evidence establishes, what remains unknown, and what would settle it.
5. Any useful refinement, defect correction, restart, or block, with a reason,
   or state that none occurred. Do not invent tool runs or operational causes.
Label the output synthetic/non-live. Return text only; the pair retains it.
```

## Reviewer prompt

Use a different person or fresh read-only assistant. Provide the exact case,
prompt, retained output, source passages, and separate expected findings:

```text
Independently check this synthetic/non-live investigation against the supplied
repository contract and input, then compare with the prepared expected findings.
Cite the input and source for each supported or unsupported conclusion. Check
whether missing evidence was treated as zero or as proof of a physical state.
Separate a ruled-out inference from an explanation that was not investigated.
Return supported findings, contradictions with location and consequence, and
remaining uncertainty; no material issue found is valid. Do not invent a defect.
For replay, compare each baseline and replay output on the original and variant.
State whether the proposed lesson helped, was unnecessary, caused a regression,
or remains untested, and recommend keep/revise/discard with a reason. Distinguish
actual agent output, actual human output, facilitator-prepared output, and not-run.
This is a read-only check: no tools, writes, live access, or replacement of the
required independent review of the pair's actual approved change.
```

## Run and retain the comparison

1. Confirm issue/plan authority, facilitator placement, and the restriction/fallback
   route. If absent, record `not-run` and defer; do not invent an issue number.
2. Run the investigator on the original and then the variant in separate fresh
   sessions, using the same baseline prompt. Do not pass an earlier answer into
   the next session. Retain each exact packet and output before review.
3. Have the independent reviewer check both baseline outputs against the contract.
   Record where any conclusion exceeded the evidence, not just a score. Structural
   review concerns the pair's actual approved code change, not an artificial defect
   in this exercise; use the separate structural-review field in the pair record.
4. Propose a short lesson only if the observed reasoning warrants one. Keep the
   exact proposed instruction in the pair record; do not edit a shared skill or
   test. A correct baseline is a valid result: record "no extra instruction needed"
   and keep the original prompt. "Do not generalise" is also legitimate when the
   observation is one-off or the evidence is insufficient.
5. Replay both the original and variant in fresh sessions with the chosen prompt
   (unchanged if no lesson is needed). Retain the revised prompt, all inputs, and
   both outputs. Use the same access and source limits. The reviewer compares
   baseline and replay for each case, including regressions; an unrun replay stays
   `not-run`, not a claimed improvement.
6. In the pair record, decide keep/revise/discard with a reason, or retain "no extra
   instruction needed" or "do not generalise". A revision needs another two-case
   replay before claiming it helped; otherwise record it as untested. Two cases
   do not establish general transfer. No participant must produce a new skill or
   meet an improvement metric.

Use this compact output inventory inside the existing pair record:

| Artefact | Retain |
| --- | --- |
| Inputs | Case IDs and exact case/source passages, prompt versions, and chosen session/fallback route |
| Original baseline and replay | Exact outputs, source citations, and reviewer result for each |
| Variant baseline and replay | Exact outputs for both missing representations, citations, and reviewer result for each |
| Output provenance | Per output: `actual agent output`, `actual human output`, or `facilitator-prepared output`; mark absent runs `not-run` |
| Learning decision | Proposed lesson or legitimate no-change outcome, keep/revise/discard reason, regressions, and remaining uncertainty |

Prepared demonstrations can use the answer key as labelled facilitator-prepared
output, but leave agent baseline and replay `not-run`. Never present it as an
observed model trajectory. Do not retain secrets or personal data in the record.

Lesson changes stay in the pair record for read-only replay. Shared-skill or test
changes outside the original approved plan require a later approved task. Do not
mutate the repository after final review; accepted defects in the actual change
return through implementation, tests, eval, and independent review. The exercise
adds no parallel lifecycle and cannot waive any gate.

## Local fixture checks

From the repository root, without workspace access or new dependencies:

```bash
python3 tests/test_agent_practice.py
```

These stdlib tests also run under pytest. They check fixture facts, non-live
labels, source references, answer-key expectations, and document integration,
including malformed teaching inputs. They do not prove agent behaviour, verified
tool restrictions, workshop timing, live operation, or successful transfer of a
lesson. Those require actual retained runs, independent source checks, and
facilitator rehearsal; none is claimed here.
