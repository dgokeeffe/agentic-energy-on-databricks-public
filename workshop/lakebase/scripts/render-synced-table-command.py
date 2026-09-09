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
    # Required, but not pinned to a name. The guardrail in
    # miniwiki/guardrails.md is "use an explicitly named Databricks profile;
    # never select a workspace implicitly" — which argparse's required=True
    # already enforces. Comparing against one hardcoded name added no safety and
    # made the script unusable on any machine without that profile.
    parser.add_argument("--profile", required=True, help="Databricks CLI profile name")
    args = parser.parse_args()
    if not args.profile.strip():
        parser.error("--profile requires a non-empty Databricks CLI profile name")

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
