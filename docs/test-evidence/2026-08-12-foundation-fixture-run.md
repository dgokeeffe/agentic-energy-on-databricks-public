# Test evidence — foundation fixture run (historical tracker capture)

> Historical note: this dated record includes output from the retired participant
> tracker. The current workflow uses the committed Markdown miniwiki; no tracker
> database or closure checker is required.

| | |
|---|---|
| Captured (UTC) | 2026-08-12T04:49:57Z |
| Repository commit | `4a06f168cf95694831f64d52270c2cf8ad6ba82b` (branch `Team-SGS`) |
| Python | 3.10.12 |
| pytest | 9.1.1 (pluggy 1.6.0) |
| Historical coordination record | Archived output; no current tracker is required |
| Historical work item | `agentic-energy-93y` — Foundation: run the deterministic fixture ETL |
| Overall | **PASS** — 24 tests passed, 17/17 closure checks passed, replay byte-identical |

Evidence for the deterministic Bronze → Silver → Quarantine → Gold fixture run
and the historical closure of the foundation work item. Layer contracts and per-record lineage
are documented separately in [`../data-lineage.md`](../data-lineage.md); this
file is the dated record of *what was executed and what it printed*.

All output below is **verbatim console capture**, not transcription.

## Contents

- [A. Contract test suite](#a-contract-test-suite)
- [B. Historical tracker capture](#b-historical-tracker-capture)
- [C. Historical coordination capture](#c-historical-coordination-capture)
- [D. Pipeline run, manifest, and replay determinism](#d-pipeline-run-manifest-and-replay-determinism)
- [Acceptance equations](#acceptance-equations)
- [Provenance and limitations](#provenance-and-limitations)

## A. Contract test suite

```bash
uv run --extra test python -m pytest -v
```

```text
platform linux -- Python 3.10.12, pytest-9.1.1, pluggy-1.6.0
rootdir: /…/agentic-energy-on-databricks-public
configfile: pyproject.toml
testpaths: tests
collected 24 items

tests/test_bundle_concurrency.py ......                                  [ 25%]
tests/test_lakebase_artifacts.py ....                                    [ 41%]
tests/test_pipeline.py ..............                                    [100%]

============================== 24 passed in 0.13s ==============================
exit=0
```

This is the only check in this document that is **machine-enforced for every
clone** — see [Provenance and limitations](#provenance-and-limitations).

## B. Historical tracker capture

```text
Retired standalone checker output is preserved below as historical capture.
It is not a current command.
```

```text
PASS  foundation status: 'closed'
PASS  foundation id: 'agentic-energy-93y'
PASS  closed_at present: True
PASS  close reason non-trivial (>500 chars): True
PASS  close reason cites 'bronze=11': True
PASS  close reason cites 'silver=6': True
PASS  close reason cites 'quarantine=3': True
PASS  close reason cites 'gold=3': True
PASS  close reason cites 'e2235552': True
PASS  close reason cites '24 passed': True
PASS  close reason cites 'identical replay': True
PASS  agentic-energy-zwh unblocked: True
PASS  agentic-energy-02f unblocked: True
PASS  agentic-energy-yx8 unblocked: True
PASS  agentic-energy-5g3 unblocked: True
PASS  agentic-energy-aln unblocked: True
PASS  foundation absent from ready: True
------------------------------------------------------------
ALL CHECKS PASSED
exit=0
```

The captured assertions show that the retired workflow required evidence: the
recorded close reason quoted layer counts, the metadata hash prefix, the test
result, and the replay claim.

### B2. Negative control

A green checker proves nothing unless it can fail. One assertion was inverted
(`"closed"` → `"open"`) and the checker re-run:

```text
FAIL  foundation status: 'closed' (expected 'open')
1 FAILURE(S): foundation status
exit=1
```

The assertions are load-bearing and the exit code is honest.

## C. Historical coordination capture

```text
Historical tracker state was captured at the time of the run; it is not a
current command or prerequisite.
```

```text
id               = agentic-energy-93y
title            = Foundation: run the deterministic fixture ETL
status           = closed
issue_type       = task
priority         = 1
created_at       = 2026-08-11T14:14:03Z
started_at       = 2026-08-12T04:20:44Z
closed_at        = 2026-08-12T04:42:19Z
updated_at       = 2026-08-12T04:42:19Z
dependent_count  = 5
revision         = 3449003596232041403
close_reason     = 1895 chars
○ agentic-energy-zwh P1 Engineering: inspect and improve the metadata contract
○ agentic-energy-02f P1 [bug] Defect: local market timestamps are not normalized correctly
○ agentic-energy-yx8 P1 [bug] Defect: malformed rows are not safely quarantined
○ agentic-energy-5g3 P1 [bug] Defect: annotation access does not enforce identity boundaries
○ agentic-energy-aln P1 [bug] Defect: synchronized Gold reconciliation is inconsistent

--------------------------------------------------------------------------------
Ready: 5 issues with no active blockers
```

All five dependents moved from blocked to ready, and the foundation work item no
longer appeared in the retired queue.

## D. Pipeline run, manifest, and replay determinism

```bash
uv run python -m agentic_energy.cli --output output-ev1
uv run python -m agentic_energy.cli --output output-ev2   # replay
```

```text
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3
Pipeline complete: bronze=11, silver=6, quarantine=3, gold=3
```

`manifest.json`:

```json
{
  "layers": {"bronze": 11, "gold": 3, "quarantine": 3, "silver": 6},
  "metadata_sha256": "e2235552b0131cfc2272a6a1da5075a8bea2d5a66c13d57496b8f770562ca94e",
  "mode": "fixture",
  "pipeline_ingested_at": "2024-04-07T00:00:00Z",
  "source_definitions": {"read": 2, "selected": 2},
  "source_ids": ["aemo_dispatch_fixture", "weather_fixture"],
  "sources": {
    "aemo_dispatch_fixture": {"accepted": 4, "bronze": 6, "deduplicated": 1, "quarantine": 2, "silver": 3},
    "weather_fixture":       {"accepted": 4, "bronze": 5, "deduplicated": 1, "quarantine": 1, "silver": 3}
  }
}
```

`sha256` of every artifact (run 1):

```text
74b81048350cda0bc9ce3f1bfe976e8b363de0934a517a73c1d725aca64849c7  ./bronze/aemo_dispatch_fixture.jsonl
d45bab3f6e3e0df90170e7cd08155ea4b0a5968efaf9c847c7c85d43756f9be4  ./bronze/weather_fixture.jsonl
f56fe6473b47cf8f31e6bbfede38cb71b923dee068edbc6f6d89f38e313d9f3d  ./gold/market_weather.jsonl
76a442644e994d35c05b85adb6781a6cda5abbfefb6e1d2224d2b9f4a37009ed  ./manifest.json
42abde41b303b6fa3dbecdfc3038d416684d065e451a5d4f7576b20f55329e92  ./quarantine/rejected.jsonl
f757635ce33ffcce60836690fb000bbe38c1e3d172a05a66d43cee6bfe6065fb  ./silver/aemo_dispatch_fixture.jsonl
28c28552326461045f69f28efca05afe774222c399a9ec1c848725d13e833989  ./silver/weather_fixture.jsonl
```

```text
--- replay: IDENTICAL, all 7 files match by sha256 ---
```

Run 2 reproduced all seven hashes. These hashes are stable for this metadata
contract: they will change if `sources.json` or the fixtures change, which is the
point — `metadata_sha256` ties the artifacts to the contract that produced them.

## Acceptance equations

From [`../facilitator/workshop-acceptance.md`](../facilitator/workshop-acceptance.md), evaluated against
the manifest above:

| Equation | `aemo_dispatch_fixture` | `weather_fixture` |
|---|---|---|
| `source definitions read == selected` | 2 == 2 ✓ | — |
| `bronze == accepted + quarantine` | 6 == 4+2 ✓ | 5 == 4+1 ✓ |
| `accepted == silver + deduplicated` | 4 == 3+1 ✓ | 4 == 3+1 ✓ |
| `silver keys unique by natural key` | 3/3 ✓ | 3/3 ✓ |
| `silver timestamps normalized` | all `Z` ✓ | all `Z` ✓ |
| `identical replay` | 7/7 hashes ✓ | ✓ |
| `run status success after all sources complete` | exit 0 ✓ | ✓ |

The first two are also enforced in code and abort the run
(`BRONZE_RECONCILIATION_FAILED` / `SILVER_RECONCILIATION_FAILED`), so a manifest
that exists has already passed them.

The three quarantined rows are **expected**: the checked-in fixtures carry
planted bad values, each isolated with a reason code rather than silently
dropped (`INVALID_DEMAND` on `demand_mw: -1`, `MISSING_PRICE` on a null price,
`MISSING_TEMPERATURE` on a null temperature). An empty quarantine would be the
failing result here.

## Provenance and limitations

Read this before citing the document.

- **Sections A and D are reproducible by anyone else.** `pytest` and the fixture
  replay run from a clean clone. Sections B and C are historical captures from
  the retired tracker and are not current validation steps.
- **The historical coordination capture is deliberately not asserted by the
  test suite.** Current human decisions and handoffs belong in the miniwiki;
  deterministic behavior belongs in `tests/`.
- **The tracker capture is historical and per-participant.** It is retained to
  explain the original run, not as a requirement for new participants. Current
  context is coordinated through committed Markdown pages, branches, and pull
  requests.
- **This is a fixture-mode run.** No Databricks workspace, credentials, or
  network were used, and nothing here is evidence about the deployed path. Per
  [`../facilitator/workshop-acceptance.md`](../facilitator/workshop-acceptance.md), the deployment
  extension must not be marked complete from fixture evidence alone.
- **A green fixture run does not clear the seeded defects.** `agentic-energy-yx8`
  (malformed rows not quarantined) and `agentic-energy-02f` (timestamps not
  normalized) both behaved *correctly* for these fixtures, so they trigger on
  input shapes the fixtures do not cover — a DST fold or gap value, an
  offset-bearing timestamp, or a non-object JSON line. Absence of failure here is
  not evidence of absence of the defect.
- **Timestamps are container-relative.** The capture time and the retired
  tracker timestamps came from the CoDA container clock.

## Reproducing this record

```bash
# A
uv run --extra test python -m pytest -v

# B and C are historical captures and are not rerun.

# D
uv run python -m agentic_energy.cli --output output-ev1
uv run python -m agentic_energy.cli --output output-ev2
diff <(cd output-ev1 && find . -type f | sort | xargs sha256sum) \
     <(cd output-ev2 && find . -type f | sort | xargs sha256sum) && echo IDENTICAL
rm -rf output-ev1 output-ev2
```
