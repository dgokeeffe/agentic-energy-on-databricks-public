from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agentic_energy.nemweb.parser import parse_zip_bytes

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tests" / "fixtures" / "nemweb" / "v1" / "raw"
PIPELINE = ROOT / "agentic_energy" / "nemweb" / "pipeline"


def _values(family: str, section: str) -> list[dict[str, object]]:
    archive = next((RAW / family).glob("*.zip"))
    parsed = parse_zip_bytes(archive.read_bytes(), family)
    assert not [issue for issue in parsed.issues if issue.severity == "error"]
    return [record.values for record in parsed.records if record.section_name == section]


def test_snapshot_t1_targets_reconcile_to_overlapping_scada_without_conflation() -> None:
    scada = {
        (row["SETTLEMENTDATE"], row["DUID"]): float(row["SCADAVALUE"])
        for row in _values("dispatch_scada", "UNIT_SCADA")
    }
    solutions = _values("next_day_dispatch", "UNIT_SOLUTION")
    assert len(solutions) == 2
    results = {}
    for row in solutions:
        key = (row["SETTLEMENTDATE"], row["DUID"])
        actual = scada[key]
        target = float(row["TOTALCLEARED"])
        results[str(row["DUID"])] = {
            "actual": actual,
            "target": target,
            "variance": actual - target,
            "availability": float(row["AVAILABILITY"]),
        }
        assert datetime.fromisoformat(str(row["LASTCHANGED"])) > datetime.fromisoformat(
            str(row["SETTLEMENTDATE"])
        )
    assert results == {
        "ARWF1": {"actual": 20.0, "target": 21.0, "variance": -1.0, "availability": 241.0},
        "ADPBA1": {"actual": -5.0, "target": -6.0, "variance": 1.0, "availability": 7.0},
    }


def test_t1_gold_keeps_target_availability_and_scada_as_separate_columns() -> None:
    source = (PIPELINE / "gold_unit_solution.py").read_text()
    assert 'F.col("t.total_cleared_mw")' in source
    assert 'F.col("t.availability_mw")' in source
    assert 'alias("overlapping_scada_actual_mw")' in source
    assert 'alias("scada_minus_dispatch_target_mw")' in source
    assert 'alias("absolute_scada_dispatch_variance_mw")' in source
    assert "daily T+1 cadence" in source
    assert "must never be represented as Current five-minute availability" in source


def test_t1_gold_left_join_preserves_solution_when_scada_is_missing() -> None:
    source = (PIPELINE / "gold_unit_solution.py").read_text()
    assert 'target.join(scada, ["interval_end", "duid"], "left")' in source
    assert '.join(\n        facilities, "duid", "left"\n    )' in source
