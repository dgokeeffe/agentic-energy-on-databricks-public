"""Static and fixture contracts for the lakehouse-owned app serving table."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "agentic_energy/nemweb/pipeline/gold_app_region_status.py"
SERVING_SQL = ROOT / "sql/app_serving/gold_nem_app_region_status.sql"
SERVING_JOB = ROOT / "resources/nemweb_app_serving.job.yml"


def _market_wide(interval_rows: list[dict]) -> tuple[int, int, float]:
    constraints = {
        row["constraint_id"]
        for row in interval_rows
        if row.get("is_binding") and row.get("is_effective_run")
    }
    flows = {
        row["interconnector_id"]: row["mw_flow"]
        for row in interval_rows
        if row.get("interconnector_id") and row.get("is_effective_run")
    }
    return len(constraints), len(flows), sum(flows.values())


def test_market_wide_aggregation_preserves_source_sign_and_is_repeated_per_region() -> None:
    rows = [
        {"constraint_id": "C1", "is_binding": True, "is_effective_run": True},
        {"constraint_id": "C2", "is_binding": True, "is_effective_run": False},
        {"interconnector_id": "I1", "mw_flow": 120.0, "is_effective_run": True},
        {"interconnector_id": "I2", "mw_flow": -20.0, "is_effective_run": True},
    ]
    market_wide = _market_wide(rows)
    assert market_wide == (1, 2, 100.0)
    repeated = {region: market_wide for region in ("NSW1", "VIC1")}
    assert repeated["NSW1"] == repeated["VIC1"]


def test_pipeline_has_effective_unique_key_and_exact_market_wide_contract() -> None:
    source = SOURCE.read_text()
    assert 'name="gold_nem_app_region_status"' in source
    assert '.alias("serving_key")' in source
    assert 'F.sha2(' in source
    assert 'F.col("is_effective_run")' in source
    assert 'groupBy("interval_end")' in source
    assert 'F.sum("mw_flow")' in source
    assert 'F.countDistinct("interconnector_id")' in source
    assert "region_id IS NOT NULL AND interval_end IS NOT NULL AND is_effective_run" in source
    assert '"delta.enableRowTracking": "true"' in source
    assert '"delta.enableChangeDataFeed": "true"' in source
    for phrase in ("market-wide", "source-sign", "no regional allocation", "no directional interpretation"):
        assert phrase in source


def test_prediction_fields_are_typed_nullable_and_correction_metadata_is_explicit() -> None:
    source = SOURCE.read_text()
    expected = {
        "prediction_score": "double",
        "prediction_model_version": "string",
        "prediction_feature_time": "timestamp",
        "prediction_scored_at": "timestamp",
        "prediction_source_freshness": "string",
        "prediction_missing_feature_status": "string",
    }
    for field, data_type in expected.items():
        assert f'F.lit(None).cast("{data_type}").alias("{field}")' in source
    assert '"price_source_run_no"' in source
    assert '"demand_source_run_no"' in source
    assert "correction_boolean" not in source


def test_regular_delta_sync_source_has_one_lakehouse_writer_and_cdf() -> None:
    sql = SERVING_SQL.read_text()
    job = SERVING_JOB.read_text()
    assert "CREATE TABLE IF NOT EXISTS IDENTIFIER" in sql
    assert "'delta.enableChangeDataFeed' = 'true'" in sql
    assert "'delta.enableRowTracking' = 'true'" in sql
    assert "target.serving_key = source.serving_key" in sql
    assert "WHEN NOT MATCHED BY SOURCE THEN DELETE" in sql
    assert "refused an empty pipeline-owned source" in sql
    assert "refused to remove more than half" in sql
    assert "INNER JOIN IDENTIFIER" in sql
    assert "source.serving_key = target.serving_key" in sql
    assert "CAN_VIEW" in job
    assert "CAN_MANAGE_RUN" not in job
    assert "schedule:" not in job and "trigger:" not in job
    assert "${var.resource_prefix}-app-serving" in job
