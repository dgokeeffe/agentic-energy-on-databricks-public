# Track record

Copy this file for your own work, for example to `my-track-record.md`, and keep
it beside you as you go. It is your evidence trail.

Do not record credentials, tokens, private workspace URLs, tenant identifiers, or
anyone's personal data.

| Field | Record |
| Track (A, B, or C) | |
| Your name | |
| Attendee slug (Track C only) | |
| Date | |

## Per stage

Repeat this block for each numbered stage you complete.

| Field | Record |
| Stage number and name | |
| What you set out to prove | |
| Exact commands run | |
| Exit codes | |
| Result, in one sentence | |
| Evidence label: **live**, **snapshot**, or **prepared** | |
| Files changed | |
| What you could not verify | |
| Human decision: accept, send back, reject, or stop | |
| Who decided | |

## Learning fields

Complete these once, at the end. They separate what you proved from what you
assumed, and they are the part most often skipped.

| Field | Record |
| Task kind, preparation choice, and verification rationale | |
| Explanations ruled out with cited evidence, versus paths not investigated | |
| Refinement, defect correction, restart, or block, with a short reason when relevant | |
| Structural-review result, location, consequence, and remaining uncertainty | |
| Proposed lesson or "do not generalise"; original and second-case inputs/results; keep/revise/discard decision | |

Cite evidence for explanations ruled out; an uninvestigated path is not
disproven. For the structural result, "no material issue found" or "not
applicable" with a reason is valid. "No extra instruction needed" and "do not
generalise" are legitimate outcomes; there is no required lesson per attendee.

Label each result `actual agent output`, `actual human output`, or
`facilitator-prepared output`. Mark unrun steps `not-run`. Retain the exact
original and second-case inputs, prompt versions, baseline and replay outputs,
source citations, and any independent check. Facilitator-prepared output is not
proof that an agent ran.

An optional read-only replay needs an approved plan, plus facilitator placement
and rehearsal. It never replaces a required check, and any shared-skill or test
change beyond the plan is a later approved task.

## Close

| Field | Record |
| What the track produced | |
| What would need to be true to trust it in production | |
| Remaining uncertainty | |
| Steps recorded `not-run` or `blocked`, and why | |

## Rules for this record

- An assistant's summary is a claim. The command, exit code, output, and diff are
  the evidence. Record the evidence.
- Label every result **live**, **snapshot**, or **prepared**. Snapshot and
  prepared material are never live proof.
- A step that did not run is `not-run` or `blocked`. It never becomes a pass
  because a fixture produced plausible output.
- If you weakened, skipped, or deleted a check to get a pass, that is the finding.
  Record it rather than hiding it.
- A reviewer other than the author gives the verdict. Prepared fallbacks do not
  reduce that floor.
- Do not mutate the repository after final review. An accepted repair returns
  through implementation and the affected gates.
- Keep lesson instructions here for read-only replay. A shared-skill or test
  change beyond the approved plan needs a later approved task.
- A person accepts, sends back, rejects, or stops. Record which.
