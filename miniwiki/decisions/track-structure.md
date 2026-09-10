# Self-contained tracks and no fixed clock

## Decision

Two decisions, taken together on 2026-09-07.

**One: each track is self-contained.** An attendee picks one track and completes
it without needing a partner in another track. `QUICKSTART.md` is a chooser that
routes to exactly one track. The previous model — cross-track pairs sharing one
GitHub issue, with Track A consuming Track B's evidence and vice versa — is
withdrawn.

**Two: there is no fixed clock.** Tracks keep their numbered stage order and
drop every wall-clock time and card number. Stages are self-paced.

## Why

The repository previously carried two competing participant paths at once. A
`QUICKSTART.md` described a shared GitHub-issue lifecycle with cross-track pairs.
`lane_a_business/Instructions.md` and
`lane_b_engineering/Instructions.md` described self-contained numbered-prompt
tracks on a fixed clock. The deleted run-of-show asserted that the lane
directories were "historical material and are not routed", while both lane
navigators actively routed to them. An attendee reading in good faith got
contradictory instructions about what to do and who to do it with.

Self-contained tracks remove the coordination failure. Cross-track pairing meant
an attendee could be blocked by a partner who was slower, absent, or working on a
different concern. It also required a shared pair record, a shared clock, and a
simultaneous evidence exchange — three synchronisation points, each of which
could strand someone.

The clock went for a simpler reason: the only clock source was deleted, and both
tracks still quoted exact times from it ("Cards 1–5, 10:03–12:00"). Re-deriving
those times would recreate a document that must stay in sync with two others and
that breaks the moment a session starts late. Stage order carries the pedagogy;
the wall time did not.

## What replaced what

| Withdrawn | Replacement |
| Cross-track pair with two owners | One attendee (or a self-chosen pair) completing one track |
| Shared `workshop-pair-record.md` | A record per track, held inside the track directory |
| `workshop-run-of-show.md` as sole clock | Stage order inside each track; no times |
| Simultaneous evidence exchange at a fixed time | Nothing. Tracks do not depend on each other. |
| `workshop-playbook.md` as the routed path | `QUICKSTART.md` chooser plus each track's `Instructions.md` |

## What this does not change

- The stage sequence inside each track, and the requirement that a human decision
  is recorded before the next stage opens.
- The fixed data contracts: interval-ending fixed AEST market time, UTC
  processing instants, correction order, `is_effective_run` defaults, SCADA
  output versus availability.
- Evidence labelling. Snapshot and prepared material remain non-live.
- The stop conditions in each track.
- Facilitator control of deployment and workspace operations, except where the
  separate isolation decision in
  [`attendee-isolation.md`](attendee-isolation.md) grants an attendee their own
  Lakebase branch and App.

## Cost accepted

Self-contained tracks lose the cross-role conversation that pairing was meant to
force. An analyst no longer has to obtain timezone evidence from an engineer.
That was the pedagogical point of the pairing model, and dropping it is a real
loss, accepted because the coordination cost and the contradictory routing were
worse. Attendees who want the conversation can still pair by choice; nothing
prevents it, and no document requires it.
