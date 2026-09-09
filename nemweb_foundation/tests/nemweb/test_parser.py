from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from agentic_energy.nemweb.parser import parse_zip_bytes

FIXTURE = Path(__file__).parents[1] / "fixtures" / "nemweb" / "v1"


def _case(name: str) -> bytes:
    return next((FIXTURE / "cases" / name).glob("*.zip")).read_bytes()


def test_parses_all_csv_members_and_interleaved_sections() -> None:
    path = FIXTURE / "raw" / "dispatchis" / "PUBLIC_DISPATCHIS_202401010005_SYNTHETIC.zip"
    result = parse_zip_bytes(path.read_bytes(), "dispatchis")

    assert {record.csv_member for record in result.records} == {
        "PUBLIC_DISPATCHIS_MARKET.CSV",
        "PUBLIC_DISPATCHIS_NETWORK.CSV",
    }
    assert {(record.section_name, record.report_version) for record in result.records} == {
        ("PRICE", "5"),
        ("REGIONSUM", "9"),
        ("CONSTRAINT", "5"),
        ("INTERCONNECTORRES", "3"),
    }
    assert len(result.records) == 6
    assert {control.kind for control in result.controls} == {"C", "I", "F"}
    assert not [issue for issue in result.issues if issue.severity == "error"]


def test_typed_values_preserve_negative_prices_flows_and_intervention() -> None:
    data = (FIXTURE / "raw" / "dispatchis" / "PUBLIC_DISPATCHIS_202401010005_SYNTHETIC.zip").read_bytes()
    result = parse_zip_bytes(data, "dispatchis")
    price = next(r for r in result.records if r.section_name == "PRICE" and r.values["INTERVENTION"] == 0)
    flow = next(r for r in result.records if r.section_name == "INTERCONNECTORRES")
    assert price.values["RRP"] == -50.25
    assert price.values["RUNNO"] == 1
    assert price.values["SETTLEMENTDATE"] == "2024-01-01T00:05:00+10:00"
    assert flow.values["MWFLOW"] == -24.5


def test_malformed_rows_and_timezones_are_quarantined_not_dropped_silently() -> None:
    malformed = parse_zip_bytes(_case("malformed_row"), "dispatch_scada")
    assert malformed.records == ()
    assert [issue.code for issue in malformed.issues] == ["COLUMN_COUNT_MISMATCH"]

    boundary = parse_zip_bytes(_case("timezone_boundary"), "dispatch_scada")
    assert len(boundary.records) == 1
    assert boundary.records[0].values["SETTLEMENTDATE"].endswith("+10:00")
    assert [issue.code for issue in boundary.issues] == ["TYPE_CONVERSION_FAILED"]


def test_unknown_column_is_retained_and_explicitly_identified() -> None:
    result = parse_zip_bytes(_case("unknown_column"), "dispatch_scada")
    assert len(result.records) == 1
    record = result.records[0]
    assert record.unknown_columns == ("NEW_TELEMETRY_FLAG",)
    assert record.values["NEW_TELEMETRY_FLAG"] == "X"


def test_malformed_footer_is_preserved_and_reported() -> None:
    result = parse_zip_bytes(_case("malformed_footer"), "dispatch_scada")
    assert result.controls[0].kind == "F"
    assert result.issues[0].code == "MALFORMED_FOOTER"


def _zip(name: str, payload: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, payload)
    return output.getvalue()


def test_one_nested_zip_and_explicit_cp1252_encoding_are_supported() -> None:
    csv_bytes = (
        "I,DISPATCH,UNIT_SCADA,1,SETTLEMENTDATE,DUID,SCADAVALUE,LASTCHANGED\n"
        "D,DISPATCH,UNIT_SCADA,1,2024/01/01 00:05:00,UNITÉ,-2.5,2024/01/01 00:04:00\n"
    ).encode("cp1252")
    result = parse_zip_bytes(_zip("outer.zip", _zip("rows.CSV", csv_bytes)), "dispatch_scada")
    assert result.records[0].selected_encoding == "cp1252"
    assert result.records[0].csv_member == "outer.zip!rows.CSV"
    assert result.records[0].values["SCADAVALUE"] == -2.5


def test_nested_zip_depth_and_binary_control_bytes_are_rejected() -> None:
    import pytest
    from agentic_energy.nemweb.contracts import ContractError
    from agentic_energy.nemweb.parser import UnsafeArchiveError
    with pytest.raises(UnsafeArchiveError, match="depth"):
        parse_zip_bytes(_zip("one.zip", _zip("two.zip", _zip("x.CSV", b"F,END\n"))), "dispatchis")
    with pytest.raises(ContractError, match="control bytes"):
        parse_zip_bytes(_zip("x.CSV", b"I,DISPATCH,UNIT_SCADA,1,DUID\x00\n"), "dispatch_scada")
