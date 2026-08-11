"""Offline checks on the Lakebase control-plane artifacts.

The migration script verifies a table list after applying the SQL. If someone
adds a table to control_plane.sql and forgets the script, the apply silently
"succeeds" while the check no longer covers the new table. These tests keep the
two in step without needing a Database Instance.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL = (REPO_ROOT / "resources" / "lakebase" / "control_plane.sql").read_text()
SCRIPT = (REPO_ROOT / "scripts" / "lakebase.py").read_text()

SCHEMA = "agentic_energy"


def tables_in_sql():
    return set(
        re.findall(
            rf"CREATE TABLE IF NOT EXISTS\s+{SCHEMA}\.(\w+)", SQL, flags=re.IGNORECASE
        )
    )


def tables_in_migrate():
    block = SCRIPT.split("EXPECTED_TABLES = {", 1)[1].split("}", 1)[0]
    return set(re.findall(r'"(\w+)"', block))


def test_sql_declares_tables():
    assert tables_in_sql(), "no CREATE TABLE statements found — check the artifact"


def test_migration_check_covers_every_table():
    assert tables_in_migrate() == tables_in_sql()


def test_sql_is_idempotent():
    """Every DDL statement must be re-runnable; the script applies it repeatedly."""
    creates = re.findall(r"^\s*CREATE\s+(\w+)(.*)$", SQL, flags=re.MULTILINE)
    for kind, rest in creates:
        assert "IF NOT EXISTS" in rest.upper(), (
            f"CREATE {kind}{rest.rstrip()} is not idempotent"
        )


def test_migrate_script_is_self_contained():
    """PEP 723 header: `uv run` supplies psycopg, so it is not a repo dependency."""
    assert "# /// script" in SCRIPT
    assert "psycopg" in SCRIPT.split("# ///")[1]
    assert "psycopg" not in (REPO_ROOT / "pyproject.toml").read_text()
