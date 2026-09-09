# Break up a 485-line component without changing what it renders

**Track C · core · frontend · no Lakebase · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`

## Operator outcome

The value-capture screen renders exactly as it does now, but the next person changing
one section does not have to read the whole file to be sure they broke nothing.

## Fits Stage 4: 60–90 minutes

`RegionalOperationsShell.tsx` is **485 lines** and holds at least six responsibilities:
region selection, capture computation, restatement arithmetic, KPI presentation, the
observation table, and journal sheet wiring. It has six `useMemo`/`useState` hooks in
one function.

There is also a genuine leak. This is inline in the component:

```tsx
row.actualGenerationMw * (5 / 60) * (priceByInterval.get(row.intervalEnd) ?? 0)
```

That `5 / 60` is the five-minute interval-to-hours conversion, and it already exists as
`INTERVAL_HOURS` in `domain/fuelCapture.ts`. So the same market semantics are encoded
twice, in two languages of the codebase — a component and a domain module. That is the
identical shape as the pipeline defect this workshop's demonstration is built around,
and it is sitting in the app today.

The satisfaction here is different from the other exercises: **you must change a lot of
code and prove the output is byte-identical.** That is a real professional skill, and the
existing test suite makes it verifiable.

**If time runs short, extract one section and the arithmetic leak.** Moving
`restatedRevenueAud` into the domain module with a test is a complete result on its own.

## Where to start

- `nemweb_app/client/src/components/RegionalOperationsShell.tsx` — the 485 lines.
- `nemweb_app/client/src/domain/fuelCapture.ts` — where `INTERVAL_HOURS` already lives.
- `nemweb_app/client/src/components/RegionalOperationsShell.test.tsx` — 263 lines of
  existing assertions. Your safety net; do not weaken it.

## Required change

- Move the restatement arithmetic into the domain module as a pure, tested function.
  Use `INTERVAL_HOURS`; delete the inline `5 / 60`.
- Extract at least two presentational sections into their own components — the KPI grid
  and the observation table are the obvious candidates.
- Keep every hook in a valid order. The current file already has a subtle constraint:
  hooks run before an early return precisely so the order stays stable. Preserve it.
- **The rendered output must not change.** No visual change, no copy change, no changed
  test expectation.

If you find a second duplicated market constant while doing this, extract that too and
say so.

## 30-minute checkpoint

Restatement arithmetic moved to the domain module with its own test, `5 / 60` gone, and
the existing suite still passing untouched. Component extraction is the second half.

## Deterministic tests

- **every existing assertion in `RegionalOperationsShell.test.tsx` passes unmodified** —
  if you changed a test, you changed behaviour;
- the extracted restatement function has direct unit tests, including zero restated
  intervals and a restated interval with negative price;
- no component imports a hard-coded interval-length constant;
- hooks are called unconditionally before any early return, and the component renders
  for the empty, error and loading states;
- the 3 Playwright smoke tests pass, including the dark-colour-scheme guard;
- `eslint` passes, including the `react-hooks` rules that already caught a purity bug in
  this file.

## Agentic eval

Did the agent modify a test to make a refactor pass? That is the failure mode here, and
it is disqualifying — ask it to show `git diff` on the test file and justify any line.
Did it find the `5 / 60` duplication, or only split files? Ask whether it checked for
other duplicated constants.

## Evidence required

Approved plan, changed files, the **unmodified** test file diff (ideally empty), test and
lint output, and a before/after screenshot pair that a reviewer cannot tell apart.

## Limits

No visual or copy change. No test expectation changed. No new dependency. No change to
capture or restatement semantics — this is structure only. If you believe a semantic
change is needed, stop and report it rather than folding it in.
