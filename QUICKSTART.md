# Workshop quickstart

Pick one track. Complete it end to end. No track depends on another track, on a
partner, or on a clock.

Work at your own pace. Each track is a numbered sequence of stages; finish the
current stage and record the decision before opening the next.

## Before you choose

```bash
git status --short
make validate-local
```

Both should succeed before you start. If `make validate-local` fails, tell the
facilitator rather than working around it.

## Choose your track

| Track | Choose this if you want to… | Start here |
| **A — Governed answer** | Turn an operator question into an explainable answer that cites its source and freshness, and that refuses an unsafe question. Metric views, Genie, dashboards. | [`lane_a_business/Instructions.md`](lane_a_business/Instructions.md) |
| **B — Production fix** | Repair a seeded data defect with a failing test, then prove that both deterministic tests and an agentic evaluation can reject weak work. | [`lane_b_engineering/Instructions.md`](lane_b_engineering/Instructions.md) |
| **C — App and Lakebase** | Build on the operations app and its writable Postgres state, with your own isolated Lakebase branch and your own deployed app. | [`workshop/track_c_app/Instructions.md`](workshop/track_c_app/Instructions.md) |

Not sure? Track A suits analysts and anyone who works with stakeholders. Track B
suits engineers who want the test-and-review loop. Track C suits people who want
to ship a running application.

You may pair with someone if you prefer, on the same track. Nothing requires it.

## What every track shares

All three read from one governed NEMWEB foundation. Do not build a second data
store.

Fixed contracts, in every track:

- NEM market timestamps are interval-ending **fixed AEST** (UTC+10, no daylight
  saving). Processing timestamps are timezone-aware **UTC**.
- Bronze keeps source corrections; Silver selects the latest valid correction.
- Gold keeps both intervention rows; ordinary analysis uses `is_effective_run`.
- `actual_generation_mw` is SCADA **output**, not availability. Authoritative
  target and availability come from the daily T+1 product.
- Snapshot and prepared fixtures are **non-live evidence**. Never describe them
  as live.

## Limits

You may inspect [`nemweb_foundation/`](nemweb_foundation/README.md), the app, the
ML starter and the Lakebase contracts, and run local tests and read-only
validation.

Without explicit facilitator release, do not deploy the foundation bundle, run
Databricks jobs, change grants, enable live NEMWEB, change schedules, or merge.

Track C is the exception, and only for its own resources: attendees on Track C
deploy their own app against their own Lakebase branch. See
[`miniwiki/decisions/attendee-isolation.md`](miniwiki/decisions/attendee-isolation.md).

Never put credentials, tokens, private workspace URLs, or tenant identifiers into
Git, a prompt, a log, or a screenshot.

If a platform capability is unavailable, record the step as `not-run` or
`blocked` and continue with local work. An unrun platform step never becomes a
pass because a fixture produced output.

## Using an AI assistant

Start a **fresh conversation** for each numbered stage. Carry facts forward
through the files, the track record, and command output — not through chat
history. An assistant's summary is a claim; the command, exit code, and diff are
the evidence.
