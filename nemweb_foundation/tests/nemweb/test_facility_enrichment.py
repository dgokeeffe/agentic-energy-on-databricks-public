from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from agentic_energy.nemweb.corrections import build_facility_dimension
from agentic_energy.nemweb.parser import parse_zip_bytes
from agentic_energy.nemweb.quality import registration_enrichment_quality

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "tests" / "fixtures" / "nemweb" / "v1" / "raw"


def _registration_rows():
    archive = next((SNAPSHOT / "registration").glob("*.zip"))
    result = parse_zip_bytes(archive.read_bytes(), "registration")
    assert not [issue for issue in result.issues if issue.severity == "error"]
    grouped = {name: [] for name in ("DUDETAILSUMMARY", "DUALLOC", "GENUNITS")}
    for record in result.records:
        grouped[record.section_name].append(record.values)
    details = [{
        "duid": r["DUID"], "start_date": r["START_DATE"], "end_date": r["END_DATE"],
        "region_id": r["REGIONID"], "station_id": r.get("STATIONID"),
        "dispatch_type": r.get("DISPATCHTYPE"), "schedule_type": r.get("SCHEDULE_TYPE"),
        "source_version_no": 7,
    } for r in grouped["DUDETAILSUMMARY"]]
    allocations = [{
        "duid": r["DUID"], "effective_at": r["EFFECTIVEDATE"],
        "source_version_no": r["VERSIONNO"], "genset_id": r["GENSETID"],
    } for r in grouped["DUALLOC"]]
    generators = [{
        "genset_id": r["GENSETID"], "fuel_type_raw": r.get("CO2E_ENERGY_SOURCE"),
        "registered_capacity_mw": r.get("REGISTEREDCAPACITY"),
        "maximum_capacity_mw": r.get("MAXCAPACITY"),
    } for r in grouped["GENUNITS"]]
    return details, allocations, generators


def _snapshot_scada_duids() -> list[str]:
    archive = next((SNAPSHOT / "dispatch_scada").glob("*.zip"))
    result = parse_zip_bytes(archive.read_bytes(), "dispatch_scada")
    return [str(record.values["DUID"]) for record in result.records]


def test_real_mmsdm_join_has_complete_region_and_at_least_90_percent_fuel() -> None:
    details, allocations, generators = _registration_rows()
    dimension = build_facility_dimension(
        _snapshot_scada_duids(), details, allocations, generators,
        as_of="2026/07/15 00:00:00",
    )
    assert len(dimension) == len(_snapshot_scada_duids())
    quality = registration_enrichment_quality(dimension)
    quality.validate(registration_context_expected=True)
    assert quality.known_region_ratio == 1.0
    assert quality.known_fuel_ratio >= 0.90


def test_allocation_join_and_single_unit_fallback_are_both_proved() -> None:
    details, allocations, generators = _registration_rows()
    by_duid = {row["duid"]: row for row in build_facility_dimension(
        ["ARWF1", "ADPBA1"], details, allocations, generators,
        as_of="2026/07/15 00:00:00",
    )}
    assert by_duid["ARWF1"]["genset_id"] == "ARWF1_1"
    assert by_duid["ARWF1"]["fuel_type"] == "Wind"
    assert by_duid["ADPBA1"]["genset_id"] == "ADPBA1"
    assert by_duid["ADPBA1"]["fuel_type"] == "Battery storage"


def test_open_ended_registration_remains_effective_and_spark_contract_matches() -> None:
    detail = [{
        "duid": "OPEN1", "start_date": "2020/01/01 00:00:00",
        "end_date": None, "region_id": "NSW1", "source_version_no": 1,
    }]
    row = build_facility_dimension(
        ["OPEN1"], detail, [], [], as_of="2026/07/15 00:00:00",
    )[0]
    assert row["region_id"] == "NSW1"
    pipeline = (Path(__file__).resolve().parents[2] / "agentic_energy/nemweb/pipeline/silver_facilities.py").read_text()
    bronze = (Path(__file__).resolve().parents[2] / "agentic_energy/nemweb/pipeline/bronze_registration.py").read_text()
    assert 'F.col("end_date").isNull()' in pipeline
    assert "end_date IS NOT NULL" not in bronze


def test_all_unknown_enrichment_fails_when_registration_context_is_expected() -> None:
    with pytest.raises(ValueError, match="all regions are UNKNOWN"):
        registration_enrichment_quality([
            {"region_id": "UNKNOWN", "fuel_type": "Wind"},
            {"region_id": "UNKNOWN", "fuel_type": "Solar"},
        ]).validate(registration_context_expected=True)
    with pytest.raises(ValueError, match="all fuels are UNKNOWN"):
        registration_enrichment_quality([
            {"region_id": "NSW1", "fuel_type": "UNKNOWN"},
            {"region_id": "QLD1", "fuel_type": "UNKNOWN"},
        ]).validate(registration_context_expected=True)


def test_absent_registration_context_is_distinguishable_from_legitimate_unknown() -> None:
    """The case the Gold count-only gate could not see.

    An absent context load yields every row UNKNOWN, which must stop the run. A
    partial load yields *some* UNKNOWN rows, which is legitimate and must not.
    Both have a positive row count, so the row count alone cannot tell them apart.
    """

    absent = registration_enrichment_quality(
        [{"region_id": "UNKNOWN", "fuel_type": "UNKNOWN"} for _ in range(3)]
    )
    assert absent.total_rows == 3
    assert absent.known_region_ratio == 0.0
    assert absent.known_fuel_ratio == 0.0
    with pytest.raises(ValueError, match="all regions are UNKNOWN"):
        absent.validate(registration_context_expected=True)

    partial = registration_enrichment_quality([
        {"region_id": "NSW1", "fuel_type": "Wind"},
        {"region_id": "UNKNOWN", "fuel_type": "UNKNOWN"},
    ])
    assert partial.total_rows == 2
    assert partial.known_region_ratio == 0.5
    # Unmatched DUIDs are preserved, not filtered, and the result still passes.
    partial.validate(registration_context_expected=True)


def test_gold_generation_fails_an_interval_with_no_enrichment_at_all() -> None:
    """The Gold expectation must be interval-scoped, not per row.

    region_id and fuel_type are grouping keys, so a legitimately UNKNOWN group is
    a valid row. Only an interval with no known region *or* no known fuel is
    evidence of a missing context load.

    This asserts source text: the view is a @dp.materialized_view requiring
    Databricks Spark, so it cannot execute in this environment.
    """

    source = (
        Path(__file__).resolve().parents[2]
        / "agentic_energy/nemweb/pipeline/gold_scada_generation.py"
    ).read_text()

    assert '"registration_context_present_per_interval"' in source
    assert (
        "interval_known_region_facility_count > 0 "
        "AND interval_known_fuel_facility_count > 0" in source
    )
    # Interval-wide totals must come from a window, not the groupBy, or the
    # expectation would only ever see one region/fuel bucket.
    assert 'Window.partitionBy("interval_end")' in source
    for column in (
        "known_region_facility_count",
        "known_fuel_facility_count",
        "unmatched_facility_count",
        "interval_known_region_facility_count",
        "interval_known_fuel_facility_count",
    ):
        assert column in source, column
    # Rows are never dropped to obtain a pass.
    assert "expect_or_drop" in source
    assert "dimension_match_status" not in source.split("expect_or_drop")[1].split(")")[0]
    # The pre-existing count gate stays; the new one is additive.
    assert '"valid_scada_enrichment_counts"' in source


def test_gold_generation_carries_registration_effective_at_for_provenance() -> None:
    """A consumer cannot report attribution staleness it cannot read."""

    source = (
        Path(__file__).resolve().parents[2]
        / "agentic_energy/nemweb/pipeline/gold_scada_generation.py"
    ).read_text()
    # Selected from the dimension, then aggregated -- max, because the column is
    # NULL for an unmatched DUID.
    assert 'F.col("f.registration_effective_at")' in source
    assert 'F.max("registration_effective_at").alias("registration_effective_at")' in source


def test_pseudo_unit_keeps_region_and_unknown_fuel_instead_of_being_dropped() -> None:
    details, allocations, generators = _registration_rows()
    row = build_facility_dimension(
        ["RT_NSW6"], details, allocations, generators,
        as_of="2026/07/15 00:00:00",
    )[0]
    assert row["region_id"] == "NSW1"
    assert row["fuel_type"] == "UNKNOWN"
    assert row["dimension_match_status"] == "REGION_ONLY"
    # One pseudo-unit UNKNOWN remains valid in an otherwise healthy result.
    registration_enrichment_quality([
        row,
        {"region_id": "VIC1", "fuel_type": "Wind"},
    ]).validate(registration_context_expected=True)
