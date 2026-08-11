#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["psycopg[binary]>=3.1"]
# ///
"""Apply the idempotent Lakebase control-plane schema to a Database Instance.

Self-contained: the PEP 723 header above means `uv run` installs psycopg into an
ephemeral environment, so this needs no repo dependency and never touches the
wheel's runtime requirements.

    scripts/lakebase_migrate.py <instance-name> [--database databricks_postgres]
    scripts/lakebase_migrate.py <instance-name> --check   # verify only

Authentication is OAuth, not a stored password: the Postgres role is the
authenticated Databricks identity and the password is a short-lived token from
`databricks database generate-database-credential` (~1 hour). Nothing durable is
written to disk, and there is no secret to rotate or leak. The identity must
already exist as a Postgres role in the instance; the instance creator does.

`resources/lakebase/control_plane.sql` is written to be re-runnable
(CREATE ... IF NOT EXISTS), so this is safe to apply repeatedly. It is
deliberately not part of `bundle deploy`: schema migrations are versioned
artifacts with their own review, not a side effect of shipping code.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = REPO_ROOT / "resources" / "lakebase" / "control_plane.sql"

# Tables control_plane.sql is expected to define, used for the post-apply check.
EXPECTED_TABLES = {
    "source_metadata",
    "metadata_versions",
    "pipeline_runs",
    "pipeline_run_sources",
}
SCHEMA = "agentic_energy"


def _cli_json(*args: str) -> dict:
    """Run the Databricks CLI and parse its JSON output."""
    proc = subprocess.run(
        ["databricks", *args, "-o", "json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"databricks {' '.join(args)} failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def connect(instance: str, database: str) -> psycopg.Connection:
    instance_info = _cli_json("database", "get-database-instance", instance)
    if instance_info.get("state") != "AVAILABLE":
        sys.exit(
            f"instance {instance} is {instance_info.get('state')}, not AVAILABLE. "
            "A stopped instance must be started before it accepts connections."
        )
    credential = _cli_json(
        "database",
        "generate-database-credential",
        "--json",
        json.dumps({"instance_names": [instance]}),
    )
    identity = _cli_json("current-user", "me")["userName"]
    return psycopg.connect(
        host=instance_info["read_write_dns"],
        dbname=database,
        user=identity,
        password=credential["token"],
        sslmode="require",
        connect_timeout=30,
    )


def check(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "select table_name from information_schema.tables where table_schema = %s",
            (SCHEMA,),
        )
        found = {row[0] for row in cur.fetchall()}
    missing = EXPECTED_TABLES - found
    for table in sorted(EXPECTED_TABLES):
        print(f"  {'ok  ' if table in found else 'MISS'} {SCHEMA}.{table}")
    extra = found - EXPECTED_TABLES
    if extra:
        print(f"  (also present: {', '.join(sorted(extra))})")
    if missing:
        print(f"missing: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", help="Database Instance name")
    parser.add_argument("--database", default="databricks_postgres")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the schema without applying it",
    )
    args = parser.parse_args()

    with connect(args.instance, args.database) as conn:
        if not args.check:
            sql = SQL_PATH.read_text()
            # One transaction: a partially applied control plane is worse than
            # none, and every statement in the artifact is idempotent.
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print(f"applied {SQL_PATH.relative_to(REPO_ROOT)} to {args.instance}")
        print(f"schema {SCHEMA} in {args.instance}/{args.database}:")
        return check(conn)


if __name__ == "__main__":
    sys.exit(main())
