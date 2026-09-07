from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "agentic_energy" / "nemweb" / "pipeline"

GOLD_DATASETS = {
    "gold_region_dispatch.py": {"gold_nem_region_dispatch_5min"},
    "gold_unit_dispatch.py": {"gold_nem_unit_dispatch_5min"},
    "gold_scada_generation.py": {"gold_nem_scada_generation_5min"},
    "gold_constraints.py": {"gold_nem_binding_constraints_5min"},
    "gold_interconnectors.py": {"gold_nem_interconnector_flows_5min"},
    "gold_unit_solution.py": {"gold_nem_unit_dispatch_availability_t1"},
    "gold_additional_aggregates.py": {
        "gold_nem_dispatch_price_30min",
        "gold_nem_dispatch_price_daily",
        "gold_nem_interconnector_flow_30min",
    },
}


def _declared_materialized_views(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "materialized_view"
            ):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    names.add(str(keyword.value.value))
    return names


def test_all_required_gold_products_are_modern_materialized_views() -> None:
    for filename, expected in GOLD_DATASETS.items():
        path = PIPELINE / filename
        assert _declared_materialized_views(path) == expected
        source = path.read_text()
        assert "spark.read.table(" in source
        assert "dp.read(" not in source
        assert ".write" not in source


def test_every_critical_gold_product_exposes_watermarks_and_publication() -> None:
    for filename in GOLD_DATASETS:
        if filename == "gold_additional_aggregates.py":
            continue
        source = (PIPELINE / filename).read_text()
        assert "source_interval_watermark" in source
        assert "source_publication_at" in source
        assert "gold_published_at" in source


def test_intervention_products_retain_and_label_both_runs() -> None:
    for filename in (
        "gold_region_dispatch.py",
        "gold_constraints.py",
        "gold_interconnectors.py",
        "gold_unit_solution.py",
    ):
        source = (PIPELINE / filename).read_text()
        assert "intervention" in source
        assert "is_effective_run" in source
        assert "Both intervention" in source


def test_current_unit_product_is_scada_actual_not_fabricated_availability() -> None:
    source = (PIPELINE / "gold_unit_dispatch.py").read_text()
    assert 'spark.read.table("silver_nem_dispatch_unit_scada")' in source
    assert "actual_generation_mw" in source
    assert "availability_mw" not in source
    assert "dispatch_target_mw" not in source
    assert "does not publish five-minute unit availability" in source


def test_scada_generation_left_joins_and_keeps_unknown_dimensions() -> None:
    source = (PIPELINE / "gold_scada_generation.py").read_text()
    assert '.join(facilities, "duid", "left")' in source
    assert source.count('F.lit("UNKNOWN")') >= 2
    assert '.groupBy("interval_end", "region_id", "fuel_type")' in source
    assert 'F.sum("actual_generation_mw")' in source


def test_binding_rule_and_flow_sign_are_explicit_not_silently_changed() -> None:
    constraints = (PIPELINE / "gold_constraints.py").read_text()
    interconnectors = (PIPELINE / "gold_interconnectors.py").read_text()
    assert 'binding.rule": "marginal_value_non_zero"' in constraints
    assert '.where(F.col("is_binding"))' in constraints
    assert 'flow.sign": "aemo_source"' in interconnectors
    assert "AEMO source sign is retained unchanged" in interconnectors


def test_additional_aggregates_default_to_effective_five_minute_gold() -> None:
    source = (PIPELINE / "gold_additional_aggregates.py").read_text()
    assert 'spark.read.table("gold_nem_region_dispatch_5min")' in source
    assert 'spark.read.table("gold_nem_interconnector_flows_5min")' in source
    assert source.count('F.col("is_effective_run")') == 2
    assert source.count('F.expr("INTERVAL 1 MICROSECOND")') == 3
    assert "30 minutes" in source
    assert "five-minute Gold table remains the primary product" in source
