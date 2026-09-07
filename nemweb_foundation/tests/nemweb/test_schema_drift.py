from __future__ import annotations

from pathlib import Path

from agentic_energy.nemweb.parser import parse_zip_bytes
from agentic_energy.nemweb.schema_drift import assess_schema_drift

FIXTURE = Path(__file__).parents[1] / "fixtures" / "nemweb" / "v1" / "cases"


def _parsed(case: str, family: str):
    data = next((FIXTURE / case).glob("*.zip")).read_bytes()
    return parse_zip_bytes(data, family)


def test_missing_required_column_fails_schema_contract() -> None:
    report = assess_schema_drift(_parsed("missing_required_column", "dispatchis"))
    assert report.failed
    finding = report.findings[0]
    assert finding.status == "fail"
    assert finding.missing_required == ("REGIONID",)


def test_unknown_column_is_quarantined_with_column_name() -> None:
    report = assess_schema_drift(_parsed("unknown_column", "dispatch_scada"))
    assert not report.failed
    assert report.warning_count == 1
    finding = report.findings[0]
    assert finding.status == "quarantine"
    assert finding.unexpected_columns == ("NEW_TELEMETRY_FLAG",)


def test_known_schema_is_compatible() -> None:
    data = next((Path(__file__).parents[1] / "fixtures" / "nemweb" / "v1" /
                 "raw" / "dispatch_scada").glob("*.zip")).read_bytes()
    report = assess_schema_drift(parse_zip_bytes(data, "dispatch_scada"))
    assert [finding.status for finding in report.findings] == ["compatible"]
