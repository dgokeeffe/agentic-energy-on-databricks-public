# Make the value-capture screen usable without colour or a mouse

**Track C · core · no Lakebase · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: app`, `accessibility`

## Operator outcome

An analyst using a screen reader, a keyboard only, or with a colour-vision deficiency
gets the same information from the value-capture screen as anyone else.

## Fits Stage 4: 60–90 minutes

This is the exercise with the shortest path from "look at it" to "found a real problem",
and it needs no market variety at all.

There is a known starting point. The capture rate originally used red and green alone to
show over- and under-performance, which fails **WCAG 1.4.1 Use of Colour**. That one was
caught and fixed with a direction symbol plus a screen-reader label. **The rest of the
screen was never audited**, and the same class of problem is likely elsewhere: the fuel
swatches are pure colour, the negative-value styling is colour-led, and the capture bars
are `div`s with a `role="img"` and a computed label.

Finding a real accessibility defect in a screen someone else already "fixed" is a
satisfying result, and it is a habit worth teaching.

**If time runs short, do the audit and fix one finding.** A documented finding list with
one repaired issue and a test is a complete result — better than four half-fixes.

## Where to start

- `nemweb_app/client/src/components/FuelValueCapture.tsx` — the swatches, the bars, the
  `role="img"` labels, the clamped axis.
- `nemweb_app/client/src/index.css` — the fuel tokens, `.capture-negative`, and the
  `prefers-reduced-motion` block that already exists for skeletons.
- `nemweb_app/tests/smoke.spec.ts` — has a dark-colour-scheme test to copy the shape of.
- `nemweb_app/client/src/components/RegionalOperationsShell.test.tsx`.

## Required change

- Audit the screen and **write down every finding**, including ones you do not fix.
- Fix at least one, with a test that fails before and passes after.
- Candidate areas: keyboard reachability of the region control and the journal trigger;
  focus visibility against the warm-neutral palette; whether the capture bars convey
  their value to a screen reader without the visual; whether any remaining state is
  colour-only; contrast of the mid-grey secondary text on the warm background.

Report contrast ratios as measured numbers against the WCAG threshold you are citing.
"Looks fine" is not a finding, and neither is "improved contrast" without a ratio.

## 30-minute checkpoint

A written finding list with at least three items, each naming the WCAG criterion it
relates to. Fixing is the second half.

## Deterministic tests

- the fix has a test that **fails before it and passes after** — demonstrate both;
- every interactive control is reachable and operable by keyboard, and focus is visible;
- no state is conveyed by colour alone;
- the existing dark-colour-scheme smoke test still passes — the light palette is
  deliberate and must not regress;
- the mobile layout still has no horizontal overflow at 375px, which the existing smoke
  test already asserts;
- measured contrast ratios are recorded for any text you changed.

## Agentic eval

Did the agent measure contrast or estimate it? Ask for the numbers. Did it demonstrate
the failing test before the fix, or only assert the fix works? Did it list findings it
chose not to fix, or silently narrow the audit to what it repaired?

## Evidence required

Approved plan, the finding list with WCAG criteria, changed files, the failing-then-passing
test output, measured contrast ratios, and before/after screenshots.

## Limits

No change to the governed figures or their semantics — this is presentation only. Do not
weaken the existing smoke tests to accommodate a change. The light-only palette is a
recorded decision; do not add a dark theme as an accessibility fix.
