#!/usr/bin/env python3
"""Idempotently grant the Unity Catalog path required by NEMWEB operators.

Every workspace-aware call uses the explicitly selected ``DEFAULT`` profile.
Credentials remain in the Databricks CLI configuration; this script accepts no
token or workspace URL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from typing import Any, Sequence

# No profile name is mandated; an explicit one is. See evidence.py.
PROFILE_REQUIRED_MESSAGE = (
    "workspace-aware grants require an explicit --profile <name>; "
    "no implicit default profile is permitted"
)
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_SAFE_WAREHOUSE = re.compile(r"^[A-Za-z0-9_-]+$")
_TERMINAL = {"SUCCEEDED", "FAILED", "CANCELED", "CLOSED"}


def quote_identifier(value: str, label: str) -> str:
    if not _SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be a simple Unity Catalog identifier")
    return f"`{value}`"


def quote_principal(value: str) -> str:
    if not value or len(value) > 255 or "`" in value or any(c in value for c in "\r\n\x00"):
        raise ValueError("principal must be non-empty and contain no backtick or control character")
    return f"`{value}`"


def grant_statements(
    principal: str, *, catalog: str, schema: str, volume: str, readers: bool
) -> list[str]:
    cat = quote_identifier(catalog, "catalog")
    sch = quote_identifier(schema, "schema")
    vol = quote_identifier(volume, "volume")
    who = quote_principal(principal)
    volume_privileges = "READ VOLUME" if readers else "READ VOLUME, WRITE VOLUME"
    return [
        f"GRANT USE CATALOG ON CATALOG {cat} TO {who}",
        f"GRANT USE SCHEMA ON SCHEMA {cat}.{sch} TO {who}",
        f"GRANT {volume_privileges} ON VOLUME {cat}.{sch}.{vol} TO {who}",
    ]


def _cli(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    command = ["databricks", "api", method, path, "--profile", PROFILE]
    if payload is not None:
        command.extend(("--json", json.dumps(payload)))
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(
            f"Databricks CLI failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return json.loads(completed.stdout)


def execute_sql(statement: str, warehouse_id: str, timeout_seconds: int = 300) -> dict[str, Any]:
    response = _cli(
        "post",
        "/api/2.0/sql/statements",
        {
            "warehouse_id": warehouse_id,
            "statement": statement,
            "wait_timeout": "0s",
            "disposition": "INLINE",
            "format": "JSON_ARRAY",
        },
    )
    statement_id = response.get("statement_id")
    if not statement_id:
        raise RuntimeError("SQL Statement Execution API returned no statement_id")
    deadline = time.monotonic() + timeout_seconds
    state = response.get("status", {}).get("state")
    while state not in _TERMINAL:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"SQL statement {statement_id} did not reach a terminal state")
        time.sleep(2)
        response = _cli("get", f"/api/2.0/sql/statements/{statement_id}")
        state = response.get("status", {}).get("state")
    if state != "SUCCEEDED":
        raise RuntimeError(
            f"SQL statement {statement_id} ended {state}: "
            f"{response.get('status', {}).get('error', {})}"
        )
    return response


def _rows(response: dict[str, Any]) -> list[list[Any]]:
    return response.get("result", {}).get("data_array") or []


def _verify_grant(
    principal: str,
    privilege: str,
    object_sql: str,
    warehouse_id: str,
) -> None:
    response = execute_sql(f"SHOW GRANTS ON {object_sql}", warehouse_id)
    wanted_principal = principal.casefold()
    wanted_privilege = privilege.replace(" ", "_").casefold()
    for row in _rows(response):
        flattened = {str(value).replace(" ", "_").casefold() for value in row if value is not None}
        if wanted_principal in flattened and wanted_privilege in flattened:
            return
    raise RuntimeError(
        f"grant verification did not find {privilege} for {principal!r} on {object_sql}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("principals", nargs="+", help="account-level users, groups or service principals")
    parser.add_argument("--readers", action="store_true", help="grant READ VOLUME, not WRITE VOLUME")
    parser.add_argument("--catalog", default=os.environ.get("BUNDLE_VAR_catalog"))
    parser.add_argument("--schema", default=os.environ.get("BUNDLE_VAR_schema"))
    parser.add_argument("--volume", default=os.environ.get("BUNDLE_VAR_landing_volume"))
    parser.add_argument("--warehouse-id", default=os.environ.get("BUNDLE_VAR_warehouse_id"))
    parser.add_argument("--profile", required=True, help="Databricks CLI profile name")
    parser.add_argument("--dry-run", action="store_true", help="validate and print SQL without workspace calls")
    args = parser.parse_args(argv)
    if not args.profile.strip():
        parser.error(PROFILE_REQUIRED_MESSAGE)
    missing = [name for name in ("catalog", "schema", "volume", "warehouse_id") if not getattr(args, name)]
    if missing:
        parser.error("missing required values (flags or BUNDLE_VAR_*): " + ", ".join(missing))
    if not _SAFE_WAREHOUSE.fullmatch(args.warehouse_id):
        parser.error("warehouse ID contains unsupported characters")

    statements: list[tuple[str, str]] = []
    for principal in args.principals:
        try:
            for statement in grant_statements(
                principal,
                catalog=args.catalog,
                schema=args.schema,
                volume=args.volume,
                readers=args.readers,
            ):
                statements.append((principal, statement))
        except ValueError as exc:
            parser.error(str(exc))
    if args.dry_run:
        print("\n".join(statement for _, statement in statements))
        return 0

    for _, statement in statements:
        execute_sql(statement, args.warehouse_id)

    cat = quote_identifier(args.catalog, "catalog")
    sch = quote_identifier(args.schema, "schema")
    vol = quote_identifier(args.volume, "volume")
    for principal in args.principals:
        _verify_grant(principal, "USE_CATALOG", f"CATALOG {cat}", args.warehouse_id)
        _verify_grant(principal, "USE_SCHEMA", f"SCHEMA {cat}.{sch}", args.warehouse_id)
        _verify_grant(principal, "READ_VOLUME", f"VOLUME {cat}.{sch}.{vol}", args.warehouse_id)
        if not args.readers:
            _verify_grant(principal, "WRITE_VOLUME", f"VOLUME {cat}.{sch}.{vol}", args.warehouse_id)
    print(f"Verified Unity Catalog access for {len(args.principals)} principal(s) using profile {PROFILE}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
