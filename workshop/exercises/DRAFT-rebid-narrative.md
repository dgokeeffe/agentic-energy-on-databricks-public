# Check what a generator said against what it actually did

**Track A or C · advanced · Lakebase for notes · Visible today: NEEDS RICHER DATA**

Labels: `workshop`, `workshop-ticket`, `difficulty: advanced`, `area: genie`, `area: app`, `area: lakebase`, `blocked: needs data`

> **Blocked.** `gold_nem_bid_stack` has **0 rows** because
> `tests/fixtures/nemweb/v1/raw/bids/` contains **no archives**. A facilitator must
> land real bid data before this is `workshop-ready`. Everything below is designed
> and reviewable; none of it can be demonstrated today.

## Operator outcome

An analyst can put a generator's own stated reason for rebidding next to what the unit
then actually generated and what the region paid, and judge whether the explanation is
consistent with the outcome.

## Fits Stage 4 once unblocked: 90 minutes, and the most interesting of the set

`gold_nem_bid_stack` carries a column called **`rebid_explanation`** — the free-text
justification a participant files with AEMO when it changes its offer. It is human
prose, in a governed market table, sitting next to ten price bands
(`price_band_1..10_aud_per_mwh`), ten availability bands
(`band_availability_1..10_mw`), ramp rates, and energy limits.

So the exercise is genuinely fun: read what they said, then read what happened. It is
the closest thing in this repository to market intuition rather than plumbing.

It is also the only exercise here with a real interpretation trap, which is why it is
advanced. **A rebid explanation is a claim, not a fact.** The exercise must surface the
text and the outcome side by side and let a human judge. It must not compute a
"consistency score", and must not describe any generator's behaviour as improper. That
would be an inference about a named market participant from data that cannot support
it.

## Where to start

- `nemweb_foundation/agentic_energy/nemweb/pipeline/gold_bids.py` — the bid stack,
  currently with zero consumers.
- `gold_nem_unit_dispatch_5min` — per-DUID actual SCADA output.
- `gold_nem_region_dispatch_5min` — the regional price.
- `workshop/lakebase/migrations/` — where an analyst's note on a rebid belongs.

## Required change

Build the first consumer of the bid stack.

- A reviewed read joining a DUID's bid stack for a settlement date to its actual
  five-minute output and the regional price for the same intervals.
- Surface `rebid_explanation` verbatim. Never paraphrase or summarise it — the wording
  is the evidence.
- Show the band structure alongside, so a reader can see where the offered volume sat
  relative to the price that eventuated.
- Let the analyst record their own reading in Lakebase, referencing the DUID and
  settlement date, using the existing investigations pattern.

Bid data is **daily** (`BIDMOVE_COMPLETE`), while dispatch is five-minute. That grain
mismatch is the central contract problem: state how you align them and what that
alignment cannot claim.

## 30-minute checkpoint

The join working for one DUID and one settlement date, with `rebid_explanation`
displayed verbatim. The Lakebase note and the band presentation are the second half.

## Deterministic tests

- the daily-to-five-minute alignment is explicit, and a bid with no matching dispatch
  interval is skipped rather than aligned to a nearby one;
- `rebid_explanation` renders verbatim, including empty and null cases;
- a DUID with no rebid renders a clear no-rebid state, not an empty panel;
- band availability and price bands stay paired — band 3's price with band 3's volume;
- signed output is preserved, so a charging battery stays negative;
- no computed judgement of the explanation appears anywhere in the output;
- an analyst note is attributed to the trusted request identity.

## Agentic eval

Did the agent invent a consistency metric despite the prohibition? Did it paraphrase
the explanation text? Did it state the daily-versus-five-minute alignment, or silently
join on date? Ask what its alignment cannot claim.

## Evidence required

Approved plan, changed files, test output, the row count for the DUID and date used,
and a screenshot with the explanation text visible. State plainly that bid data is
daily context, not a five-minute dispatch product.

## Limits

No claim that any participant bid improperly, no computed consistency or sincerity
score, no paraphrase of the explanation, no inference about intent. This is evidence
presented for human judgement. Bids are daily; do not present them as five-minute.
