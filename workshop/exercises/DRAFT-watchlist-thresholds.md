# Let an analyst set their own alert threshold, and have it stick

**Track C · core · Lakebase central · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`, `area: lakebase`

## Operator outcome

An analyst sets the price and capture-rate thresholds that matter to them, and those
thresholds persist across sessions and are attributed to them. Two analysts on the
same market data can watch for different things.

## Fits Stage 4: 60–90 minutes

Every threshold in the app is currently hard-coded. `SOURCE_STALE_AFTER_MS` is a
constant in `domain/regionStatus.ts`; the value-capture axis clamp is a constant in
`FuelValueCapture.tsx`. Nothing is user-owned, so the app has no per-analyst state at
all — which is odd for an app with a Postgres database attached.

The payoff is immediate and tactile: set a threshold, reload, it is still there, and
the screen reacts. It needs no market variety, because you choose the threshold that
makes the current data interesting.

**If time runs short, do one threshold, not both.** The capture-rate floor is the more
visible of the two. One persisted, validated, applied threshold is a complete result.

## Where to start

- `nemweb_app/client/src/domain/regionStatus.ts` — `SOURCE_STALE_AFTER_MS`, the
  15-minute constant.
- `nemweb_app/client/src/components/FuelValueCapture.tsx` — `AXIS_MAX`, the 2.00×
  clamp.
- `workshop/lakebase/migrations/` — where a `watchlist` table belongs, alongside
  `investigations`.

## Required change

Persist per-analyst thresholds in Lakebase and apply them.

- A migration creating a thresholds table in `app_write`, keyed on the trusted
  identity, with sensible defaults so a first-time analyst sees today's behaviour.
- Read/write functions alongside the existing investigation queries.
- The screen applies the analyst's thresholds: a capture rate below their floor is
  flagged, and their staleness window drives the existing stale banner.
- A control to change them, with the value validated server-side.

Keep the current behaviour as the default. An analyst who sets nothing must see
exactly what they see today, so the change is additive.

## 30-minute checkpoint

One threshold saved to Postgres and read back on reload. If you are not there by 30
minutes, drop the second threshold and the settings control, and hard-code the write
while you get the read path and its application working.

## Deterministic tests

- a first-time analyst gets the documented defaults, and today's rendering is
  unchanged;
- a saved threshold is read back for that identity and not for another;
- an out-of-range or non-numeric threshold is rejected server-side, not only in the
  browser;
- a capture rate exactly on the threshold boundary resolves the documented way —
  state whether the comparison is strict, and test both sides;
- thresholds are keyed on the trusted request identity, and a request cannot set
  another analyst's threshold;
- existing capture semantics are untouched, including the three cases where the rate
  is withheld rather than shown.

## Agentic eval

Did the agent validate server-side, or only in the component? Did it pick a boundary
convention and test both sides, or leave the on-threshold case undefined? Did it
preserve the default so the change is additive? Ask which existing constant it
replaced and whether anything else still reads it.

## Evidence required

Approved plan, the migration, changed files, test output including the boundary cases,
and a screenshot of the same market data rendered under two different thresholds.

## Limits

Your own Lakebase branch. No shared configuration table, no threshold applied to
another analyst's session, no change to the governed Gold semantics. A threshold
changes what is *highlighted*, never what the underlying figure *is*.
