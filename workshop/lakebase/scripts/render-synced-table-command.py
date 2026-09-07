#!/usr/bin/env python3
"""Render, but never execute, the current Lakebase synced-table CLI command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
from string import Template

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    if args.profile != "daveok":
        parser.error("--profile daveok is required")

    resources = json.loads(args.resources.read_text())
    required = {
        "synced_table_id",
        "uc_catalog",
        "uc_schema",
        "lakebase_project",
        "lakebase_branch",
        "lakebase_database_name",
        "storage_catalog",
        "storage_schema",
    }
    missing = sorted(required - resources.keys())
    if missing:
        parser.error(f"missing resource fields: {', '.join(missing)}")

    template = Template((ROOT / "synced-table/create-synced-table.json.template").read_text())
    body = template.substitute(
        UC_CATALOG=resources["uc_catalog"],
        UC_SCHEMA=resources["uc_schema"],
        LAKEBASE_PROJECT=resources["lakebase_project"],
        LAKEBASE_BRANCH=resources["lakebase_branch"],
        LAKEBASE_DATABASE_NAME=resources["lakebase_database_name"],
        UC_STORAGE_CATALOG=resources["storage_catalog"],
        UC_STORAGE_SCHEMA=resources["storage_schema"],
    )
    json.loads(body)
    print(
        "databricks postgres create-synced-table "
        f"{shlex.quote(resources['synced_table_id'])} --json @<rendered-json> "
        f"--no-wait --profile {shlex.quote(args.profile)}"
    )
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
