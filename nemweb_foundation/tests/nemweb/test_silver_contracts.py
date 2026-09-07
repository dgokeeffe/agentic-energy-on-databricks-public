from __future__ import annotations

import ast
from pathlib import Path

from agentic_energy.nemweb.corrections import constraint_is_binding, latest_by_natural_key

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "agentic_energy" / "nemweb" / "pipeline"
SILVER_FILES = {
    "silver_region_dispatch.py": "silver_nem_region_dispatch",
    "silver_scada.py": "silver_nem_dispatch_unit_scada",
    "silver_constraints.py": "silver_nem_dispatch_constraint",
    "silver_interconnectors.py": "silver_nem_interconnector_flow",
    "silver_unit_solution.py": "silver_nem_dispatch_unit_solution_t1",
    "silver_facilities.py": "silver_nem_facility_dimension",
}


def _declared_dataset(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "materialized_view":
                for keyword in decorator.keywords:
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                        names.add(keyword.value.value)
    return names


def test_all_six_silver_contracts_are_materialized_views() -> None:
    for filename, table in SILVER_FILES.items():
        assert table in _declared_dataset(PIPELINE / filename)
        source = (PIPELINE / filename).read_text()
        assert "spark.read.table(" in source
        assert "dp.read(" not in source


def test_negative_prices_and_negative_battery_load_mw_are_valid_values() -> None:
    common = {
        "report_version": 1,
        "source_run_no": 1,
        "source_publication_at": "2024-01-01T00:06:00+10:00",
        "ingestion_sequence": 1,
    }
    price = {**common, "interval_end": "2024-01-01T00:05:00+10:00", "region_id": "SA1", "intervention": 0, "rrp_aud_per_mwh": -1000.0}
    scada = {**common, "interval_end": "2024-01-01T00:05:00+10:00", "duid": "BATTERY1", "actual_generation_mw": -25.0}
    assert latest_by_natural_key([price], ("interval_end", "region_id", "intervention"))[0]["rrp_aud_per_mwh"] == -1000.0
    assert latest_by_natural_key([scada], ("interval_end", "duid"))[0]["actual_generation_mw"] == -25.0


def test_binding_rule_is_exact_non_zero_and_raw_rows_are_not_filtered() -> None:
    assert constraint_is_binding(0) is False
    assert constraint_is_binding(None) is False
    assert constraint_is_binding(0.0001) is True
    source = (PIPELINE / "silver_constraints.py").read_text()
    assert 'F.col("marginal_value") != F.lit(0.0)' in source
    assert "0.001" not in source
    assert "no constraint is filtered out" in source
