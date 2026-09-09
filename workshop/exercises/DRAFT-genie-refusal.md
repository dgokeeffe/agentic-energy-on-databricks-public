# Make Genie refuse the questions it should not answer

**Track A · core · no Lakebase · Visible today: yes**

Labels: `workshop`, `workshop-ticket`, `difficulty: core`, `area: genie`

## Operator outcome

An analyst asking Genie something the data cannot support gets a clear refusal that
names the reason, instead of a confident answer built on an inference nobody governed.

## Fits a 60–90 minute slot

This is the most immediately entertaining exercise here, because **you try to break
it**. You write questions designed to trick the space into overclaiming, watch which
ones succeed, then close the gaps.

**If time runs short, cut the near-miss pairs.** Three must-refuse questions, each
citing a real contract rule, with the test asserting they exist, is a complete result.

It needs no market variety at all — a refusal is about what the data *cannot* say, and
two intervals of one region cannot say plenty.

The richest target is real. `gold_nem_scada_generation_5min` is actual SCADA output,
and AEMO Current publishes **no five-minute availability**. So any question of the form
"how much was curtailed", "what could that unit have produced", or "why was output
below capacity" is unanswerable from this data — and is exactly what an informed energy
person asks first. The Track C app states this denial on screen. Genie should too.

## Where to start

- `nemweb_foundation/genie/benchmark_questions.json` — existing benchmark set.
- `nemweb_foundation/genie/nemweb_space.json` — the space definition and its
  instructions.
- `nemweb_foundation/tests/nemweb/test_genie_assets.py` — the deterministic checks.
- `nemweb_foundation/DATA-CONTRACT.md` — the authoritative list of what must not be
  inferred, including the SCADA-versus-availability rule and market-notice omission.

## Required change

Strengthen the refusal side of the benchmark.

- Add questions that **must be refused**, each paired with the contract rule that
  makes it unanswerable. At minimum: five-minute availability or curtailment; summing
  market-wide constraint or interconnector values across regions; inferring
  interconnector flow direction without a governed region mapping; treating a snapshot
  figure as live.
- Add near-miss pairs: one answerable question and one superficially similar
  unanswerable one, so the space is not simply refusing on keywords.
- Extend the space instructions so a refusal **names its reason**, not just declines.
- Extend the tests to assert refusals are present and attributed to a rule.

A refusal that says "I cannot answer that" is worth little. One that says "AEMO Current
does not publish five-minute availability, so withheld output cannot be quantified" is
worth a lot.

## 30-minute checkpoint

At least three must-refuse questions with their contract rules quoted, and the test
asserting they exist. If you are not there by 30 minutes, stop adding questions and make
the three you have cite their rules correctly — a question citing an invented rule is
worse than no question.

## Deterministic tests

- every must-refuse question cites a contract rule that exists in
  `DATA-CONTRACT.md` — verified by matching text, not by a human reading it;
- every answerable question still resolves against governed Gold or a metric view;
- near-miss pairs are both present, and the answerable one is not accidentally listed
  as must-refuse;
- no benchmark question depends on a table with no rows in the snapshot — check first,
  because `bids`, `trading` and `settlement` are all empty;
- the existing `test_genie_assets.py` assertions still pass unchanged.

## Agentic eval

Did the agent read `DATA-CONTRACT.md` and cite real rules, or invent plausible-sounding
ones? Check each cited rule actually appears in the contract. Did it add near-misses,
or only easy refusals a keyword filter would catch? Ask it which of its questions it
expects to be hardest to refuse correctly, and why.

## Evidence required

Approved plan, changed files, test output, and — if a facilitator authorises executing
against the space — the actual response to each must-refuse question, marked as
non-live evidence. Text-only validation is a legitimate outcome; say so rather than
implying the space was exercised.

## Limits

No new Gold table, no relaxing of a contract rule to make a question answerable, no
claim that a snapshot answer is live. Executing against a deployed space consumes
compute and needs facilitator authorisation; validating the JSON and tests locally does
not.
