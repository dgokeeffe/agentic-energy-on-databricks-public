# Market time is Brisbane; source time is per-feed

## Decision

Two different timezones coexist in this repository on purpose.

**NEM market time is `Australia/Brisbane`.** Brisbane is UTC+10 all year with no
daylight saving, which is exactly the fixed-AEST semantics of NEM dispatch
intervals. It is the Spark session zone, the market zone, and the schedule zone.

**A source's `source_timezone` describes how that feed stamps its own
timestamps**, which is not always the market zone. It is per-feed metadata, not a
second opinion about market time.

Do not "tidy" these into one value. They answer different questions: what a
market interval *means* versus how an upstream file *was written*.

## Where each one is enforced

Market time is asserted, not assumed. `nemweb_foundation/agentic_energy/nemweb/pipeline/config.py:44`
raises before any data is read:

```python
if session_timezone != "Australia/Brisbane":
    raise ValueError("spark.sql.session.timeZone must be Australia/Brisbane")
if market_timezone != "Australia/Brisbane":
    raise ValueError(
        "NEM market timestamps must use fixed AEST semantics "
        "(Australia/Brisbane)"
    )
```

The same value is pinned in the deployed resources, so a pipeline cannot inherit
a workspace default:

- `nemweb_foundation/resources/nemweb.pipeline.yml:94` — `spark.sql.session.timeZone`
- `nemweb_foundation/resources/nemweb.pipeline.yml:102` — `nemweb.market_timezone`
- `nemweb_foundation/resources/nemweb_refresh.job.yml:42` — `timezone_id`
- `nemweb_foundation/resources/nemweb_context_refresh.job.yml:12` — `timezone_id`

Contract-level parsing is independent of all of it: `parse_market_time` hardcodes
the +10:00 offset, and `tests/nemweb/test_time_semantics.py` asserts the offset
does not move across the civil daylight-saving boundary.

## The apparent inconsistency, and why it is not one

The same field name, `interval_datetime`, carries different `source_timezone`
values in the two metadata files:

| File | `source_timezone` | Why |
|---|---|---|
| `resources/metadata/sources.live.json:18` | `Australia/Brisbane` | Real NEMWEB DISPATCHIS. Market time, so fixed AEST. |
| `resources/metadata/sources.json:6` | `Australia/Sydney` | Workshop fixture. Sydney *because* it observes DST. |

The weather feed is `Australia/Sydney` in both files (`sources.json:13`,
`sources.live.json:41`). That is correct and unremarkable: Open-Meteo
observations are civil-time, not market-time.

The snapshot fixture is not mislabelled. Its rows are dated `2024-04-07`:

```
{"region":"NSW1","interval_datetime":"2024-04-07T10:00:00", ...}
```

That date is the 2024 NSW daylight-saving changeover. Tagging the fixture
`Australia/Sydney` is what makes it exercise the gap/fold logic in
`agentic_energy/pipeline.py:59`, which refuses to guess an offset:

```python
unique_offsets = {candidate.utcoffset() for candidate in candidates}
if not candidates or len(unique_offsets) != 1:
    raise ValueError("NONEXISTENT_OR_AMBIGUOUS_LOCAL_TIME")
```

`tests/test_pipeline.py:148` locks in the resulting normalisation, and the two
assertions are only meaningfully different because Sydney shifts:

```python
assert _utc_timestamp("2024-04-07T10:00:00", "Australia/Sydney") == "2024-04-07T00:00:00Z"
assert _utc_timestamp("2024-01-15T10:00:00", "Australia/Sydney") == "2024-01-14T23:00:00Z"
```

Same wall-clock `10:00`, two different UTC instants. Rewrite that fixture to
Brisbane and both lines collapse to a constant offset — the test still passes and
silently stops testing anything.

## What would make a change here wrong

- Unifying `source_timezone` to Brisbane everywhere. The DST-normalisation path
  stops being covered while its tests stay green.
- Substituting `Australia/Sydney` for market time. It is UTC+11 for roughly half
  the year and would misplace every dispatch interval by an hour in that window.
- Relying on the machine's local timezone. It is irrelevant by design — all
  production time calls are explicitly zoned and there are no naive
  `datetime.now()` calls in the repository. A developer shell reading UTC is not
  a defect; see the processing-time convention in
  [`../../QUICKSTART.md`](../../QUICKSTART.md).
- Deriving the facility dimension from wall-clock time. That failure already
  happened; see [`facility-dimension-as-of.md`](facility-dimension-as-of.md).

## Status

Documentation only. No behaviour was changed, and no defect was found in the
timezone handling — this page exists because the Brisbane/Sydney split was
readable only from code and appeared nowhere in the prose except one passing
mention in [`opening-demo.md`](opening-demo.md).
