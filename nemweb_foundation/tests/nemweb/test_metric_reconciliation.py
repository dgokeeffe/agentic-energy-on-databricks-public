from __future__ import annotations

import math
import re
from pathlib import Path
from statistics import mean

import yaml

ROOT = Path(__file__).parents[2]
METRIC_SQL = (ROOT / "sql/nemweb_metric_views.sql").read_text()


def metric_definitions() -> dict[str, dict]:
    pattern = re.compile(
        r"CREATE OR REPLACE VIEW\s+(\w+)\s+WITH METRICS\s+LANGUAGE YAML\s+AS \$\$(.*?)\$\$;",
        re.DOTALL | re.IGNORECASE,
    )
    return {name: yaml.safe_load(body) for name, body in pattern.findall(METRIC_SQL)}


EXPECTED_EXPRESSIONS = {
    "nem_region_dispatch_metrics": {
        "average_dispatch_price_aud_per_mwh": "AVG(rrp_aud_per_mwh)",
        "maximum_dispatch_price_aud_per_mwh": "MAX(rrp_aud_per_mwh)",
        "average_total_demand_mw": "AVG(total_demand_mw)",
        "estimated_demand_energy_mwh": "SUM(total_demand_mw) * 5.0 / 60.0",
        "five_minute_interval_count": "COUNT(1)",
    },
    "nem_unit_output_metrics": {
        "average_actual_generation_mw": "AVG(source.actual_generation_mw)",
        "maximum_actual_generation_mw": "MAX(source.actual_generation_mw)",
        "estimated_actual_energy_mwh": "SUM(source.actual_generation_mw) * 5.0 / 60.0",
        "unit_interval_count": "COUNT(1)",
    },
    "nem_scada_generation_metrics": {
        "average_actual_generation_mw": "AVG(actual_generation_mw)",
        "estimated_actual_energy_mwh": "SUM(actual_generation_mw) * 5.0 / 60.0",
        "partially_enriched_observation_count": "SUM(CASE WHEN partially_enriched_facility_count > 0 THEN 1 ELSE 0 END)",
    },
    "nem_binding_constraint_metrics": {
        "binding_constraint_interval_count": "COUNT(1)",
        "distinct_binding_constraint_count": "COUNT(DISTINCT constraint_id)",
        "average_marginal_value": "AVG(marginal_value)",
        "maximum_violation_degree": "MAX(violation_degree)",
    },
    "nem_interconnector_flow_metrics": {
        "average_source_sign_flow_mw": "AVG(mw_flow)",
        "estimated_source_sign_flow_mwh": "SUM(mw_flow) * 5.0 / 60.0",
        "average_losses_mw": "AVG(mw_losses)",
        "estimated_losses_mwh": "SUM(mw_losses) * 5.0 / 60.0",
    },
    "nem_unit_availability_t1_metrics": {
        "average_dispatch_target_mw": "AVG(total_cleared_mw)",
        "average_availability_mw": "AVG(availability_mw)",
        "estimated_dispatched_energy_mwh": "SUM(total_cleared_mw) * 5.0 / 60.0",
        "mean_absolute_scada_target_variance_mw": "AVG(absolute_scada_dispatch_variance_mw)",
    },
    "nem_bid_availability_metrics": {
        "average_maximum_offer_availability_mw": "AVG(maximum_availability_mw)",
        "average_total_band_availability_mw": "AVG(COALESCE(band_availability_1_mw, 0) + COALESCE(band_availability_2_mw, 0) + COALESCE(band_availability_3_mw, 0) + COALESCE(band_availability_4_mw, 0) + COALESCE(band_availability_5_mw, 0) + COALESCE(band_availability_6_mw, 0) + COALESCE(band_availability_7_mw, 0) + COALESCE(band_availability_8_mw, 0) + COALESCE(band_availability_9_mw, 0) + COALESCE(band_availability_10_mw, 0))",
        "minimum_price_band_aud_per_mwh": "MIN(LEAST(price_band_1_aud_per_mwh, price_band_2_aud_per_mwh, price_band_3_aud_per_mwh, price_band_4_aud_per_mwh, price_band_5_aud_per_mwh, price_band_6_aud_per_mwh, price_band_7_aud_per_mwh, price_band_8_aud_per_mwh, price_band_9_aud_per_mwh, price_band_10_aud_per_mwh))",
        "bid_period_row_count": "COUNT(1)",
    },
}


SOURCE_ROWS = {
    "nem_region_dispatch_metrics": [
        {"rrp_aud_per_mwh": 50.0, "total_demand_mw": 1000.0, "is_effective_run": True},
        {"rrp_aud_per_mwh": 70.0, "total_demand_mw": 1100.0, "is_effective_run": True},
        {"rrp_aud_per_mwh": 999.0, "total_demand_mw": 9999.0, "is_effective_run": False},
    ],
    "nem_unit_output_metrics": [
        {"actual_generation_mw": 12.0},
        {"actual_generation_mw": -3.0},
    ],
    "nem_scada_generation_metrics": [
        {"actual_generation_mw": 100.0, "partially_enriched_facility_count": 0},
        {"actual_generation_mw": -10.0, "partially_enriched_facility_count": 2},
    ],
    "nem_binding_constraint_metrics": [
        {"constraint_id": "C1", "marginal_value": 2.0, "violation_degree": 0.0, "is_effective_run": True},
        {"constraint_id": "C2", "marginal_value": -3.0, "violation_degree": 0.1, "is_effective_run": True},
        {"constraint_id": "C3", "marginal_value": 100.0, "violation_degree": 9.0, "is_effective_run": False},
    ],
    "nem_interconnector_flow_metrics": [
        {"mw_flow": 120.0, "mw_losses": 5.0, "is_effective_run": True},
        {"mw_flow": -60.0, "mw_losses": 3.0, "is_effective_run": True},
        {"mw_flow": 999.0, "mw_losses": 99.0, "is_effective_run": False},
    ],
    "nem_unit_availability_t1_metrics": [
        {"total_cleared_mw": 100.0, "availability_mw": 120.0, "absolute_scada_dispatch_variance_mw": 4.0, "is_effective_run": True},
        {"total_cleared_mw": 50.0, "availability_mw": 60.0, "absolute_scada_dispatch_variance_mw": 6.0, "is_effective_run": True},
        {"total_cleared_mw": 900.0, "availability_mw": 900.0, "absolute_scada_dispatch_variance_mw": 90.0, "is_effective_run": False},
    ],
    "nem_bid_availability_metrics": [
        {
            "maximum_availability_mw": 100.0,
            **{f"band_availability_{i}_mw": float(i) for i in range(1, 11)},
            **{f"price_band_{i}_aud_per_mwh": float(i * 10) for i in range(1, 11)},
        },
        {
            "maximum_availability_mw": 200.0,
            **{f"band_availability_{i}_mw": 10.0 for i in range(1, 11)},
            **{f"price_band_{i}_aud_per_mwh": float(-100 + i) for i in range(1, 11)},
        },
    ],
}


EXPECTED_RESULTS = {
    "nem_region_dispatch_metrics": {
        "average_dispatch_price_aud_per_mwh": 60.0,
        "maximum_dispatch_price_aud_per_mwh": 70.0,
        "average_total_demand_mw": 1050.0,
        "estimated_demand_energy_mwh": 175.0,
        "five_minute_interval_count": 2,
    },
    "nem_unit_output_metrics": {
        "average_actual_generation_mw": 4.5,
        "maximum_actual_generation_mw": 12.0,
        "estimated_actual_energy_mwh": 0.75,
        "unit_interval_count": 2,
    },
    "nem_scada_generation_metrics": {
        "average_actual_generation_mw": 45.0,
        "estimated_actual_energy_mwh": 7.5,
        "partially_enriched_observation_count": 1,
    },
    "nem_binding_constraint_metrics": {
        "binding_constraint_interval_count": 2,
        "distinct_binding_constraint_count": 2,
        "average_marginal_value": -0.5,
        "maximum_violation_degree": 0.1,
    },
    "nem_interconnector_flow_metrics": {
        "average_source_sign_flow_mw": 30.0,
        "estimated_source_sign_flow_mwh": 5.0,
        "average_losses_mw": 4.0,
        "estimated_losses_mwh": 2.0 / 3.0,
    },
    "nem_unit_availability_t1_metrics": {
        "average_dispatch_target_mw": 75.0,
        "average_availability_mw": 90.0,
        "estimated_dispatched_energy_mwh": 12.5,
        "mean_absolute_scada_target_variance_mw": 5.0,
    },
    "nem_bid_availability_metrics": {
        "average_maximum_offer_availability_mw": 150.0,
        "average_total_band_availability_mw": 77.5,
        "minimum_price_band_aud_per_mwh": -99.0,
        "bid_period_row_count": 2,
    },
}


def direct_gold_aggregate(view: str, rows: list[dict]) -> dict[str, float]:
    if view in {
        "nem_region_dispatch_metrics",
        "nem_binding_constraint_metrics",
        "nem_interconnector_flow_metrics",
        "nem_unit_availability_t1_metrics",
    }:
        rows = [row for row in rows if row["is_effective_run"]]

    if view == "nem_region_dispatch_metrics":
        return {
            "average_dispatch_price_aud_per_mwh": mean(r["rrp_aud_per_mwh"] for r in rows),
            "maximum_dispatch_price_aud_per_mwh": max(r["rrp_aud_per_mwh"] for r in rows),
            "average_total_demand_mw": mean(r["total_demand_mw"] for r in rows),
            "estimated_demand_energy_mwh": sum(r["total_demand_mw"] for r in rows) * 5 / 60,
            "five_minute_interval_count": len(rows),
        }
    if view == "nem_unit_output_metrics":
        return {
            "average_actual_generation_mw": mean(r["actual_generation_mw"] for r in rows),
            "maximum_actual_generation_mw": max(r["actual_generation_mw"] for r in rows),
            "estimated_actual_energy_mwh": sum(r["actual_generation_mw"] for r in rows) * 5 / 60,
            "unit_interval_count": len(rows),
        }
    if view == "nem_scada_generation_metrics":
        return {
            "average_actual_generation_mw": mean(r["actual_generation_mw"] for r in rows),
            "estimated_actual_energy_mwh": sum(r["actual_generation_mw"] for r in rows) * 5 / 60,
            "partially_enriched_observation_count": sum(r["partially_enriched_facility_count"] > 0 for r in rows),
        }
    if view == "nem_binding_constraint_metrics":
        return {
            "binding_constraint_interval_count": len(rows),
            "distinct_binding_constraint_count": len({r["constraint_id"] for r in rows}),
            "average_marginal_value": mean(r["marginal_value"] for r in rows),
            "maximum_violation_degree": max(r["violation_degree"] for r in rows),
        }
    if view == "nem_interconnector_flow_metrics":
        return {
            "average_source_sign_flow_mw": mean(r["mw_flow"] for r in rows),
            "estimated_source_sign_flow_mwh": sum(r["mw_flow"] for r in rows) * 5 / 60,
            "average_losses_mw": mean(r["mw_losses"] for r in rows),
            "estimated_losses_mwh": sum(r["mw_losses"] for r in rows) * 5 / 60,
        }
    if view == "nem_unit_availability_t1_metrics":
        return {
            "average_dispatch_target_mw": mean(r["total_cleared_mw"] for r in rows),
            "average_availability_mw": mean(r["availability_mw"] for r in rows),
            "estimated_dispatched_energy_mwh": sum(r["total_cleared_mw"] for r in rows) * 5 / 60,
            "mean_absolute_scada_target_variance_mw": mean(r["absolute_scada_dispatch_variance_mw"] for r in rows),
        }
    if view == "nem_bid_availability_metrics":
        band_totals = [sum(r[f"band_availability_{i}_mw"] or 0 for i in range(1, 11)) for r in rows]
        lowest_prices = [min(r[f"price_band_{i}_aud_per_mwh"] for i in range(1, 11)) for r in rows]
        return {
            "average_maximum_offer_availability_mw": mean(r["maximum_availability_mw"] for r in rows),
            "average_total_band_availability_mw": mean(band_totals),
            "minimum_price_band_aud_per_mwh": min(lowest_prices),
            "bid_period_row_count": len(rows),
        }
    raise AssertionError(f"unhandled metric view {view}")


def test_every_measure_expression_is_reconciled_to_its_gold_source() -> None:
    metrics = metric_definitions()
    actual_expressions = {
        view: {measure["name"]: measure["expr"] for measure in definition["measures"]}
        for view, definition in metrics.items()
    }
    assert actual_expressions == EXPECTED_EXPRESSIONS
    assert set(SOURCE_ROWS) == set(EXPECTED_EXPRESSIONS)

    for view, rows in SOURCE_ROWS.items():
        actual = direct_gold_aggregate(view, rows)
        expected = EXPECTED_RESULTS[view]
        assert actual.keys() == expected.keys()
        for measure, expected_value in expected.items():
            assert math.isclose(actual[measure], expected_value, rel_tol=1e-12), (
                view,
                measure,
                actual[measure],
                expected_value,
            )


def test_effective_run_filters_exclude_non_effective_rows_from_reconciliation() -> None:
    metrics = metric_definitions()
    filtered_views = {
        name for name, definition in metrics.items() if definition.get("filter") == "is_effective_run = true"
    }
    assert filtered_views == {
        "nem_region_dispatch_metrics",
        "nem_binding_constraint_metrics",
        "nem_interconnector_flow_metrics",
        "nem_unit_availability_t1_metrics",
    }
    # Each filtered fixture includes an adversarial high-value non-effective row;
    # the reconciled results above prove it contributes to none of the measures.
    assert all(any(not row["is_effective_run"] for row in SOURCE_ROWS[name]) for name in filtered_views)


def test_mw_to_mwh_conversion_is_exactly_five_minutes() -> None:
    energy_expressions = [
        measure["expr"]
        for definition in metric_definitions().values()
        for measure in definition["measures"]
        if measure["name"].endswith("_energy_mwh") or measure["name"].endswith("_flow_mwh") or measure["name"].endswith("_losses_mwh")
    ]
    assert len(energy_expressions) == 6
    assert all("* 5.0 / 60.0" in expression for expression in energy_expressions)
