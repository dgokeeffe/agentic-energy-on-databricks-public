"""Offline contract evidence for critical append-only NEMWEB Bronze tables."""

from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

from agentic_energy.ingestion.lander import land_snapshot

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "src" / "agentic_energy"
SNAPSHOT = ROOT / "tests" / "fixtures" / "nemweb" / "v1"

EXPECTED_PROVENANCE = {
    "source_mode",
    "source_url_path",
    "source_archive",
    "source_archive_sha256",
    "source_csv_member",
    "report_family",
    "section_name",
    "report_version",
    "run_no",
    "source_publication_at",
    "source_publication_basis",
    "interval_end",
    "landed_at",
    "ingested_at",
    "ingestion_run_id",
    "ingestion_sequence",
    "_rescued_data",
}
CRITICAL_TABLES = {
    "bronze_nem_dispatch_price",
    "bronze_nem_dispatch_region_sum",
    "bronze_nem_dispatch_constraint",
    "bronze_nem_dispatch_interconnector_res",
    "bronze_nem_dispatch_unit_scada",
    "bronze_nem_genunits",
    "bronze_nem_dudetail",
    "bronze_nem_dualloc",
}
SECTION_REQUIRED_VALUES = {
    ("dispatchis", "PRICE"): {"SETTLEMENTDATE", "RUNNO", "REGIONID", "INTERVENTION", "RRP"},
    ("dispatchis", "REGIONSUM"): {"SETTLEMENTDATE", "RUNNO", "REGIONID", "INTERVENTION", "TOTALDEMAND"},
    ("dispatchis", "CONSTRAINT"): {"SETTLEMENTDATE", "RUNNO", "CONSTRAINTID", "INTERVENTION"},
    ("dispatchis", "INTERCONNECTORRES"): {"SETTLEMENTDATE", "RUNNO", "INTERCONNECTORID", "INTERVENTION", "MWFLOW"},
    ("dispatch_scada", "UNIT_SCADA"): {"SETTLEMENTDATE", "DUID", "SCADAVALUE"},
    ("next_day_dispatch", "UNIT_SOLUTION"): {"SETTLEMENTDATE", "RUNNO", "DUID", "INTERVENTION", "TOTALCLEARED", "AVAILABILITY"},
    ("registration", "DUDETAILSUMMARY"): {"DUID", "START_DATE", "REGIONID"},
    ("registration", "DUALLOC"): {"EFFECTIVEDATE", "VERSIONNO", "DUID", "GENSETID"},
    ("registration", "GENUNITS"): {"GENSETID"},
}


def _table_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "dp"
                and func.attr == "table"
            ):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    names.add(keyword.value.value)
    return names


def test_all_critical_bronze_tables_and_quarantines_are_declared() -> None:
    sources = list((PIPELINE / "bronze").glob("bronze_*.py"))
    table_names = set().union(*(_table_names(path) for path in sources))
    assert CRITICAL_TABLES <= table_names
    for name in CRITICAL_TABLES:
        assert name.replace("bronze_", "quarantine_", 1) in table_names


def test_common_bronze_provenance_contract_is_complete() -> None:
    io_source = (PIPELINE / "common" / "io.py").read_text()
    tree = ast.parse(io_source)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PROVENANCE_COLUMNS" for target in node.targets)
    )
    assert EXPECTED_PROVENANCE == set(ast.literal_eval(assignment.value))
    assert "source_publication_timestamp" in io_source
    assert "source_publication_at" in io_source
    assert 'NOT COALESCE(({validity_sql}), FALSE)' in io_source


def test_scada_is_actual_generation_and_t1_is_not_misrepresented() -> None:
    scada = (PIPELINE / "bronze" / "bronze_scada.py").read_text()
    assert "actual_generation_mw" in scada
    assert "dispatch_target_mw" not in scada
    assert "actual_generation_mw >= 0" not in scada


def test_snapshot_parsed_rows_reconcile_per_section_to_bronze_or_quarantine(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "landed"
    result = land_snapshot(SNAPSHOT, destination, run_id="bronze-reconciliation")
    manifest = json.loads(result.manifest_path.read_text())
    observed = Counter()

    for archive in manifest["archives"]:
        for section in archive["sections"]:
            key = (archive["report_family"], section["section_name"])
            if key not in SECTION_REQUIRED_VALUES:
                continue
            path = destination / "snapshot" / section["parsed_path"]
            rows = [json.loads(line) for line in path.read_text().splitlines() if line]
            valid = sum(
                all(row["values"].get(column) is not None for column in SECTION_REQUIRED_VALUES[key])
                for row in rows
            )
            quarantined = len(rows) - valid
            assert section["row_count"] == valid + quarantined
            observed[key] += len(rows)

    assert observed == Counter(
        {
            ("dispatchis", "PRICE"): 4,
            ("dispatchis", "REGIONSUM"): 4,
            ("dispatchis", "CONSTRAINT"): 2,
            ("dispatchis", "INTERCONNECTORRES"): 2,
            ("dispatch_scada", "UNIT_SCADA"): 28,
            ("next_day_dispatch", "UNIT_SOLUTION"): 2,
            ("registration", "DUDETAILSUMMARY"): 28,
            ("registration", "DUALLOC"): 19,
            ("registration", "GENUNITS"): 14,
        }
    )
    assert sum(observed.values()) == result.parsed_row_count == 103


def test_bronze_never_deduplicates_distinct_report_versions() -> None:
    sources = "\n".join(path.read_text() for path in (PIPELINE / "bronze").glob("bronze_*.py"))
    assert "dropDuplicates" not in sources
    assert "distinct()" not in sources
    assert "row_number" not in sources
    assert "source_run_no" in (ROOT / "src/agentic_energy/ingestion/source_registry.py").read_text()
    assert "report_version" in (PIPELINE / "common" / "io.py").read_text()
