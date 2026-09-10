from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("validate_nemweb_genie", SCRIPTS / "validate_nemweb_genie.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

BENCHMARKS = json.loads((ROOT / "genie/benchmark_questions.json").read_text())["benchmarks"]


def test_benchmark_catalog_covers_every_required_question() -> None:
    assert {item["id"] for item in BENCHMARKS} == validator.REQUIRED_TOPICS
    assert len(BENCHMARKS) == 7
    for item in BENCHMARKS:
        assert item["question"]
        assert item["expected_columns"]
        assert item["explanation"]
        assert "result_expectation" in item
        sql = (ROOT / item["sql_file"]).read_text()
        assert "{{catalog}}.{{schema}}." in sql
        assert ";" not in sql.rstrip().rstrip(";")


def test_benchmarks_encode_semantics_not_only_table_presence() -> None:
    sql_by_id = {item["id"]: (ROOT / item["sql_file"]).read_text().lower() for item in BENCHMARKS}
    assert "count_if(is_effective_run)" in sql_by_id["effective-intervention-uniqueness"]
    assert "having count_if(is_effective_run) <> 1" in sql_by_id["effective-intervention-uniqueness"]
    assert BENCHMARKS[0]["result_expectation"] == {"row_count": 0}
    assert "nem_region_dispatch_metrics" in sql_by_id["regional-price-demand"]
    assert "nem_scada_generation_metrics" in sql_by_id["generation-by-fuel"]
    assert "nem_binding_constraint_metrics" in sql_by_id["binding-constraints"]
    assert "source_sign" in sql_by_id["interconnector-source-sign"]
    assert "nem_unit_availability_t1_metrics" in sql_by_id["t1-unit-availability"]
    spikes = sql_by_id["regional-price-spikes"]
    assert "nem_dispatch_price_spike_metrics" in spikes
    # A spike count alone cannot distinguish "no spike" from "no data", and a
    # spike without freshness cannot be acted on. Both must be in the answer.
    assert "measure(five_minute_interval_count)" in spikes
    assert "measure(stale_price_spike_interval_count)" in spikes
    assert "max(source_publication_at)" in spikes and "max(gold_published_at)" in spikes
    assert "spike_threshold_aud_per_mwh" in spikes
    # Zero spikes is a valid answer, so this benchmark must not demand a row.
    by_id = {item["id"]: item for item in BENCHMARKS}
    assert by_id["regional-price-spikes"]["result_expectation"] == {"minimum_row_count": 0}


def test_template_rendering_is_bounded_and_complete() -> None:
    rendered = validator.render_benchmark_sql(
        "SELECT * FROM {{catalog}}.{{schema}}.asset", "daveok", "nemweb_dev"
    )
    assert rendered == "SELECT * FROM daveok.nemweb_dev.asset"
    with pytest.raises(ValueError, match="simple Databricks identifiers"):
        validator.render_benchmark_sql("SELECT 1", "bad.catalog", "schema")


def test_sql_gate_rejects_failed_terminal_state_even_after_successful_transport() -> None:
    def fake_cli(_args: list[str]) -> dict:
        return {
            "statement_id": "statement-for-test",
            "status": {"state": "FAILED", "error": {"message": "analysis failed"}},
        }

    with pytest.raises(RuntimeError, match="ended in FAILED"):
        validator.execute_statement(
            "SELECT 1",
            profile="DEFAULT",
            warehouse_id="warehouse",
            catalog="catalog",
            schema="schema",
            timeout_seconds=1,
            cli_runner=fake_cli,
        )


def test_result_contract_checks_terminal_result_columns_and_counts() -> None:
    item = BENCHMARKS[0]
    response = {
        "statement_id": "statement-for-test",
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": name} for name in item["expected_columns"]]}},
        "result": {"row_count": 0, "data_array": []},
    }
    validator._check_benchmark_result(item, response)
    response["result"]["row_count"] = 1
    with pytest.raises(RuntimeError, match="row count"):
        validator._check_benchmark_result(item, response)


def test_static_asset_validator_reconciles_all_files() -> None:
    # The validator no longer pins a profile name. It carries the explicit-profile
    # requirement as an error message instead, so no operator's workspace name is
    # embedded in this repository.
    assert not hasattr(validator, "REQUIRED_PROFILE")
    assert "explicit --profile" in validator.PROFILE_REQUIRED_MESSAGE
    result = validator.validate_assets()
    assert len(result["benchmarks"]) == 7
    assert len(result["dashboard_sql"]) == 7
    # The Genie asset set is deliberately unchanged: adding the spike measure to
    # the analyst space is a separate scoping decision, not part of this measure.
    assert result["genie_asset_count"] == 6
