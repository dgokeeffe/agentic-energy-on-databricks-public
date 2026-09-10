#!/usr/bin/env python3
"""Validate NEMWEB Genie/benchmark/dashboard assets and optionally execute SQL.

Static validation is offline. ``--execute`` submits every canonical benchmark
and every dashboard dataset through the SQL Statement Execution API, polls its
statement ID, and fails unless each statement reaches SUCCEEDED. A Databricks
CLI process exit code is treated only as transport evidence, never as query
success. This script does not create or update Genie spaces or dashboards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from extract_dashboard_sql import extract_dashboard_sql

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "genie" / "benchmark_questions.json"
GENIE_SPACE = ROOT / "genie" / "nemweb_space.json"
DASHBOARD = ROOT / "dashboards" / "nemweb_overview.lvdash.json"
TERMINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELED", "CLOSED"}
# No profile name is mandated; an explicit one is. See evidence.py.
PROFILE_REQUIRED_MESSAGE = (
    "workspace-aware validation requires an explicit --profile <name>; "
    "no implicit default profile is permitted"
)
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
REQUIRED_TOPICS = {
    "effective-intervention-uniqueness",
    "regional-price-demand",
    "generation-by-fuel",
    "binding-constraints",
    "interconnector-source-sign",
    "t1-unit-availability",
    "dispatch-price-spikes",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_benchmark_sql(sql: str, catalog: str, schema: str) -> str:
    if not SAFE_IDENTIFIER.fullmatch(catalog) or not SAFE_IDENTIFIER.fullmatch(schema):
        raise ValueError("catalog and schema must be simple Databricks identifiers")
    rendered = sql.replace("{{catalog}}", catalog).replace("{{schema}}", schema)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("unresolved SQL template placeholder")
    return rendered


def validate_assets() -> dict[str, Any]:
    benchmark_doc = _read_json(BENCHMARKS)
    benchmarks = benchmark_doc.get("benchmarks", [])
    if len(benchmarks) < 5:
        raise ValueError("at least five benchmark questions are required")
    ids = [item.get("id") for item in benchmarks]
    if len(ids) != len(set(ids)) or not REQUIRED_TOPICS.issubset(set(ids)):
        raise ValueError("benchmark IDs are duplicate or omit a required topic")

    benchmark_sql: list[dict[str, Any]] = []
    for item in benchmarks:
        relative = Path(item["sql_file"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe benchmark path: {relative}")
        path = ROOT / relative
        sql = path.read_text(encoding="utf-8").strip()
        if not sql or ";" in sql.rstrip(";"):
            raise ValueError(f"benchmark {item['id']} must contain exactly one SQL statement")
        if "{{catalog}}.{{schema}}." not in sql:
            raise ValueError(f"benchmark {item['id']} must be catalog/schema parameterised")
        if not item.get("expected_columns") or "result_expectation" not in item:
            raise ValueError(f"benchmark {item['id']} lacks a result contract")
        benchmark_sql.append({"benchmark": item, "sql": sql})

    genie = _read_json(GENIE_SPACE)
    tables = genie.get("data_sources", {}).get("tables", [])
    identifiers = [table.get("identifier", "") for table in tables]
    if not (5 <= len(identifiers) <= 8):
        raise ValueError("Genie must expose a deliberately small set of 5-8 assets")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Genie contains duplicate assets")
    if any(not value.startswith("${var.catalog}.${var.schema}.") for value in identifiers):
        raise ValueError("Genie identifiers must use bundle catalog/schema variables")
    instructions = json.dumps(genie.get("instructions", {})).lower()
    for phrase in ("effective", "aest", "t+1", "source sign", "measure()", "unknown"):
        if phrase not in instructions:
            raise ValueError(f"Genie instructions omit required semantic phrase: {phrase}")
    sample_questions = genie.get("config", {}).get("sample_questions", [])
    examples = genie.get("instructions", {}).get("example_question_sqls", [])
    if len(sample_questions) < 5 or len(examples) < 5:
        raise ValueError("Genie requires at least five samples and example SQL entries")

    dashboard = _read_json(DASHBOARD)
    dashboard_sql = extract_dashboard_sql(DASHBOARD)
    genie_link = dashboard.get("uiSettings", {}).get("genieSpace", {})
    if genie_link.get("isEnabled") is not True or genie_link.get("overrideId") != "${resources.genie_spaces.nemweb_analyst.id}":
        raise ValueError("dashboard is not linked to the bundle-managed Genie space")
    if not any(page.get("pageType") == "PAGE_TYPE_GLOBAL_FILTERS" for page in dashboard.get("pages", [])):
        raise ValueError("dashboard requires global region/date filters")
    if "daily T+1" not in json.dumps(dashboard) and "daily T+1" not in json.dumps(dashboard, ensure_ascii=False):
        raise ValueError("dashboard must disclose daily T+1 availability")

    return {
        "benchmarks": benchmark_sql,
        "dashboard_sql": dashboard_sql,
        "genie_asset_count": len(identifiers),
    }


def _run_cli(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Databricks CLI transport failed ({completed.returncode}): {completed.stderr.strip()}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Databricks CLI returned non-JSON output") from exc


def _statement_state(response: dict[str, Any]) -> str:
    state = response.get("status", {}).get("state")
    if not isinstance(state, str):
        raise RuntimeError("SQL statement response has no status.state")
    return state


def execute_statement(
    sql: str,
    *,
    profile: str,
    warehouse_id: str,
    catalog: str,
    schema: str,
    timeout_seconds: int,
    cli_runner: Callable[[list[str]], dict[str, Any]] = _run_cli,
) -> dict[str, Any]:
    payload = {
        "warehouse_id": warehouse_id,
        "catalog": catalog,
        "schema": schema,
        "statement": sql,
        "wait_timeout": "0s",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
    }
    response = cli_runner(
        ["databricks", "api", "post", "/api/2.0/sql/statements", "--profile", profile, "--json", json.dumps(payload)]
    )
    statement_id = response.get("statement_id")
    if not statement_id:
        raise RuntimeError("SQL submission returned no statement_id")
    deadline = time.monotonic() + timeout_seconds
    state = _statement_state(response)
    while state not in TERMINAL_STATES:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"SQL statement {statement_id} did not reach a terminal state")
        time.sleep(2)
        response = cli_runner(
            ["databricks", "api", "get", f"/api/2.0/sql/statements/{statement_id}", "--profile", profile]
        )
        state = _statement_state(response)
    if state != "SUCCEEDED":
        error = response.get("status", {}).get("error", {})
        raise RuntimeError(f"SQL statement {statement_id} ended in {state}: {error}")
    # The state check above is mandatory even when the CLI process exited zero.
    return response


def _result_columns(response: dict[str, Any]) -> list[str]:
    columns = response.get("manifest", {}).get("schema", {}).get("columns", [])
    return [column.get("name") for column in columns if isinstance(column, dict)]


def _result_row_count(response: dict[str, Any]) -> int:
    result = response.get("result", {})
    if isinstance(result.get("row_count"), int):
        return result["row_count"]
    data = result.get("data_array", [])
    if isinstance(data, list):
        return len(data)
    raise RuntimeError("successful SQL response did not expose a row count")


def _check_benchmark_result(item: dict[str, Any], response: dict[str, Any]) -> None:
    expected_columns = item["expected_columns"]
    actual_columns = _result_columns(response)
    if actual_columns != expected_columns:
        raise RuntimeError(f"benchmark {item['id']} columns {actual_columns!r} != {expected_columns!r}")
    count = _result_row_count(response)
    expectation = item["result_expectation"]
    if "row_count" in expectation and count != expectation["row_count"]:
        raise RuntimeError(f"benchmark {item['id']} row count {count} != {expectation['row_count']}")
    if count < expectation.get("minimum_row_count", 0):
        raise RuntimeError(f"benchmark {item['id']} row count {count} is below its minimum")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="execute every benchmark and dashboard SQL statement")
    parser.add_argument("--catalog")
    parser.add_argument("--schema")
    parser.add_argument("--warehouse-id")
    parser.add_argument("--profile", required=True, help="Databricks CLI profile name")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not args.profile.strip():
        parser.error(PROFILE_REQUIRED_MESSAGE)

    assets = validate_assets()
    print(
        f"Static assets valid: {len(assets['benchmarks'])} benchmarks, "
        f"{assets['genie_asset_count']} Genie assets, {len(assets['dashboard_sql'])} dashboard statements."
    )
    if not args.execute:
        return 0
    if not all((args.catalog, args.schema, args.warehouse_id)):
        parser.error("--execute requires --catalog, --schema and --warehouse-id")

    records: list[dict[str, Any]] = []
    for entry in assets["benchmarks"]:
        item = entry["benchmark"]
        sql = render_benchmark_sql(entry["sql"], args.catalog, args.schema)
        response = execute_statement(
            sql,
            profile=args.profile,
            warehouse_id=args.warehouse_id,
            catalog=args.catalog,
            schema=args.schema,
            timeout_seconds=args.timeout_seconds,
        )
        _check_benchmark_result(item, response)
        records.append({
            "kind": "benchmark",
            "name": item["id"],
            "sha256": hashlib.sha256(sql.rstrip(";").encode("utf-8")).hexdigest(),
            "state": _statement_state(response),
            "row_count": _result_row_count(response),
            "statement_id": response["statement_id"],
        })

    for item in assets["dashboard_sql"]:
        response = execute_statement(
            item["sql"],
            profile=args.profile,
            warehouse_id=args.warehouse_id,
            catalog=args.catalog,
            schema=args.schema,
            timeout_seconds=args.timeout_seconds,
        )
        records.append({
            "kind": "dashboard",
            "name": item["dataset"],
            "sha256": item["sha256"],
            "state": _statement_state(response),
            "row_count": _result_row_count(response),
            "statement_id": response["statement_id"],
        })

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Executed {len(records)} SQL statements; every terminal state was SUCCEEDED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
