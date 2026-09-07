from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_triggered_synced_table_contract_is_parameterised_and_lakehouse_owned():
    path = ROOT / "synced-table/create-synced-table.json.template"
    text = path.read_text()
    spec = json.loads(text)["spec"]
    assert spec["source_table_full_name"].endswith(".gold_nem_app_region_status")
    assert spec["primary_key_columns"] == ["serving_key"]
    assert spec["scheduling_policy"] == "TRIGGERED"
    assert spec["branch"] == "projects/${LAKEBASE_PROJECT}/branches/${LAKEBASE_BRANCH}"
    assert spec["postgres_database"] == "${LAKEBASE_DATABASE_NAME}"
    assert spec["create_database_objects_if_missing"] is True
    assert spec["new_pipeline_spec"] == {
        "storage_catalog": "${UC_STORAGE_CATALOG}",
        "storage_schema": "${UC_STORAGE_SCHEMA}",
    }
    for forbidden in (
        "https://",
        "adb-",
        "dapi",
        "synced_database_tables",
        "database_instance_name",
        "production",
    ):
        assert forbidden not in text


def test_renderer_uses_current_postgres_cli_and_is_dry_run_by_default():
    script = (ROOT / "scripts/render-synced-table-command.py").read_text()
    assert "postgres create-synced-table" in script
    assert "subprocess" not in script
    assert "--profile" in script
