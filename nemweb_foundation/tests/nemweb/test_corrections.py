from __future__ import annotations

import pytest

from agentic_energy.nemweb.contracts import ContractError
from agentic_energy.nemweb.corrections import latest_by_natural_key


def row(**changes):
    base = {
        "interval_end": "2024-01-01T00:05:00+10:00",
        "region_id": "NSW1",
        "intervention": 0,
        "report_version": "5",
        "source_run_no": 1,
        "source_publication_at": "2024-01-01T00:06:00+10:00",
        "ingestion_sequence": 1,
        "value": "original",
    }
    base.update(changes)
    return base


KEY = ("interval_end", "region_id", "intervention")


def test_duplicate_archive_collapses_without_changing_bronze_inputs() -> None:
    source = [row(), row()]
    selected = latest_by_natural_key(source, KEY)
    assert len(source) == 2
    assert selected == [row()]


def test_higher_runno_wins_over_earlier_correction() -> None:
    assert latest_by_natural_key([row(), row(source_run_no=2, value="corrected")], KEY)[0]["value"] == "corrected"


def test_equal_version_later_publication_wins() -> None:
    later = row(source_publication_at="2024-01-01T00:07:00+10:00", value="later")
    assert latest_by_natural_key([row(), later], KEY)[0]["value"] == "later"


def test_ingestion_sequence_is_final_deterministic_tie_break() -> None:
    later = row(ingestion_sequence=99, value="deterministic")
    assert latest_by_natural_key([later, row()], KEY)[0]["value"] == "deterministic"


def test_bid_version_revision_precedes_landing_tie_breaks() -> None:
    newer = row(VERSIONNO=2, source_publication_at="2024-01-01T00:05:00+10:00", value="v2")
    older = row(VERSIONNO=1, source_publication_at="2024-01-01T00:07:00+10:00", value="v1")
    assert latest_by_natural_key([newer, older], KEY, source_revision="VERSIONNO")[0]["value"] == "v2"


def test_settlement_run_revision_precedes_landing_tie_breaks() -> None:
    newer = row(SETTLEMENTRUNNO=20, value="run20")
    older = row(SETTLEMENTRUNNO=10, ingestion_sequence=999, value="run10")
    assert latest_by_natural_key(
        [older, newer], KEY, source_revision="SETTLEMENTRUNNO"
    )[0]["value"] == "run20"


@pytest.mark.parametrize("bad", [None, "", "   "])
def test_malformed_natural_key_is_rejected_not_silently_dropped(bad) -> None:
    with pytest.raises(ContractError, match="natural-key"):
        latest_by_natural_key([row(region_id=bad)], KEY)


def test_null_ordering_field_is_rejected() -> None:
    with pytest.raises(ContractError, match="source_publication_at"):
        latest_by_natural_key([row(source_publication_at=None)], KEY)
