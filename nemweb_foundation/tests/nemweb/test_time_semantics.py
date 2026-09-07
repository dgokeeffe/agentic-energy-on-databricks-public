from datetime import timedelta, timezone

import pytest

from agentic_energy.nemweb.contracts import ContractError, market_time_to_utc, parse_market_time


def test_interval_boundary_is_interval_ending_fixed_aest() -> None:
    end = parse_market_time("2024/01/01 00:05:00")
    start = end - timedelta(minutes=5)
    assert end.utcoffset() == timedelta(hours=10)
    assert start.isoformat() == "2024-01-01T00:00:00+10:00"
    assert market_time_to_utc("2024/01/01 00:05:00").isoformat() == "2023-12-31T14:05:00+00:00"


def test_aest_does_not_change_at_civil_daylight_saving_boundary() -> None:
    before = parse_market_time("2024/04/07 01:55:00")
    after = parse_market_time("2024/04/07 02:05:00")
    assert before.utcoffset() == after.utcoffset() == timedelta(hours=10)
    assert after - before == timedelta(minutes=10)


@pytest.mark.parametrize("value", ["2024-01-01T00:05:00+11:00", "2024-01-01T00:05:00Z", "2024-01-01"])
def test_non_nem_or_ambiguous_timestamp_is_rejected(value: str) -> None:
    with pytest.raises(ContractError):
        parse_market_time(value)
