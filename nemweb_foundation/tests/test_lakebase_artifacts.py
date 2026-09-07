from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def test_lakebase_cdf_pipeline_reads_parameterised_history_without_mutating_it():
    source = (ROOT / "agentic_energy/nemweb/pipeline/lakebase_investigations.py").read_text()
    assert 'spark.conf.get("nemweb.lakebase_cdf_history_table")' in source
    assert "spark.read.table(_HISTORY_TABLE)" in source
    assert 'name="silver_nem_investigations_current"' in source
    assert "_sort_by" in source and "_pg_lsn" in source and "_timestamp" in source
    assert 'F.col("_timestamp").cast("timestamp")' in source
    assert "F.conv(" in source and "4294967296" in source
    assert 'F.col("_pg_lsn").desc()' not in source
    assert "update_preimage" in source and "delete" in source
    for forbidden in ("import dlt", "dp.read", "LIVE.", "apply_changes", "writeStream", "delta.enableChangeDataFeed"):
        assert forbidden not in source


def test_cdf_pipeline_resource_has_no_schedule_and_no_private_identifier():
    document = yaml.safe_load((ROOT / "resources/nemweb_lakebase_cdf.pipeline.yml").read_text())
    pipeline = document["resources"]["pipelines"]["nemweb_lakebase_cdf"]
    assert pipeline["serverless"] is True
    assert pipeline["configuration"]["nemweb.lakebase_cdf_history_table"] == "${var.lakebase_cdf_history_table}"
    assert "trigger" not in pipeline and "schedule" not in pipeline and "continuous" not in pipeline
    text = (ROOT / "databricks.yml").read_text() + str(document)
    assert "https://" not in text
    assert "dapi" not in text.lower()


def test_offline_lakebase_contracts_are_checked_in():
    required = (
        "workshop/lakebase/contracts/region-status.schema.json",
        "workshop/lakebase/contracts/investigation.schema.json",
        "workshop/lakebase/contracts/cdf-event.schema.json",
        "workshop/lakebase/migrations/001_app_write_investigations.sql",
        "workshop/lakebase/synced-table/create-synced-table.json.template",
        "workshop/lakebase/fixtures/investigation-cdf.json",
    )
    assert all((REPO / path).is_file() for path in required)
