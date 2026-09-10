# Executing the Genie refusal benchmarks — prepared, not run

Status: **prepared. Nothing in this page has been run.** No workspace was
contacted while writing it. Treat every command here as requiring explicit
facilitator authorisation at the moment of use.

Companion to the refusal set added in `nemweb_foundation/genie/benchmark_questions.json`
(`"refusals"`, schema `version` 2) and the `## Refusal policy` block in
`nemweb_foundation/genie/nemweb_space.json`.

## Correction: `--execute` does not test refusals

`validate_nemweb_genie.py --execute` iterates `assets["benchmarks"]` and
`assets["dashboard_sql"]` only. Refusals appear in one summary `print()` and
nowhere else. That is deliberate: a refusal carries no `sql_file`,
`expected_columns` or `result_expectation`, and `test_benchmarks.py` asserts
both the structural absence and that `main()`'s `--execute` region never
references `refusals`.

So `--execute` submits **SQL to a SQL warehouse**. It cannot produce a refusal,
because a refusal is a **natural-language response from the Genie space**. The
two are different mechanisms:

| Want to prove | Mechanism | Exists in repo today |
|---|---|---|
| Supported benchmark SQL still resolves | SQL Statement Execution API, via `--execute` | yes |
| Genie refuses an unanswerable question and names its reason | Genie conversation API | **no tooling** |

Anyone reading "executed the benchmarks" as "saw Genie refuse" would be
misreading the evidence. Keep the two claims separate.

## Step 1 — supported side (existing tooling, still needs authorisation)

Consumes warehouse compute. Requires a deployed space and a running warehouse.

```bash
uv run --project nemweb_foundation python \
  nemweb_foundation/scripts/validate_nemweb_genie.py \
  --execute \
  --profile <named-profile> \
  --catalog <catalog> \
  --schema <schema> \
  --warehouse-id <warehouse-id> \
  --output <evidence-path>.json
```

Every workspace-aware command must name a profile explicitly. Do not rely on an
implicit default.

What this newly proves that the offline run cannot:

- `distinct_key_columns` grain contracts on benchmarks 02–06. `_check_result_grain`
  is reachable only through `_check_benchmark_result`, i.e. only under `--execute`.
  Offline it is tested against synthetic responses only.
- Benchmark 04's expectation is now row-count-independent, so it holds at 0, 1 or
  50 rows. `--execute` is the first time that is observed against real content.

Known gap it will **not** close: freshness columns for benchmarks 03/04/05 were
deliberately not added. `expected_columns` is compared exactly and in order
against the live result manifest, so a new column cannot be proven correct until
a run like this one exists. Deferred rather than guessed.

## Step 2 — refusal side (no tooling; needs a decision first)

There is no script for this. Three options, cheapest first.

### 2a. Manual, in the Genie UI — recommended first

The six must-refuse questions are already `config.sample_questions` in the space,
so they appear as clickable prompts. No new code, and it exercises exactly what
an analyst would hit.

For each, record verbatim: the question, the response, whether it refused,
whether it **named a governed reason** rather than merely declining, and whether
it offered the supported near-miss instead. A refusal that says "I cannot answer
that" is a fail even though it refused.

### 2b. Scripted, via the conversation API

New scope: a helper that starts a conversation, posts each question, polls to a
terminal state, and captures the response text. Two cautions —

- Genie replies are **not deterministic**. Treat the result as evidence of
  behaviour on one run, not as a test with a pass/fail gate. Do not wire it into
  CI as a required check.
- It consumes compute per question.

### 2c. Facilitator's prepared cases

If the space or the Genie surface is unavailable, `lane_a_business/skills/06-benchmarks/SKILL.md`
directs recording a `prepared` or `unavailable` status rather than claiming a run.
Prepared material is non-live evidence and must be labelled as such.

## Acceptance criteria per refusal

A pass requires all four:

1. it refuses;
2. it names the governed reason — the rule and what is missing;
3. it does not invent a rule that is absent from the contract;
4. where a near-miss exists, it offers that supported question instead.

The near-miss pairs matter here: each must-refuse question shares nearly all its
vocabulary with an answerable twin, so a keyword filter would refuse both. Ask
the answerable twin too and confirm it is **not** refused.

`snapshot-price-as-live-spot` is the hardest case — same table, same measure as
`regional-price-demand`, differing only in tense. If any single case fails, this
is the likely one.

## What has been verified without a workspace

- 362 tests pass; 54 across the two Genie/benchmark files, up from 12.
- Static validation is genuinely offline: 6 benchmarks, 6 contract-cited refusals,
  6 Genie assets, 6 dashboard statements.
- Every cited `contract_quote` matches inside its named section of its named
  contract, whitespace-normalised. Two of six fail a raw substring match because
  the markdown hard-wraps, so normalisation is load-bearing.
- Mutation-tested: inventing a quote, moving a real quote to the wrong section,
  restoring the vacuous expectation, a duplicate key tuple, stripping the refusal
  policy, a decline-only policy, and dropping a sample question each turn the
  suite red.
- `serialized_space` parses equal to `nemweb_space.json`; `${var.*}` survive as
  literal text; one text-instruction block; all ids 32-hex; both lists sorted.

## What remains unproven until Step 2 runs

The refusal side is **text-only validated**. No evidence here shows the deployed
space actually refusing anything, or naming a reason when it does. The tests
prove the catalogue and the space instructions are internally consistent and
contract-grounded; they cannot prove model behaviour.
