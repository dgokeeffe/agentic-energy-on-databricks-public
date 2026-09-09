from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / "sql/app_serving/gold_nem_scada_generation_5min.sql"
JOB = ROOT / "resources/nemweb_app_serving.job.yml"


def test_generation_serving_is_mode_explicit_and_fail_closed():
    sql = SQL.read_text()
    assert "CAST(:source_mode AS STRING) AS source_mode" in sql
    assert "data.classification' = 'mode_explicit" in sql
    assert "refused an empty pipeline-owned generation source" in sql
    assert "refused to remove more than half" in sql
    assert "interval_end = source.interval_end" in sql
    assert "region_id = source.region_id" in sql
    assert "fuel_type = source.fuel_type" in sql


def test_serving_job_publishes_both_tables_sequentially():
    text = JOB.read_text()
    assert text.count("source_mode: ${var.nemweb_mode}") == 2
    assert "publish_regular_delta_source" in text
    assert "publish_generation_source" in text
