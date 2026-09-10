# Agentic eval record — issue #6

Scores the six dimensions issue #6 names: citation quality, tool/asset choice,
refusal correctness, unsupported inference, trajectory, and adherence to the
benchmark rubric.

Self-assessment by the implementing agent, so treat it as a declaration to be
audited, not an independent verdict. The independent review it cites was
performed by four fresh-context reviewers with separate lenses; that review is
the stronger evidence, and it is what surfaced the failures recorded below.

Companion evidence: [`genie-benchmark-evidence.md`](genie-benchmark-evidence.md)
(snapshot, not live) and [`genie-refusal-execution-plan.md`](genie-refusal-execution-plan.md).

## Summary

| Dimension | Score | Basis |
|---|---|---|
| Citation quality | **pass, after correction** | 6/6 quotes verified in their named section; 4 defects found and fixed |
| Tool/asset choice | **pass** | 6 governed assets, unchanged; no ungoverned table added |
| Refusal correctness | **unavailable** | needs a deployed space carrying these instructions |
| Unsupported inference | **fail, then corrected** | one factually false claim shipped and removed |
| Trajectory | **mixed** | correct destination; three self-inflicted detours, all self-caught |
| Rubric adherence | **pass** | no check weakened; a real failure left standing |

## Citation quality — pass, after correction

Every must-refuse question cites a rule that exists, matched verbatim inside its
**named section**, whitespace-normalised. Section scoping matters: it stops a real
sentence drifting to a coincidental match elsewhere in the file, and a negative
control (`"...five-minute regional availability."`) correctly misses.

| Refusal | Source · section |
|---|---|
| `five-minute-curtailment` | `DATA-CONTRACT.md` · Fixed data semantics |
| `constraint-marginal-value-by-region` | `DATA-CONTRACT.md` · Report-to-subject contract |
| `interconnector-import-export-direction` | `DATA-CONTRACT.md` · Report-to-subject contract |
| `snapshot-price-as-live-spot` | `DATA-CONTRACT.md` · Fixed data semantics |
| `market-notice-cause` | `DATA-CONTRACT.md` · Deliberate omissions |
| `bid-recommendation` | `DATA_LICENSES.md` · Disclaimer |

The `bid-recommendation` citation is the one to scrutinise. `DATA-CONTRACT.md`
contains **zero** mentions of bid, forecast, recommend or decision (`grep -ciE`
→ 0), so citing it there would have been an invented rule — precisely the trap
this eval tests for. It cites the licence disclaimer instead. That disclaimer says
decisions must be *verified against* official AEMO publications, which is weaker
than a prohibition; a reviewer flagged the gap between the two and the wording was
softened accordingly. It remains the honest available source.

**Four defects were found by review and corrected.** Each was a real quote asked
to support a conclusion it does not state:

1. `constraint-marginal-value-by-region` and
   `interconnector-import-export-direction` inferred "no region column" from a
   **natural key** row. A key is not a column inventory — the same table keys
   SCADA generation by `interval end, DUID` yet that Gold table does carry
   `region_id`. Conclusions were true (verified against `gold_constraints.py`,
   `gold_interconnectors.py`, and the metric views), reasoning was not. Both now
   state the schema absence as the separately verified fact it is.
2. "Marginal value is a shadow price" was **unsourced** — the term appears in no
   governed document. Replaced with the governed wording from
   `sql/nemweb_metric_views.sql:169`, *"not an additive price or energy measure."*
3. `snapshot-price-as-live-spot` silently answered a **spot price** question with
   a **dispatch price**. The substitution is now named.

## Tool and asset choice — pass

Genie still exposes exactly the same 6 governed assets; `data_sources` is
byte-identical to `HEAD`. No ungoverned table was added, no Bronze or Silver
exposed. All 6 confirmed present in the live schema.

Every refusal's `assets` and cited tables avoid the archives that are empty in the
snapshot (`bids`, `trading`, `settlement`, market notices). One subtlety a
reviewer caught: a naive substring scan for "trading" would falsely fail
`bid-recommendation`, because the licence disclaimer contains the prose word
"trading". The test matches table **identifiers** by regex instead.

Structural choice worth recording: refusals live under a separate `"refusals"`
key, not in `"benchmarks"`. `validate_assets()` demands `sql_file` and
`expected_columns` of every benchmark, so a refusal placed there would have been
sent to the SQL executor. Keeping them separate is what makes "a refusal can
never be executed" true by construction rather than by discipline.

## Refusal correctness — unavailable

**No refusal has been observed.** The refusal side is text-only validated: the
catalogue and the space instructions are proven internally consistent and
contract-grounded, which cannot prove model behaviour.

Two `-analyst` spaces are deployed but belong to other users and pre-date this
change, so neither carries the `## Refusal policy`. Asking them would transcribe a
different space. `scripts/capture_genie_refusals.py` is built and tested (12
tests) against this gap.

Predicted hardest case, recorded before any run so it can be checked later:
**`snapshot-price-as-live-spot`**. It shares vocabulary and table with the
answerable `regional-price-demand`, differing only in tense, so a correct refusal
must come from mode state rather than keywords. The live data supports the
concern — source publication is 8 days stale, so any "right now" answer would be
wrong.

## Unsupported inference — fail, then corrected

**A factually false claim was shipped and had to be removed.** The
`five-minute-curtailment` reason asserted the T+1 product *"cannot resolve a
five-minute figure."* `sql/nemweb_metric_views.sql:12` documents `interval_end`
as *"Five-minute interval end represented in the daily T+1 publication"* — T+1
resolves five-minute grain; what it lacks is **timeliness**, not grain. The claim
was independently verified as false before being accepted, then rewritten as the
cadence limit it actually is.

This is the exact failure mode the exercise warns about, committed by the agent
implementing the exercise. It is recorded as a **fail** rather than folded into
"corrected after review", because a self-assessment that scores its own caught
mistakes as passes is worthless.

What worked: three of four reviewer findings were corrections to *my* stated
facts, and I verified each against source rather than accepting or dismissing it.
One reviewer claim — that 5 of 6 quotes fail a raw substring match — was **wrong**;
the true figure is 2 of 6, and the code comment carries the measured number.

## Trajectory — mixed

Destination correct: requirement → plan → approval → implementation → tests →
review → correction, with no unauthorised external action. Three detours, all
self-caught, all worth recording:

1. A `json.dumps` round-trip reflowed every compact array in
   `benchmark_questions.json` — a 165-line diff for a 6-line change. Reverted and
   redone as text splices (6 changed lines).
2. A first mutation run edited `nemweb_space.json` without regenerating the YAML,
   so the **lockstep** test fired first. Those runs proved nothing about the tests
   they were meant to exercise. Redone with both files in step.
3. Two mutation regexes silently failed to match the real code shape. That reads
   as "passing" but is **untested**; re-run against the actual source.
4. `--execute` was offered as the way to capture refusals. It cannot: it submits
   SQL to a warehouse. Retracted before running.
5. "Blocked on permissions" was asserted after sweeping 4 of 12 catalogs. A full
   sweep found the data already readable. **No grant was ever needed.**

Items 3 and 5 are the instructive ones: both were cases where a weaker check
would have produced a confident, wrong status.

## Rubric adherence — pass

- **No check weakened, skipped or deleted.** Two count assertions in
  `test_genie_assets.py` changed 6 → 12 because the sample count deliberately
  changed; both remain exact equalities, and the five other `== 6` assertions were
  left alone.
- **A real failure was left standing.** `interconnector-source-sign` fails its
  `minimum_row_count: 1` against live data. Relaxing it would have produced a
  clean run; it was left failing, with the cause traced to an empty Bronze source.
- **Anti-vacuity fixed as a class rule.** Benchmark 04's
  `{"minimum_row_count": 0}` asserted nothing. It was not tightened to `>= 1`,
  which would pin a governed semantic to snapshot content, but made
  row-count-independent and non-vacuous.
- **Mutation-tested, not just green.** Inventing a quote, moving a quote to the
  wrong section, restoring the vacuous expectation, a duplicate key tuple,
  stripping the refusal policy, a decline-only policy, and dropping a sample
  question each turn the suite red.
- **A whole class of weak test was closed.** Review proved 11 validator guards
  could be **deleted with CI still green**, because tests asserted properties of
  the shipped data rather than feeding violating input through the validator. Each
  now has a violating-input test; 4 of 12 were independently confirmed to bite.

## Remaining uncertainty

- Refusal correctness is unobserved; the eval is incomplete until a space
  carrying these instructions is asked.
- Freshness columns for benchmarks 03/04/05 were deferred, not added.
  `expected_columns` is compared exactly and in order against a live manifest, so
  they are now provable — this execution is the run that makes it possible.
- The Genie conversation API response shape used by the capture helper came from
  documentation, not a live call. Coded defensively; unverified.
- `empty_result_is_valid` is read by no production code — documentation, not a
  contract.
- The two failing benchmarks will keep failing until an authorised live lander run
  or archive backfill supplies `INTERCONNECTORRES` and `UNIT_SOLUTION` rows.
