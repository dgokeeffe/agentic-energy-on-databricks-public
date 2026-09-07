from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from agentic_energy.nemweb.corrections import (
    build_facility_dimension,
    constraint_is_binding,
    latest_by_natural_key,
    mark_effective_intervention,
)
from agentic_energy.nemweb.lander import land_snapshot
from agentic_energy.nemweb.parser import parse_zip_bytes

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "tests" / "fixtures" / "nemweb" / "v1"
RAW = SNAPSHOT / "raw"


def _parsed(report_family: str, path: Path | None = None):
    archives = [path] if path else sorted((RAW / report_family).glob("*.zip"))
    records = []
    for archive in archives:
        result = parse_zip_bytes(archive.read_bytes(), report_family)
        assert not [issue for issue in result.issues if issue.severity == "error"]
        records.extend(result.records)
    return records


def _silver_rows(report_family: str, section_name: str) -> list[dict[str, object]]:
    rows = []
    for sequence, record in enumerate(_parsed(report_family), start=1):
        if record.section_name != section_name:
            continue
        values = record.values
        rows.append({
            "interval_end": values.get("SETTLEMENTDATE"),
            "region_id": values.get("REGIONID"),
            "duid": values.get("DUID"),
            "constraint_id": values.get("CONSTRAINTID"),
            "interconnector_id": values.get("INTERCONNECTORID"),
            "intervention": values.get("INTERVENTION"),
            "report_version": int(record.report_version),
            "source_run_no": values.get("RUNNO") or 0,
            "source_publication_at": "2026-09-02T11:30:00+10:00",
            "ingestion_sequence": sequence,
            **values,
        })
    return rows


def _facility_dimension(scada_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in _parsed("registration"):
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
    return build_facility_dimension(
        [str(row["DUID"]) for row in scada_rows],
        details,
        allocations,
        generators,
        as_of="2026/07/15 00:00:00",
    )


def _snapshot_products() -> tuple[dict[str, list[dict[str, object]]], dict[str, int]]:
    prices = latest_by_natural_key(
        _silver_rows("dispatchis", "PRICE"),
        ("interval_end", "region_id", "intervention"),
    )
    demand = latest_by_natural_key(
        _silver_rows("dispatchis", "REGIONSUM"),
        ("interval_end", "region_id", "intervention"),
    )
    demand_by_key = {
        (r["interval_end"], r["region_id"], r["intervention"]): r for r in demand
    }
    region = []
    for price in prices:
        key = (price["interval_end"], price["region_id"], price["intervention"])
        row = dict(price)
        row["total_demand_mw"] = demand_by_key[key]["TOTALDEMAND"]
        row["rrp_aud_per_mwh"] = price["RRP"]
        region.append(row)
    region = mark_effective_intervention(region, ("interval_end", "region_id"))

    scada = latest_by_natural_key(
        _silver_rows("dispatch_scada", "UNIT_SCADA"), ("interval_end", "duid")
    )
    dimension = {row["duid"]: row for row in _facility_dimension(scada)}
    unit = []
    generation_by_key: dict[tuple[object, object, object], dict[str, object]] = {}
    for row in scada:
        facility = dimension[str(row["duid"])]
        output = {
            "interval_end": row["interval_end"],
            "duid": row["duid"],
            "actual_generation_mw": row["SCADAVALUE"],
            **facility,
        }
        unit.append(output)
        key = (row["interval_end"], facility["region_id"], facility["fuel_type"])
        aggregate = generation_by_key.setdefault(key, {
            "interval_end": key[0], "region_id": key[1], "fuel_type": key[2],
            "actual_generation_mw": 0.0, "facility_count": 0,
        })
        aggregate["actual_generation_mw"] = float(aggregate["actual_generation_mw"]) + float(row["SCADAVALUE"])
        aggregate["facility_count"] = int(aggregate["facility_count"]) + 1

    constraints = latest_by_natural_key(
        _silver_rows("dispatchis", "CONSTRAINT"),
        ("interval_end", "constraint_id", "intervention"),
    )
    constraints = [
        {**row, "is_binding": True}
        for row in constraints if constraint_is_binding(row["MARGINALVALUE"])
    ]
    constraints = mark_effective_intervention(
        constraints, ("interval_end", "constraint_id")
    )
    interconnectors = mark_effective_intervention(
        latest_by_natural_key(
            _silver_rows("dispatchis", "INTERCONNECTORRES"),
            ("interval_end", "interconnector_id", "intervention"),
        ),
        ("interval_end", "interconnector_id"),
    )
    t1 = mark_effective_intervention(
        latest_by_natural_key(
            _silver_rows("next_day_dispatch", "UNIT_SOLUTION"),
            ("interval_end", "duid", "intervention"),
        ),
        ("interval_end", "duid"),
    )
    products = {
        "region": region,
        "unit": unit,
        "generation": list(generation_by_key.values()),
        "constraints": constraints,
        "interconnectors": interconnectors,
        "unit_t1": t1,
    }
    silver_counts = {
        "region": len(region), "scada": len(scada), "constraints": len(constraints),
        "interconnectors": len(interconnectors), "unit_t1": len(t1),
        "facilities": len(dimension),
    }
    return products, silver_counts


def test_snapshot_layer_and_subject_counts_reconcile(tmp_path: Path) -> None:
    landed = land_snapshot(
        SNAPSHOT, tmp_path / "landing-parent", run_id="gold-e2e"
    )
    products, silver_counts = _snapshot_products()
    assert landed.parsed_row_count == 103
    assert silver_counts == {
        "region": 4, "scada": 28, "constraints": 2,
        "interconnectors": 2, "unit_t1": 2, "facilities": 14,
    }
    assert {name: len(rows) for name, rows in products.items()} == {
        "region": 4, "unit": 28, "generation": 22,
        "constraints": 2, "interconnectors": 2, "unit_t1": 2,
    }


def test_gold_natural_keys_and_effective_runs_are_unique() -> None:
    products, _ = _snapshot_products()
    keys = {
        "region": ("interval_end", "region_id", "intervention"),
        "unit": ("interval_end", "duid"),
        "generation": ("interval_end", "region_id", "fuel_type"),
        "constraints": ("interval_end", "constraint_id", "intervention"),
        "interconnectors": ("interval_end", "interconnector_id", "intervention"),
        "unit_t1": ("interval_end", "duid", "intervention"),
    }
    for name, rows in products.items():
        natural_keys = [tuple(row[field] for field in keys[name]) for row in rows]
        assert len(natural_keys) == len(set(natural_keys)), name
    assert [row["intervention"] for row in products["region"] if row["is_effective_run"]] == [1, 1]
    for name in ("constraints", "interconnectors", "unit_t1"):
        business_keys = defaultdict(int)
        key_fields = keys[name][:-1]
        for row in products[name]:
            if row["is_effective_run"]:
                business_keys[tuple(row[field] for field in key_fields)] += 1
        assert set(business_keys.values()) == {1}


def test_selected_silver_values_reconcile_and_unknown_facility_survives() -> None:
    products, _ = _snapshot_products()
    assert sum(float(row["actual_generation_mw"]) for row in products["generation"]) == sum(
        float(row["actual_generation_mw"]) for row in products["unit"]
    ) == 446.0
    unknown = [row for row in products["unit"] if row["duid"] == "RT_NSW6"]
    assert len(unknown) == 2
    assert {row["region_id"] for row in unknown} == {"NSW1"}
    assert {row["fuel_type"] for row in unknown} == {"UNKNOWN"}
    effective_region = next(row for row in products["region"] if row["is_effective_run"])
    assert effective_region["rrp_aud_per_mwh"] == 250.0
    assert effective_region["total_demand_mw"] == 7001.5


def test_snapshot_intervals_are_five_minute_aligned_interval_endings() -> None:
    products, _ = _snapshot_products()
    for rows in products.values():
        for row in rows:
            interval = datetime.fromisoformat(str(row["interval_end"]))
            assert interval.second == interval.microsecond == 0
            assert interval.minute % 5 == 0
            assert interval.utcoffset().total_seconds() == 10 * 60 * 60
    for name in ("region", "unit", "generation", "constraints", "interconnectors"):
        intervals = sorted({datetime.fromisoformat(str(row["interval_end"])) for row in products[name]})
        assert len(intervals) == 2
        assert (intervals[1] - intervals[0]).total_seconds() == 300


def test_later_source_correction_propagates_to_region_gold() -> None:
    base = _silver_rows("dispatchis", "PRICE")
    correction_path = SNAPSHOT / "cases" / "later_correction" / "LATER_CORRECTION.zip"
    corrected_record = _parsed("dispatchis", correction_path)[0]
    corrected = {
        "interval_end": corrected_record.values["SETTLEMENTDATE"],
        "region_id": corrected_record.values["REGIONID"],
        "intervention": corrected_record.values["INTERVENTION"],
        "report_version": int(corrected_record.report_version),
        "source_run_no": corrected_record.values["RUNNO"],
        "source_publication_at": "2026-09-02T11:35:00+10:00",
        "ingestion_sequence": 99,
        "RRP": corrected_record.values["RRP"],
    }
    selected = latest_by_natural_key(
        [*base, corrected], ("interval_end", "region_id", "intervention")
    )
    non_intervention = next(row for row in selected if row["intervention"] == 0)
    assert non_intervention["source_run_no"] == 2
    assert non_intervention["RRP"] == 75.0
