#!/usr/bin/env python3
"""Run one bounded workshop SELECT and retain its Statement API evidence.

Explicit warehouse/catalog/schema/profile; no default-profile discovery. The
output must be inside ignored .databricks. Reuse --resume with the saved statement
ID after an observation timeout; never resubmit just because polling timed out.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("Expected a simple SQL identifier")
    return value


def cli(profile, *args, body=None):
    command = ["databricks", *args, "--profile", profile, "-o", "json"]
    if body is not None:
        command += ["--json", json.dumps(body)]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def rows(response):
    if response["status"]["state"] != "SUCCEEDED":
        raise ValueError(response["status"])
    if response.get("manifest", {}).get("truncated") or response.get("result", {}).get("next_chunk_index") is not None:
        raise ValueError("Result truncated; reduce the window instead of accepting partial evidence")
    columns = [c["name"] for c in response["manifest"]["schema"]["columns"]]
    return [dict(zip(columns, row)) for row in response.get("result", {}).get("data_array", [])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("profile", "warehouse-id", "catalog", "schema", "sql-file", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--resume", help="Previously saved statement ID; observe, do not resubmit")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to(ROOT / ".databricks"):
        parser.error("output must be inside this checkout's ignored .databricks directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    sql = Path(args.sql_file).read_text().replace("${catalog}", identifier(args.catalog)).replace("${schema}", identifier(args.schema))
    if not re.match(r"\s*(SELECT|WITH)\b", sql, re.I) or ";" in sql:
        parser.error("Use one SELECT/WITH statement without a trailing semicolon")
    if output.exists() and not args.resume:
        parser.error("Evidence already exists; choose a new output or resume the saved statement ID")
    if args.resume:
        response = cli(args.profile, "api", "get", "/api/2.0/sql/statements/" + args.resume)
    else:
        response = cli(args.profile, "api", "post", "/api/2.0/sql/statements", body={
            "warehouse_id": args.warehouse_id, "catalog": args.catalog, "schema": args.schema,
            "statement": sql, "wait_timeout": "10s", "on_wait_timeout": "CONTINUE",
            "disposition": "INLINE", "format": "JSON_ARRAY", "row_limit": 1000,
        })
    output.write_text(json.dumps(response, indent=2) + "\n")
    statement_id = response["statement_id"]
    print("Statement:", statement_id, flush=True)
    deadline = time.monotonic() + 600
    while response["status"]["state"] in {"PENDING", "RUNNING"}:
        if time.monotonic() >= deadline:
            raise TimeoutError("Still pending; resume statement " + statement_id)
        time.sleep(5)
        response = cli(args.profile, "api", "get", "/api/2.0/sql/statements/" + statement_id)
        output.write_text(json.dumps(response, indent=2) + "\n")
    result = rows(response)
    print(json.dumps(result, indent=2))
    if result and set(result[0]) == {"check_name", "violations"}:
        if any(int(row["violations"]) != 0 for row in result):
            raise ValueError("Workshop verification found violations")


if __name__ == "__main__":
    main()
