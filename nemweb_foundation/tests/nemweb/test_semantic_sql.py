from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
SEMANTICS = (ROOT / "sql/nemweb_semantics.sql").read_text()
METRICS = (ROOT / "sql/nemweb_metric_views.sql").read_text()
RESOURCE = yaml.safe_load((ROOT / "resources/nemweb_semantics.job.yml").read_text())


def metric_definitions() -> dict[str, dict]:
    pattern = re.compile(
        r"CREATE OR REPLACE VIEW\s+(\w+)\s+WITH METRICS\s+LANGUAGE YAML\s+AS \$\$(.*?)\$\$;",
        re.DOTALL | re.IGNORECASE,
    )
    return {name: yaml.safe_load(body) for name, body in pattern.findall(METRICS)}


def test_semantic_job_is_manual_parameterised_and_dependency_ordered() -> None:
    job = RESOURCE["resources"]["jobs"]["nemweb_semantics"]
    assert "schedule" not in job and "trigger" not in job
    assert job["max_concurrent_runs"] == 1
    assert job["queue"]["enabled"] is True
    assert [task["task_key"] for task in job["tasks"]] == [
        "validate_and_apply_comments",
        "create_metric_views",
    ]
    assert job["tasks"][1]["depends_on"] == [
        {"task_key": "validate_and_apply_comments"}
    ]
    for task, filename in zip(
        job["tasks"], ("nemweb_semantics.sql", "nemweb_metric_views.sql"), strict=True
    ):
        sql_task = task["sql_task"]
        assert sql_task["warehouse_id"] == "${var.warehouse_id}"
        assert sql_task["file"] == {
            "path": f"${{workspace.file_path}}/sql/{filename}",
            "source": "WORKSPACE",
        }
        assert sql_task["parameters"] == {
            "catalog": "${var.catalog}",
            "schema": "${var.schema}",
        }


def test_semantic_sql_checks_every_candidate_key_before_comments() -> None:
    expected_errors = {
        "gold_nem_region_dispatch_5min candidate key is not unique",
        "gold_nem_unit_dispatch_5min candidate key is not unique",
        "gold_nem_scada_generation_5min candidate key is not unique",
        "gold_nem_binding_constraints_5min candidate key is not unique",
        "gold_nem_interconnector_flows_5min candidate key is not unique",
        "gold_nem_unit_dispatch_availability_t1 candidate key is not unique",
        "silver_nem_facility_dimension candidate key is not unique",
        "gold_nem_bid_stack candidate key is not unique",
    }
    for error in expected_errors:
        assert error in SEMANTICS
    assert SEMANTICS.index("SELECT assert_true") < SEMANTICS.index("COMMENT ON TABLE")
    assert "HAVING COUNT(*) > 1" in SEMANTICS
    assert "unit_rows_without_facility_dimension" in SEMANTICS
    assert "t1_rows_without_facility_dimension" in SEMANTICS


def test_relationships_are_honest_for_lakeflow_materialized_views() -> None:
    # PK/FK DDL is unsupported on these Lakeflow materialized views. The SQL must
    # not claim enforcement; it verifies uniqueness and documents nullable joins.
    upper = SEMANTICS.upper()
    assert "ADD CONSTRAINT" not in upper
    assert "DO NOT SUPPORT DECLARATIVE PRIMARY KEY / FOREIGN KEY" in upper
    assert "LEFT JOIN SILVER_NEM_FACILITY_DIMENSION" in upper
    assert "UNKNOWN ENRICHMENT IS INTENTIONAL" in upper

    metrics = metric_definitions()
    unit_join = metrics["nem_unit_output_metrics"]["joins"]
    assert unit_join == [
        {
            "name": "facility",
            "source": "silver_nem_facility_dimension",
            "on": "source.duid = facility.duid",
        }
    ]


def test_comments_encode_all_required_market_semantics() -> None:
    lower = SEMANTICS.lower()
    required = [
        "aud/mwh",
        "mw",
        "interval-ending",
        "aest (utc+10",
        "no daylight saving",
        "dispatch, not settlement",
        "is_effective_run",
        "must never aggregate runs blindly",
        "aemo source sign",
        "actual scada",
        "never dispatch target",
        "daily t+1",
        "unknown",
        "freshness",
    ]
    for phrase in required:
        assert phrase in lower, phrase

    for relation in (
        "gold_nem_region_dispatch_5min",
        "gold_nem_unit_dispatch_5min",
        "gold_nem_scada_generation_5min",
        "gold_nem_binding_constraints_5min",
        "gold_nem_interconnector_flows_5min",
        "gold_nem_unit_dispatch_availability_t1",
        "silver_nem_facility_dimension",
        "gold_nem_bid_stack",
    ):
        assert f"COMMENT ON TABLE {relation}" in SEMANTICS


def test_metric_yaml_uses_supported_v11_shape_and_curated_sources() -> None:
    metrics = metric_definitions()
    expected = {
        "nem_region_dispatch_metrics": "gold_nem_region_dispatch_5min",
        "nem_unit_output_metrics": "gold_nem_unit_dispatch_5min",
        "nem_scada_generation_metrics": "gold_nem_scada_generation_5min",
        "nem_binding_constraint_metrics": "gold_nem_binding_constraints_5min",
        "nem_interconnector_flow_metrics": "gold_nem_interconnector_flows_5min",
        "nem_unit_availability_t1_metrics": "gold_nem_unit_dispatch_availability_t1",
        "nem_bid_availability_metrics": "gold_nem_bid_stack",
    }
    assert {name: definition["source"] for name, definition in metrics.items()} == expected
    for definition in metrics.values():
        assert definition["version"] == 1.1
        assert definition["comment"]
        assert definition["dimensions"] and definition["measures"]
        assert all({"name", "expr", "comment"} <= item.keys() for item in definition["dimensions"])
        assert all({"name", "expr", "comment"} <= item.keys() for item in definition["measures"])


def test_intervention_metric_views_filter_effective_runs() -> None:
    metrics = metric_definitions()
    for name in (
        "nem_region_dispatch_metrics",
        "nem_binding_constraint_metrics",
        "nem_interconnector_flow_metrics",
        "nem_unit_availability_t1_metrics",
    ):
        assert metrics[name]["filter"] == "is_effective_run = true"
        assert "effective" in metrics[name]["comment"].lower()


def test_metric_yaml_distinguishes_source_cadence_units_sign_and_freshness() -> None:
    metrics = metric_definitions()
    all_text = yaml.safe_dump(metrics).lower()
    for phrase in (
        "aud/mwh",
        "fixed aest",
        "interval-ending",
        "effective-run",
        "aemo source sign",
        "unknown",
        "source publication",
        "gold publication",
        "daily t+1",
        "never dispatch target",
        "estimated signed mwh",
    ):
        assert phrase in all_text, phrase
