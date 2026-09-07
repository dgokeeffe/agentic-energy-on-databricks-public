from __future__ import annotations

from datetime import timedelta

import pytest

from agentic_energy.nemweb.contracts import ContractError, market_time_to_utc, parse_market_time
from agentic_energy.nemweb.schemas import get_schema, registered_families, required_sections


def test_critical_schema_registry_is_versioned_and_complete() -> None:
    assert {"dispatchis", "dispatch_scada", "next_day_dispatch", "registration"} <= registered_families()
    assert required_sections("dispatchis") == {
        ("DISPATCH", "PRICE", "5"),
        ("DISPATCH", "REGIONSUM", "9"),
        ("DISPATCH", "CONSTRAINT", "5"),
        ("DISPATCH", "INTERCONNECTORRES", "3"),
    }
    price = get_schema("dispatchis", "DISPATCH", "PRICE", "5")
    assert price is not None
    assert {"SETTLEMENTDATE", "RUNNO", "REGIONID", "INTERVENTION", "RRP"} <= price.required_names
    assert get_schema("dispatchis", "DISPATCH", "PRICE", "4") is None


def test_nem_market_time_is_fixed_aest_without_dst() -> None:
    winter = parse_market_time("2024/04/07 02:30:00")
    summer = parse_market_time("2024/10/06 02:30:00")
    assert winter.utcoffset() == summer.utcoffset() == timedelta(hours=10)
    assert market_time_to_utc("2024/10/06 02:30:00").isoformat() == "2024-10-05T16:30:00+00:00"
    assert parse_market_time("2024-10-06T02:30:00+10:00").isoformat().endswith("+10:00")


@pytest.mark.parametrize("value", [
    "2024-10-06T02:30:00+11:00",
    "2024-01-01T00:00:00Z",
    "2024-01-01",
    "2024-01-01 00:00 AEDT",
    "",
])
def test_nem_market_time_rejects_non_aest_or_ambiguous_forms(value: str) -> None:
    with pytest.raises(ContractError):
        parse_market_time(value)
