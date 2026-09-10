"""Correction observability for the DISPATCHIS PRICE critical report family.

These tests prove the operator question "why did this published interval
change?" can be answered from the same governed latest-correction contract that
Silver already uses. Nothing here needs Spark or a workspace.
"""

from __future__ import annotations

import pytest

from agentic_energy.nemweb.contracts import ContractError
from agentic_energy.nemweb.corrections import (
    DISPATCH_PRICE_VALUE_FIELDS,
    correction_history,
    dispatch_price_correction_history,
    latest_by_natural_key,
)
from agentic_energy.nemweb.source_registry import get_subject_by_key

KEY = ("interval_end", "region_id", "intervention")


def row(**changes):
    """One Bronze DISPATCHIS PRICE row with its complete source lineage."""

    base = {
        "interval_end": "2024-01-01T00:05:00+10:00",
        "region_id": "NSW1",
        "intervention": 0,
        "report_version": "5",
        "source_run_no": 1,
        "source_publication_at": "2024-01-01T00:06:00+10:00",
        "landed_at": "2024-01-01T00:06:30+10:00",
        "ingestion_run_id": "run-a",
        "ingestion_sequence": 1,
        "source_row_number": 1,
        "source_csv_member": "PUBLIC_DISPATCHIS_202401010005_0000000001.CSV",
        "source_archive": "PUBLIC_DISPATCHIS_202401010005_0000000001.zip",
        "source_archive_sha256": "a" * 64,
        "source_url_path": "/Reports/Current/DispatchIS_Reports/"
        "PUBLIC_DISPATCHIS_202401010005_0000000001.zip",
        "rrp_aud_per_mwh": 91.5,
        "energy_excess_price_aud_per_mwh": 0.0,
        "regional_override_price_aud_per_mwh": 91.5,
        "administered_price_cap_flag": 0,
        "market_suspended_flag": 0,
    }
    base.update(changes)
    return base


def corrected(**changes):
    """A genuine later AEMO correction: a distinct archive with a later RUNNO."""

    run_no = changes.pop("source_run_no", 2)
    checksum = changes.pop("source_archive_sha256", "b" * 64)
    archive = f"PUBLIC_DISPATCHIS_202401010005_000000000{run_no}.zip"
    return row(
        source_run_no=run_no,
        source_publication_at="2024-01-01T00:11:00+10:00",
        landed_at="2024-01-01T00:11:30+10:00",
        ingestion_run_id=changes.pop("ingestion_run_id", "run-b"),
        source_archive=archive,
        source_archive_sha256=checksum,
        source_url_path=f"/Reports/Current/DispatchIS_Reports/{archive}",
        **changes,
    )


def only(records):
    assert len(records) == 1
    return records[0]


# --- 1. a later correction wins for the governed current value ---------------


def test_later_correction_wins_for_the_governed_current_value() -> None:
    history = only(dispatch_price_correction_history([row(), corrected(rrp_aud_per_mwh=310.0)]))

    assert history["current"]["values"]["rrp_aud_per_mwh"] == 310.0
    assert history["current"]["correction_sequence"] == 2
    assert history["correction_status"] == "VALUE_CORRECTED"
    assert history["is_value_corrected"] is True
    assert history["changed_value_fields"] == ("rrp_aud_per_mwh",)


def test_later_correction_wins_regardless_of_bronze_row_order() -> None:
    forward = only(dispatch_price_correction_history([row(), corrected(rrp_aud_per_mwh=310.0)]))
    reversed_input = only(
        dispatch_price_correction_history([corrected(rrp_aud_per_mwh=310.0), row()])
    )
    assert forward == reversed_input


def test_current_value_is_the_existing_latest_correction_and_not_a_second_definition() -> None:
    """The governed current value must be the row ``latest_by_natural_key`` picks."""

    rows = [
        corrected(rrp_aud_per_mwh=310.0),
        row(),
        corrected(
            source_run_no=3,
            rrp_aud_per_mwh=275.0,
            source_archive_sha256="c" * 64,
            ingestion_run_id="run-c",
        ),
    ]
    history = only(dispatch_price_correction_history(rows))
    governed = latest_by_natural_key(rows, KEY)[0]

    assert history["current"]["source_row"] == governed
    assert history["current"]["values"]["rrp_aud_per_mwh"] == governed["rrp_aud_per_mwh"]


# --- 2. the original remains traceable --------------------------------------


def test_original_source_version_remains_traceable() -> None:
    history = only(dispatch_price_correction_history([row(), corrected(rrp_aud_per_mwh=310.0)]))
    original = history["original"]

    assert original["correction_sequence"] == 1
    assert original["values"]["rrp_aud_per_mwh"] == 91.5
    assert original["source_archive"] == (
        "PUBLIC_DISPATCHIS_202401010005_0000000001.zip"
    )
    assert original["source_archive_sha256"] == "a" * 64
    assert original["source_publication_at"] == "2024-01-01T00:06:00+10:00"
    assert original["report_version"] == "5"
    assert original["source_run_no"] == 1
    # Complete source-version metadata survives, not just the compared measures.
    assert original["source_row"] == row()


def test_every_intermediate_correction_is_retained_in_governed_order() -> None:
    middle = corrected(rrp_aud_per_mwh=310.0)
    newest = corrected(
        source_run_no=3,
        rrp_aud_per_mwh=275.0,
        source_archive_sha256="c" * 64,
        ingestion_run_id="run-c",
    )
    history = only(dispatch_price_correction_history([newest, row(), middle]))

    assert [version["correction_sequence"] for version in history["source_versions"]] == [1, 2, 3]
    assert [
        version["values"]["rrp_aud_per_mwh"] for version in history["source_versions"]
    ] == [91.5, 310.0, 275.0]
    assert history["source_version_count"] == 3
    assert history["correction_count"] == 2


def test_bronze_rows_are_never_mutated_or_collapsed_by_observability() -> None:
    source = [row(), corrected(rrp_aud_per_mwh=310.0)]
    before = [dict(item) for item in source]
    dispatch_price_correction_history(source)
    assert source == before


# --- 3. duplicate archives with identical content are not value corrections --


def test_duplicate_archive_with_identical_content_is_not_a_value_correction() -> None:
    history = only(dispatch_price_correction_history([row(), row()]))

    assert history["is_value_corrected"] is False
    assert history["correction_status"] == "NO_CORRECTION"
    assert history["source_version_count"] == 1
    assert history["correction_count"] == 0
    assert history["changed_value_fields"] == ()
    assert history["original"]["source_row"] == history["current"]["source_row"]


def test_duplicate_archive_relanded_in_a_later_run_is_still_one_source_version() -> None:
    # The same archive re-listed by AEMO and landed again in a later run keeps
    # its checksum and its row number within that archive.
    relanded = row(
        landed_at="2024-01-02T00:00:00+10:00",
        ingestion_run_id="run-z",
    )
    history = only(dispatch_price_correction_history([row(), relanded]))

    assert history["source_version_count"] == 1
    assert history["correction_status"] == "NO_CORRECTION"
    assert history["is_value_corrected"] is False


# --- 4. an unchanged corrected row differs from a changed value --------------


def test_republished_row_with_unchanged_value_is_distinguishable_from_a_changed_value() -> None:
    unchanged = only(dispatch_price_correction_history([row(), corrected()]))
    changed = only(dispatch_price_correction_history([row(), corrected(rrp_aud_per_mwh=310.0)]))

    assert unchanged["correction_status"] == "REPUBLISHED_UNCHANGED"
    assert unchanged["is_value_corrected"] is False
    assert unchanged["changed_value_fields"] == ()
    # A republication is still a real later source version, unlike a duplicate.
    assert unchanged["source_version_count"] == 2
    assert unchanged["correction_count"] == 1
    assert unchanged["current"]["source_run_no"] == 2

    assert changed["correction_status"] == "VALUE_CORRECTED"
    assert changed["is_value_corrected"] is True
    assert changed["correction_status"] != unchanged["correction_status"]


def test_republished_unchanged_row_is_distinguishable_from_a_duplicate_archive() -> None:
    republished = only(dispatch_price_correction_history([row(), corrected()]))
    duplicate = only(dispatch_price_correction_history([row(), row()]))

    assert republished["correction_status"] != duplicate["correction_status"]
    assert republished["source_version_count"] == 2
    assert duplicate["source_version_count"] == 1


def test_a_change_in_any_governed_value_field_counts_as_a_correction() -> None:
    history = only(dispatch_price_correction_history([row(), corrected(market_suspended_flag=1)]))
    assert history["correction_status"] == "VALUE_CORRECTED"
    assert history["changed_value_fields"] == ("market_suspended_flag",)


def test_a_retyped_but_unchanged_measure_is_not_reported_as_a_correction() -> None:
    """``"91.5"`` and ``91.5`` are the same published price, not a correction."""

    history = only(
        dispatch_price_correction_history(
            [row(), corrected(rrp_aud_per_mwh="91.5", market_suspended_flag=False)]
        )
    )
    assert history["changed_value_fields"] == ()
    assert history["correction_status"] == "REPUBLISHED_UNCHANGED"


def test_a_measure_that_disappears_is_reported_as_a_change() -> None:
    history = only(dispatch_price_correction_history([row(), corrected(rrp_aud_per_mwh=None)]))
    assert history["changed_value_fields"] == ("rrp_aud_per_mwh",)
    assert history["correction_status"] == "VALUE_CORRECTED"


# --- 5. natural-key and intervention fields remain in the comparison --------


def test_natural_key_and_intervention_remain_part_of_the_comparison() -> None:
    intervention_run = corrected(intervention=1, rrp_aud_per_mwh=310.0)
    records = dispatch_price_correction_history([row(), intervention_run])

    assert len(records) == 2
    assert [record["intervention"] for record in records] == [0, 1]
    # Neither intervention run is reported as a correction of the other.
    assert {record["correction_status"] for record in records} == {"NO_CORRECTION"}
    assert all(record["source_version_count"] == 1 for record in records)


def test_a_different_region_is_never_reported_as_a_correction() -> None:
    records = dispatch_price_correction_history(
        [row(), corrected(region_id="VIC1", rrp_aud_per_mwh=310.0)]
    )
    assert [record["region_id"] for record in records] == ["NSW1", "VIC1"]
    assert all(not record["is_value_corrected"] for record in records)


def test_natural_key_is_echoed_on_every_observability_record() -> None:
    record = only(dispatch_price_correction_history([row()]))
    for field in KEY:
        assert record[field] == row()[field]


def test_the_natural_key_comes_from_the_governed_source_registry() -> None:
    subject = get_subject_by_key("dispatch_price")
    assert subject.natural_key == KEY
    assert "intervention" in subject.natural_key
    assert "rrp_aud_per_mwh" in DISPATCH_PRICE_VALUE_FIELDS


# --- shared contract behaviour ----------------------------------------------


@pytest.mark.parametrize("bad", [None, "", "   "])
def test_malformed_natural_key_is_rejected_not_silently_dropped(bad) -> None:
    with pytest.raises(ContractError, match="natural-key"):
        dispatch_price_correction_history([row(region_id=bad)])


def test_null_ordering_field_is_rejected_exactly_as_in_the_latest_contract() -> None:
    with pytest.raises(ContractError, match="source_publication_at"):
        dispatch_price_correction_history([row(source_publication_at=None)])


def test_report_specific_revision_is_honoured_without_a_new_ordering_rule() -> None:
    newer = row(
        SETTLEMENTRUNNO=20,
        source_archive_sha256="d" * 64,
        rrp_aud_per_mwh=310.0,
    )
    older = row(SETTLEMENTRUNNO=10, ingestion_sequence=999)
    history = only(
        correction_history(
            [older, newer],
            KEY,
            value_fields=DISPATCH_PRICE_VALUE_FIELDS,
            source_revision="SETTLEMENTRUNNO",
        )
    )
    assert history["current"]["values"]["rrp_aud_per_mwh"] == 310.0
    assert history["current"]["source_row"] == (
        latest_by_natural_key([older, newer], KEY, source_revision="SETTLEMENTRUNNO")[0]
    )


def test_current_value_tracks_the_latest_contract_even_when_versions_tie() -> None:
    """Two distinct archives tying on every ordering field must not diverge.

    ``current`` is read out of the single ``latest_by_natural_key`` selection, so
    the reported current value is the governed one by construction rather than
    by a parallel "last one wins" rule in this module.
    """

    tied = row(source_archive_sha256="e" * 64, rrp_aud_per_mwh=310.0)
    history = only(dispatch_price_correction_history([row(), tied]))
    governed = latest_by_natural_key([row(), tied], KEY)[0]

    assert history["source_version_count"] == 2
    assert history["current"]["source_row"] == governed
    assert history["current"]["values"]["rrp_aud_per_mwh"] == governed["rrp_aud_per_mwh"]


def test_records_are_returned_in_deterministic_natural_key_order() -> None:
    records = dispatch_price_correction_history(
        [row(region_id="VIC1"), row(region_id="NSW1"), row(region_id="QLD1")]
    )
    assert [record["region_id"] for record in records] == ["NSW1", "QLD1", "VIC1"]
