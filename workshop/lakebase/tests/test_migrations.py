from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def _normalised_columns(sql: str) -> set[str]:
    body = re.search(r"CREATE TABLE IF NOT EXISTS app_write\.investigations\s*\((.*?)\);", sql, re.S | re.I)
    assert body
    return {
        line.strip().split()[0].lower()
        for line in body.group(1).splitlines()
        if line.strip() and not line.lstrip().upper().startswith(("CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK"))
    }


def test_canonical_migration_is_idempotent_non_destructive_and_cdf_ready():
    sql = (ROOT / "migrations/001_app_write_investigations.sql").read_text()
    assert "CREATE SCHEMA IF NOT EXISTS app_write" in sql
    assert "CREATE TABLE IF NOT EXISTS app_write.investigations" in sql
    assert "UUID PRIMARY KEY" in sql
    assert "REPLICA IDENTITY FULL" in sql
    assert "DROP " not in sql.upper()
    for column in (
        "investigation_id", "nem_event_key", "region_id", "interval_end",
        "operator_identity", "team_identifier", "status", "decision",
        "evidence_reference", "created_at", "updated_at", "version",
    ):
        assert column in _normalised_columns(sql)


def test_application_schema_matches_canonical_migration():
    canonical = (ROOT / "migrations/001_app_write_investigations.sql").read_text()
    app_schema = (REPO / "nemweb_app/server/db/schema.ts").read_text()
    embedded = re.search(r"INVESTIGATIONS_MIGRATION = `(.+?)`;", app_schema, re.S)
    assert embedded
    assert _normalised_columns(embedded.group(1)) == _normalised_columns(canonical)
    assert "REPLICA IDENTITY FULL" in embedded.group(1)
    assert "DROP " not in embedded.group(1).upper()


def test_least_privilege_template_revokes_synced_table_writes():
    sql = (ROOT / "migrations/002_app_read_least_privilege.sql.template").read_text()
    assert "GRANT SELECT" in sql
    for privilege in ("INSERT", "UPDATE", "DELETE"):
        assert privilege in sql
    assert ":app_principal" in sql
