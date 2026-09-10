"""Offline contracts for the NEMWEB bundle foundation."""

from __future__ import annotations

import ast
import importlib
import re
import tomllib
from pathlib import Path

import pytest


yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parents[2]


def _yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def _job(path: str, key: str):
    return _yaml(path)["resources"]["jobs"][key]


def test_required_nemweb_bundle_variables_are_parameterised():
    variables = _yaml("databricks.yml")["variables"]
    expected = {
        "warehouse_id",
        "landing_schema",
        "nemweb_mode",
        "critical_lookback_hours",
        "context_lookback_days",
        "max_files_per_cycle",
        "network_timeout_seconds",
        "network_retry_count",
    }
    assert expected <= variables.keys()
    assert variables["catalog"]["default"] == "${workspace.current_user.short_name}"
    assert variables["schema"]["default"] == "agentic_energy_workshop"
    assert variables["app_serving_schema"]["default"] == "${var.schema}_serving"
    assert variables["landing_volume"]["default"] == "nemweb_landing"
    assert variables["warehouse_id"]["default"] == "${resources.sql_warehouses.analytics.id}"
    assert variables["landing_schema"]["default"] == "${var.schema}"
    assert variables["landing_path"]["default"] == "/Volumes/${var.catalog}/${var.landing_schema}/${var.landing_volume}"
    assert variables["nemweb_mode"]["default"] == "snapshot"
    assert variables["critical_lookback_hours"]["default"] == "2"
    assert variables["network_retry_count"]["default"] == "3"
    # Next_Day_Dispatch is T+1 and its filename token is the prior trading day,
    # so the newest available archive is routinely more than 24h old by that
    # token. A window under 3 days makes the required listing look empty and
    # fails the whole context cycle (observed against live NEMWEB 2026-09-02).
    assert int(variables["context_lookback_days"]["default"]) >= 3
    bundle = _yaml("databricks.yml")
    target = bundle["targets"]["live_evidence"]
    assert target["mode"] == "development"
    for key in ("resource_prefix", "schema", "landing_schema", "landing_volume", "app_serving_schema"):
        assert target["variables"][key] == "${var.live_evidence_" + key + "}"
        assert "default" in variables["live_evidence_" + key]
    assert target["variables"]["nemweb_mode"] == "live"
    assert target["variables"]["allow_live_nemweb"] == "true"


def test_bundle_owns_warehouse_and_schemas():
    warehouse = _yaml("resources/nemweb_sql_warehouse.sql_warehouse.yml")["resources"][
        "sql_warehouses"
    ]["analytics"]
    assert warehouse["enable_serverless_compute"] is True
    assert warehouse["warehouse_type"] == "PRO"
    assert warehouse["name"] == "${var.resource_prefix}-sql"
    pipeline = _yaml("resources/nemweb_pipeline.schema.yml")["resources"]["schemas"]["pipeline"]
    serving = _yaml("resources/nemweb_app_serving.schema.yml")["resources"]["schemas"]["app_serving"]
    assert pipeline["name"] == "${var.schema}"
    assert serving["name"] == "${var.app_serving_schema}"
    bundle = _yaml("databricks.yml")
    assert bundle["experimental"]["skip_name_prefix_for_schema"] is True


def test_managed_landing_volume_is_governed_and_parameterised():
    volume = _yaml("resources/nemweb_landing.volume.yml")["resources"]["volumes"][
        "nemweb_landing"
    ]
    assert volume["catalog_name"] == "${var.catalog}"
    assert volume["schema_name"] == "${var.landing_schema}"
    assert volume["name"] == "${var.landing_volume}"
    landing_path = _yaml("databricks.yml")["variables"]["landing_path"]["default"]
    assert landing_path == "/Volumes/${var.catalog}/${var.landing_schema}/${var.landing_volume}"
    assert volume["volume_type"] == "MANAGED"
    assert volume["lifecycle"]["prevent_destroy"] is True
    # Grant principals are their own variables because bundle grant lists MERGE
    # across target overrides instead of replacing, and because Unity Catalog
    # resolves only account-level principals while workspace-local groups remain
    # valid for Job/Pipeline ACLs. They default to the participant/facilitator
    # groups in databricks.yml.
    assert {grant["principal"] for grant in volume["grants"]} == {
        "${var.volume_reader_principal}",
        "${var.volume_writer_principal}",
    }


def test_pipeline_is_serverless_triggered_and_includes_all_source_files():
    pipeline = _yaml("resources/nemweb.pipeline.yml")["resources"]["pipelines"][
        "nemweb"
    ]
    assert pipeline["serverless"] is True
    assert pipeline["catalog"] == "${var.catalog}"
    assert pipeline["schema"] == "${var.schema}"
    assert "continuous" not in pipeline
    assert "trigger" not in pipeline
    assert "target" not in pipeline
    assert pipeline["root_path"] == ".."
    assert {
        Path(library["file"]["path"]).name for library in pipeline["libraries"]
    } == {
        "parsed_records.py",
        "bronze_dispatchis.py",
        "bronze_scada.py",
        "bronze_unit_solution.py",
        "bronze_registration.py",
        "silver_region_dispatch.py",
        "silver_scada.py",
        "silver_constraints.py",
        "silver_interconnectors.py",
        "silver_unit_solution.py",
        "silver_facilities.py",
        "gold_region_dispatch.py",
        "gold_unit_dispatch.py",
        "gold_scada_generation.py",
        "gold_constraints.py",
        "gold_interconnectors.py",
        "gold_unit_solution.py",
        "gold_app_region_status.py",
        "gold_additional_aggregates.py",
        "bronze_bids.py",
        "silver_bids.py",
        "gold_bids.py",
        "bronze_trading.py",
        "silver_trading.py",
        "gold_trading.py",
        "bronze_settlement.py",
        "silver_settlement.py",
        "gold_settlement.py",
    }
    assert all("glob" not in library for library in pipeline["libraries"])
    assert (ROOT / "agentic_energy/nemweb/pipeline/__init__.py").is_file()


def test_all_25_bronze_and_silver_tables_enable_row_tracking_and_cdf():
    sources = list((ROOT / "agentic_energy/nemweb/pipeline").glob("bronze_*.py")) + list(
        (ROOT / "agentic_energy/nemweb/pipeline").glob("silver_*.py")
    )
    declarations = []
    for source in sources:
        tree = ast.parse(source.read_text(), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                if decorator.func.attr not in {"table", "materialized_view"}:
                    continue
                properties = next((keyword.value for keyword in decorator.keywords if keyword.arg == "table_properties"), None)
                if not isinstance(properties, ast.Dict):
                    continue
                values = {
                    key.value: value.value
                    for key, value in zip(properties.keys, properties.values)
                    if isinstance(key, ast.Constant) and isinstance(value, ast.Constant)
                }
                declarations.append((source.name, values))
    assert len(declarations) == 25
    for source, properties in declarations:
        assert properties.get("delta.enableRowTracking") == "true", source
        assert properties.get("delta.enableChangeDataFeed") == "true", source


def test_pipeline_sources_reject_legacy_dlt_apis():
    sources = list((ROOT / "agentic_energy/nemweb/pipeline").glob("*.py"))
    assert sources
    forbidden = {
        "import dlt": re.compile(r"(?:^|\n)\s*(?:from\s+dlt\s+|import\s+dlt\b)"),
        "dlt.read": re.compile(r"\bdlt\.read(?:_stream)?\s*\("),
        "dp.read": re.compile(r"\bdp\.read(?:_stream)?\s*\("),
        "LIVE prefix": re.compile(r"\bLIVE\."),
        "CREATE LIVE": re.compile(r"\bCREATE\s+(?:STREAMING\s+)?LIVE\b", re.I),
        "old apply_changes": re.compile(r"\b(?:dlt|dp)\.apply_changes\s*\("),
    }
    for source in sources:
        text = source.read_text()
        for label, pattern in forbidden.items():
            assert not pattern.search(text), f"{label} in {source.relative_to(ROOT)}"


def test_five_minute_refresh_selects_only_critical_datasets():
    job = _job("resources/nemweb_refresh.job.yml", "nemweb_refresh")
    task = next(t for t in job["tasks"] if t["task_key"] == "publish_medallion")
    selection = task["pipeline_task"]["refresh_selection"]
    # The app slice combines SCADA with regional price/demand. Constraints,
    # interconnectors, and slower domains remain outside the five-minute update.
    assert selection == [
        "bronze_nem_dispatch_price",
        "bronze_nem_dispatch_region_sum",
        "bronze_nem_dispatch_unit_scada",
        "silver_nem_region_dispatch",
        "silver_nem_dispatch_unit_scada",
        "silver_nem_facility_dimension",
        "gold_nem_region_dispatch_5min",
        "gold_nem_unit_dispatch_5min",
        "gold_nem_scada_generation_5min",
    ]
    assert task["pipeline_task"]["full_refresh"] is False
    assert "full_refresh_selection" not in task["pipeline_task"]


def test_five_minute_refresh_is_paused_ordered_and_non_destructive():
    job = _job("resources/nemweb_refresh.job.yml", "nemweb_refresh")
    assert job["max_concurrent_runs"] == 1
    assert job["queue"] == {"enabled": True}
    assert job["trigger"] == {
        "pause_status": "PAUSED",
        "quartz_cron_expression": "0 0/5 * * * ?",
        "timezone_id": "Australia/Brisbane",
    }
    tasks = {task["task_key"]: task for task in job["tasks"]}
    assert set(tasks) == {
        "land_current",
        "publish_medallion",
        "capture_cycle_evidence",
    }
    assert tasks["land_current"]["run_job_task"]["job_id"] == (
        "${resources.jobs.nemweb_lander.id}"
    )
    assert tasks["publish_medallion"]["depends_on"] == [
        {"task_key": "land_current"}
    ]
    pipeline_task = tasks["publish_medallion"]["pipeline_task"]
    assert pipeline_task["pipeline_id"] == "${resources.pipelines.nemweb.id}"
    assert pipeline_task["full_refresh"] is False
    # Selective refresh keeps the cycle inside its cadence; asserted in detail by
    # test_five_minute_refresh_selects_only_critical_datasets.
    assert pipeline_task["refresh_selection"]
    assert tasks["capture_cycle_evidence"]["run_if"] == "ALL_DONE"
    assert tasks["capture_cycle_evidence"]["depends_on"] == [
        {"task_key": "land_current"},
        {"task_key": "publish_medallion"},
    ]


def test_lander_is_bounded_unscheduled_and_uses_unique_cycle_id():
    job = _job("resources/nemweb_lander.job.yml", "nemweb_lander")
    # The shared lander must NOT be serialised to a single run: the five-minute
    # job and the daily context job both call it, and serialising made a critical
    # cycle wait 325s behind another caller and time out. Landing is
    # content-addressed and write-once, so concurrent runs are safe. Cycle
    # overlap is prevented on nemweb_refresh instead.
    assert job["max_concurrent_runs"] > 1
    assert job["queue"] == {"enabled": True}
    assert "schedule" not in job and "trigger" not in job and "continuous" not in job
    task = job["tasks"][0]
    # The shared lander Job carries an outer safety bound because one Job serves
    # both the five-minute critical scope and the much heavier daily context
    # scope, and a task timeout cannot be overridden by a run_job_task caller.
    # The cadence-protecting bound is asserted on the calling task below.
    assert task["timeout_seconds"] == 3600
    refresh = _yaml("resources/nemweb_refresh.job.yml")["resources"]["jobs"][
        "nemweb_refresh"
    ]
    land_task = next(
        item for item in refresh["tasks"] if item["task_key"] == "land_current"
    )
    # Queue delay counts against the caller timeout. Keep enough headroom for
    # three queued evidence cycles, but remain below the shared lander's outer
    # one-hour network safety bound.
    assert land_task["timeout_seconds"] == 1200
    assert land_task["timeout_seconds"] < task["timeout_seconds"]
    assert task["max_retries"] == 0
    assert task["spark_python_task"]["python_file"] == "../scripts/land_nemweb_delta.py"
    spark_script = (ROOT / "scripts/land_nemweb_delta.py").read_text()
    assert "raise SystemExit(main())" not in spark_script
    assert 'raise RuntimeError(f"NEMWEB Delta landing failed' in spark_script
    parameters = task["spark_python_task"]["parameters"]
    assert parameters[parameters.index("--cycle-id") + 1] == "{{job.run_id}}"
    assert "${var.max_files_per_cycle}" in parameters
    assert "${var.network_timeout_seconds}" in parameters
    assert "${var.network_retry_count}" in parameters


def test_daily_context_refresh_is_paused_and_source_appropriate():
    job = _job("resources/nemweb_context_refresh.job.yml", "nemweb_context_refresh")
    assert job["max_concurrent_runs"] == 1
    assert job["queue"] == {"enabled": True}
    assert job["schedule"] == {
        "quartz_cron_expression": "0 0 2 * * ?",
        "timezone_id": "Australia/Brisbane",
        "pause_status": "PAUSED",
    }
    land = job["tasks"][0]["run_job_task"]
    assert land["job_parameters"]["scope"] == "context"
    assert job["tasks"][1]["pipeline_task"]["full_refresh"] is False


def test_legacy_job_is_manual_fixture_only():
    job = _job(
        "resources/agentic_energy_job.job.yml", "agentic_energy_local_fixture"
    )
    assert "schedule" not in job and "trigger" not in job and "continuous" not in job
    task = job["tasks"][0]
    assert task["task_key"] == "local_fixture_demo"
    assert task["python_wheel_task"]["entry_point"] == "local-fixture"
    parameters = task["python_wheel_task"]["parameters"]
    assert parameters[parameters.index("--mode") + 1] == "fixture"
    output = parameters[parameters.index("--output") + 1]
    assert output.endswith("/legacy-fixture/runs/{{job.run_id}}")


def test_primary_and_legacy_console_scripts_are_distinct():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    scripts = pyproject["project"]["scripts"]
    assert scripts["agentic-energy"] == "agentic_energy.cli:main"
    assert scripts["agentic-energy-local-fixture"] == "agentic_energy.legacy_cli:main"
    assert importlib.import_module("agentic_energy.nemweb")
    assert importlib.import_module("agentic_energy.nemweb.pipeline")


def test_resources_contain_no_secret_or_private_workspace_configuration():
    text = "\n".join(
        path.read_text()
        for path in (ROOT / "resources").glob("*.yml")
        if "nemweb" in path.name or path.name == "agentic_energy_job.job.yml"
    )
    assert "DATABRICKS_TOKEN" not in text
    assert "dapi" not in text.lower()
    assert "https://" not in text
    assert "0aee324ba8546f28" not in text
    assert "/Workspace/Users/" not in text
