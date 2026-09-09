# Make the app honest when the warehouse is slow, broken, or half-answering

**Track C · core · frontend · no Lakebase · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`

## Operator outcome

An analyst can always tell which of four situations they are in: data is loading, data
is current, data is stale, or data is unavailable. They never read a number without
knowing which.

## Fits Stage 4: 60 minutes

The app already has a `QueryState` union and a skeleton, so the scaffolding exists. What
it does not have is honest handling of **partial** failure, and that is the common case
in production.

There is a real example already in the code. The fuel read can fail independently of the
price read, and the screen degrades to a badge and a banner:

```
Generation read unavailable
The generation read is unavailable, so no fuel-level capture is shown.
```

That path works. But the app has **two** analytics queries and **one** shared error
state, so a reviewer cannot easily tell which failures are handled well and which blank
the page. Meanwhile `state.partial` exists in the domain type and drives only one
banner, and `predictionStale` is reported separately again.

The payoff is fast and very visible: you deliberately break things and watch the screen
tell the truth.

**If time runs short, do the loading and one failure case properly.** A skeleton that
matches the real layout plus one honest partial-failure state beats four half-states.

## Where to start

- `nemweb_app/client/src/components/QueryState.tsx` — the skeleton and error rendering.
- `nemweb_app/client/src/domain/regionStatus.ts` — the `QueryState` union, `stale`,
  `partial`, `predictionStale`, and the `fuelRows: … | null` degraded case.
- `nemweb_app/client/src/App.tsx` — where both `useAnalyticsQuery` calls live, including
  the warehouse-status branch.
- `nemweb_app/client/src/components/RegionalOperationsShell.tsx` — the banner block.

## Required change

Enumerate the states this screen can actually be in, then make each one unambiguous.

- A loading skeleton whose shape matches the real layout, so the page does not jump.
- Distinct, honest handling for: warehouse not running; price read failed; generation
  read failed; both succeeded but prediction fields missing; data present but stale.
- Every state that shows numbers must show its freshness. Every state that hides numbers
  must say why.
- A retry affordance where retrying could plausibly help, and none where it cannot.

Keep the existing distinction where staleness is an alarm in integration mode and a
plain statement against a prepared fixture — that is deliberate, and there is a test
asserting it.

## 30-minute checkpoint

A written list of every reachable state with what the screen should show for each, and
the loading skeleton matching the layout. Implementing the rest is the second half.

## Deterministic tests

- each enumerated state renders its own distinguishable output;
- a failed generation read still shows governed price and freshness — assert both;
- a failed price read does not silently render a zeroed or empty capture section;
- staleness remains an alert in integration mode and a non-alarm statement in mock mode,
  and the "Do not treat these values as current" instruction survives in both;
- the skeleton respects `prefers-reduced-motion`, which `index.css` already handles for
  the shimmer;
- no state renders a number without an accompanying freshness indication.

## Agentic eval

Did the agent enumerate states from the type union and the two query call sites, or guess
from the component? Ask for the list, and for which states it could not reach in a test
and why. A state nobody can reach in a test is a state nobody has verified.

## Evidence required

Approved plan with the state list, changed files, test output, and a screenshot per
state. Say plainly which states you simulated versus genuinely triggered.

## Limits

No fabricated data to fill a gap. No hiding a failure behind a plausible-looking empty
result. No removal of the existing staleness distinction or the "not current"
instruction. Presentation only — no change to governed figures.
