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
        "gold_nem_dispatch_price_spike_5min",
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
    assert '"known_dimension_match_status"' in source
    for status in ("REGION_AND_FUEL", "REGION_ONLY", "FUEL_ONLY", "UNMATCHED"):
        assert status in source


def test_scada_generation_left_joins_and_keeps_unknown_dimensions() -> None:
    source = (PIPELINE / "gold_scada_generation.py").read_text()
    assert '.join(facilities, "duid", "left")' in source
    assert source.count('F.lit("UNKNOWN")') >= 2
    assert '.groupBy("interval_end", "region_id", "fuel_type")' in source
    assert 'F.sum("actual_generation_mw")' in source
    assert '"valid_scada_enrichment_counts"' in source
    assert "partially_enriched_facility_count BETWEEN 0 AND facility_count" in source


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


def test_the_deployed_spike_window_excludes_the_interval_it_judges() -> None:
    """The deployed PySpark must match the tested pure function, not merely resemble it.

    ``miniwiki/decisions/facility-dimension-as-of.md`` records a defect where a
    well-tested pure function was reimplemented in PySpark with one input
    substituted, so the tests confirmed the assumption rather than the deployed
    behaviour. The frame end is that input here: ``rowsBetween(-288, 0)`` would let
    each price enter the median it is judged against and mask real spikes, while
    every pure-function test kept passing.
    """

    source = (PIPELINE / "gold_additional_aggregates.py").read_text()
    assert "rowsBetween(-SPIKE_BASELINE_INTERVALS, -1)" in source
    assert "rowsBetween(-SPIKE_BASELINE_INTERVALS, 0)" not in source
    # The window length is the shared constant, never a literal re-typed here.
    assert "rowsBetween(-288" not in source
    assert "from agentic_energy.nemweb.pipeline.config import (" in source


def test_the_deployed_spike_threshold_is_never_a_literal() -> None:
    """A hard-coded multiple would defeat the no-default decision silently."""

    source = (PIPELINE / "gold_additional_aggregates.py").read_text()
    assert "multiple = spike_baseline_multiple(spark)" in source
    assert "F.lit(multiple)" in source


def test_the_spike_flag_is_withheld_rather_than_false_when_undecidable() -> None:
    """NULL and false are different claims; the deployed CASE must keep them apart.

    ``F.when(...)`` with no ``.otherwise(...)`` yields NULL, which is the intent.
    An ``.otherwise(F.lit(False))`` would assert that a comparison was made and
    failed, on intervals where none was possible.
    """

    source = (PIPELINE / "gold_additional_aggregates.py").read_text()
    spike = source[source.index("def gold_nem_dispatch_price_spike_5min") :]
    spike = spike[: spike.index("@dp.materialized_view")]
    assert "otherwise(F.lit(False))" not in spike
    assert "_baseline_rows" in spike, "window completeness must be measured"
    assert 'F.col("_baseline_median") > 0' in spike, "non-positive baseline withheld"


def test_the_trailing_median_uses_exact_percentile_not_median_or_approx() -> None:
    """The median mechanism is not interchangeable, and the wrong one fails silently.

    Verified against a warehouse by scripts/verify_spike_sql_semantics.py:
    median() over a ROWS frame raises INVALID_WINDOW_SPEC_FOR_AGGREGATION_FUNC, so
    the view would not analyse at all. percentile_approx() *is* accepted, which
    makes it the tempting fix, but it is approximate -- for [0, 1] it returns 0.0
    where the exact median is 0.5. That would disagree with every offline test
    while the pipeline stayed green, which is the worse failure of the two.
    """

    source = (PIPELINE / "gold_additional_aggregates.py").read_text()
    assert 'F.expr("percentile(rrp_aud_per_mwh, 0.5)")' in source
    # Comment lines legitimately name the rejected functions to explain why they
    # are rejected, so only executable lines are searched.
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    assert "F.median(" not in code, "median() cannot take a window frame"
    assert "percentile_approx" not in code, "approximate median diverges from the rule"


def test_the_spike_view_separates_administered_prices_from_market_prices() -> None:
    """An administered or suspended price is an intervention artefact.

    Counting it as market scarcity overstates genuine price risk, so the basis is
    carried as a dimension rather than being dropped or silently merged.
    """

    source = (PIPELINE / "gold_additional_aggregates.py").read_text()
    assert 'F.lit("ADMINISTERED")' in source
    assert 'F.lit("SUSPENDED")' in source
    assert 'F.lit("MARKET")' in source
    assert "price_formation_basis" in source
