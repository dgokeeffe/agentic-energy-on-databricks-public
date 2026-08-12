# Agent token usage

The README carries a token-usage badge under its title. This page explains what
that number is, how it is measured, and why two different totals are quoted.

## How to refresh it

```bash
python3 scripts/token-usage.py            # print the report
python3 scripts/token-usage.py --write    # refresh the README badge in place
```

The badge lives between `<!-- token-usage:begin -->` and
`<!-- token-usage:end -->` markers in `README.md`. The script rewrites only the
block between those markers, so it is safe to re-run and cannot drift into the
surrounding prose. Do not hand-edit the numbers: the point of the block is that
it is generated from a transcript rather than typed from memory.

## Where the numbers come from

The pi harness appends a `usage` object to every assistant message in the session
transcript named by `PI_SESSION_FILE` (JSONL, one record per line). The script
sums those objects. Nothing is estimated, and nothing is derived from
character counts.

```json
{"input": 16663, "output": 88, "cacheRead": 0, "cacheWrite": 0,
 "reasoning": 0, "totalTokens": 16751,
 "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0}}
```

## Two totals, because one alone misleads

| Figure | Meaning | Scale here |
|---|---|---|
| **Billed** | Sum of every call's `input` + `output` | ~14.8M |
| **Conversation** | Final call's `input` + all `output` | ~178K |

A chat agent re-sends the entire conversation on every turn, so `input` grows
roughly linearly with turn count: the first call in this session sent 16,663
input tokens and a later one sent 119,548. Summing that column counts the same
context dozens of times.

Both figures are honest, and each is misleading alone:

- Quoting only **14.8M** implies an enormous amount of unique material was
  produced. It was not; most of it is the model re-reading its own history.
- Quoting only **178K** understates what a provider would invoice.

So the badge shows billed as the headline, with generated output alongside, and
the caption states the conversation size explicitly.

## Reported cost is zero, and that is not a claim of free

`usage.cost.total` is `0` for every call in this session because this harness
does not attach prices to the model endpoint (`system.ai.claude-opus-5` via the
`omnigent` provider). The script reports the field verbatim rather than
multiplying by a guessed rate. **A zero here means "not priced by the harness",
not "no cost incurred".** Anyone who needs a dollar figure should apply their own
contracted rate to the token counts.

## Limitations

- **The figure covers one session, not the project.** It measures the agent
  session that produced the recent commits on this branch. It is not the
  cumulative cost of the repository, and re-running the script in a different
  session reports that session instead.
- **It is only refreshed when someone runs the script.** The number is accurate
  as of the commit that wrote it and goes stale immediately afterwards — the
  session continues after the badge is written, so the true final total for a
  session is always slightly higher than the last committed badge. It is a
  snapshot, not a live counter.
- **`cacheRead` / `cacheWrite` / `reasoning` are zero here.** That reflects this
  harness configuration (`PI_REASONING_LEVEL=off`), not a general property. On a
  cache-enabled provider, billed input would overstate real cost substantially,
  since cached reads are usually much cheaper.
- **It cannot be reproduced from a clean clone.** Without `PI_SESSION_FILE` and
  its transcript there is nothing to measure, and the script exits `2` with an
  explanatory message rather than inventing a total. This is the same
  reproducibility caveat that applies to the Beads evidence in
  [`README.md`](README.md) in this directory.
- **Token count is not a measure of value.** A large total can mean thorough
  verification or wasted, unfocused looping. It should not be read as a
  productivity metric in either direction.

## Measured snapshot

Captured on the session that produced commits `4d5603d` … `f2517df` on branch
`Team-SGS`:

```text
model calls        : 199
input  (summed)    : 14,677,983
output (summed)    : 112,528
cache read/write   : 0 / 0
reasoning          : 0
BILLED total       : 14,790,511  (14.8M)
conversation size  : 178,027  (last context + all output)
final context      : 65,499
reported cost      : 0.0  (0 when the harness does not price calls)
```
