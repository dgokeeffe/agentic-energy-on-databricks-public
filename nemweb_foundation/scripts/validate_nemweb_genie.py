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
}

# Governed contract sources a refusal is allowed to quote. `DATA-CONTRACT.md` is
# owned by this package, but `DATA_LICENSES.md` lives at the repository root
# (``ROOT.parent``), i.e. deliberately outside the packaging boundary. That
# crossing is why the sources are a named registry resolved here rather than a
# relative path carried in benchmark_questions.json: validate_assets() already
# rejects `..` in any `sql_file` path, and the same prohibition must hold for
# refusal metadata. A `contract_source` outside this registry is an error.
CONTRACT_SOURCES: dict[str, Path] = {
    "DATA-CONTRACT.md": ROOT / "DATA-CONTRACT.md",
    "DATA_LICENSES.md": ROOT.parent / "DATA_LICENSES.md",
}
# Refusal topics that must always be present. `market-notice-cause` is
# deliberately EXCLUDED: the exercise documents it as the "cut if time runs
# short" refusal, so dropping it must not require editing this validator.
REQUIRED_REFUSAL_TOPICS = frozenset(
    {
        "five-minute-curtailment",
        "constraint-marginal-value-by-region",
        "interconnector-import-export-direction",
        "snapshot-price-as-live-spot",
        "bid-recommendation",
    }
)
# The permitted `unsupported_because` enum, taken from the refusal catalogue as
# authored. A new class must be added here consciously, not invented in JSON.
REFUSAL_CLASSES = frozenset(
    {
        "deliberate_omission",
        "no_governed_dimension",
        "no_governed_mapping",
        "no_published_field",
        "out_of_scope_decision_support",
        "snapshot_not_live",
    }
)
REFUSAL_REQUIRED_FIELDS = (
    "id",
    "space_question_id",
    "question",
    "contract_source",
    "contract_section",
    "contract_quote",
    "unsupported_because",
    "refusal_reason",
    "near_miss_of",
)
# A refusal must reach the executor under no circumstance; these keys are what
# the --execute path consumes, so their presence on a refusal is a hard error.
REFUSAL_FORBIDDEN_FIELDS = ("sql_file", "expected_columns", "result_expectation")
SPACE_QUESTION_ID = re.compile(r"^[0-9a-f]{32}$")
MINIMUM_REFUSAL_COUNT = 4
MINIMUM_REFUSAL_NEAR_MISS_COVERAGE = 4
# "I cannot answer that" is exactly the inadequate answer this exercise exists
# to rule out, so a refusal reason must be long enough to name a reason.
MINIMUM_REFUSAL_REASON_CHARS = 80
MARKDOWN_HEADING = re.compile(r"^(#{2,})\s+(.*\S)\s*$")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_benchmark_sql(sql: str, catalog: str, schema: str) -> str:
    if not SAFE_IDENTIFIER.fullmatch(catalog) or not SAFE_IDENTIFIER.fullmatch(schema):
        raise ValueError("catalog and schema must be simple Databricks identifiers")
    rendered = sql.replace("{{catalog}}", catalog).replace("{{schema}}", schema)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("unresolved SQL template placeholder")
    return rendered


def _normalise_contract_text(text: str) -> str:
    """Collapse every whitespace run to a single space.

    This is mandatory, not cosmetic. The governed contract markdown hard-wraps
    prose mid-sentence, so a cited sentence longer than one wrapped line spans a
    newline plus indentation and cannot be found by a raw substring match against
    the file as written. As authored, two of the six quotes
    (`bid-recommendation` and `snapshot-price-as-live-spot`) fail a raw match and
    pass only once normalised; the remaining four fit a single source line today
    and would break the moment either contract is re-wrapped. Normalising both
    the section body and the quote compares the sentence rather than the line
    wrapping, and, because it is applied per section, still refuses a quote that
    only matches outside the section it claims.
    """
    return " ".join(text.split())


def contract_sections(path: Path) -> dict[str, str]:
    """Split a markdown file into ``{"## Heading": normalised_body}``.

    Only level-2-or-deeper headings start a section, and the returned key keeps
    the literal heading line (hashes included) so a refusal cites it verbatim.
    Bodies are normalised and scoped to their own section, so a quote is matched
    only inside the section it claims to come from and cannot silently drift to
    a coincidental match elsewhere in the file.
    """
    sections: dict[str, str] = {}
    heading: str | None = None
    body: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = MARKDOWN_HEADING.match(line)
        if match:
            if heading is not None:
                sections[heading] = _normalise_contract_text("\n".join(body))
            heading = f"{match.group(1)} {match.group(2)}"
            body = []
            continue
        if heading is not None:
            body.append(line)
    if heading is not None:
        sections[heading] = _normalise_contract_text("\n".join(body))
    return sections


def validate_refusals(
    refusals: list[dict[str, Any]], benchmark_ids: set[str]
) -> list[dict[str, Any]]:
    """Statically validate the refusal catalogue against the governed contracts.

    Every refusal must quote a real sentence from a named section of a named
    governed source. That is the check an invented rule cannot pass.
    """
    if len(refusals) < MINIMUM_REFUSAL_COUNT:
        raise ValueError(f"at least {MINIMUM_REFUSAL_COUNT} refusal questions are required")
    ids = [item.get("id") for item in refusals]
    if len(ids) != len(set(ids)):
        raise ValueError("refusal IDs are duplicate")
    missing_topics = sorted(REQUIRED_REFUSAL_TOPICS - set(ids))
    if missing_topics:
        raise ValueError(f"refusal catalogue omits required topics: {missing_topics}")
    colliding = sorted(set(ids) & benchmark_ids)
    if colliding:
        raise ValueError(f"refusal IDs collide with benchmark IDs: {colliding}")
    space_ids = [item.get("space_question_id") for item in refusals]
    if len(space_ids) != len(set(space_ids)):
        raise ValueError("refusal space_question_id values are duplicate")

    sections_cache: dict[str, dict[str, str]] = {}
    covered_near_misses: set[str] = set()
    for item in refusals:
        name = item.get("id") or "<unnamed>"
        for field in REFUSAL_REQUIRED_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"refusal {name} lacks a non-empty {field}")
        present_forbidden = [field for field in REFUSAL_FORBIDDEN_FIELDS if field in item]
        if present_forbidden:
            raise ValueError(
                f"refusal {name} must not carry executable benchmark keys: {present_forbidden}"
            )
        if not SPACE_QUESTION_ID.fullmatch(item["space_question_id"]):
            raise ValueError(f"refusal {name} space_question_id is not a 32-character hex ID")
        if item["unsupported_because"] not in REFUSAL_CLASSES:
            raise ValueError(
                f"refusal {name} uses unknown unsupported_because {item['unsupported_because']!r}"
            )
        if len(item["refusal_reason"].strip()) < MINIMUM_REFUSAL_REASON_CHARS:
            raise ValueError(
                f"refusal {name} reason must name a reason, not merely decline "
                f"(at least {MINIMUM_REFUSAL_REASON_CHARS} characters)"
            )
        source = item["contract_source"]
        if source not in CONTRACT_SOURCES:
            raise ValueError(f"refusal {name} cites unknown contract source {source!r}")
        if source not in sections_cache:
            sections_cache[source] = contract_sections(CONTRACT_SOURCES[source])
        sections = sections_cache[source]
        section = item["contract_section"]
        if section not in sections:
            raise ValueError(f"refusal {name} cites missing section {section!r} in {source}")
        if _normalise_contract_text(item["contract_quote"]) not in sections[section]:
            raise ValueError(
                f"refusal {name} quote is not present in {source} section {section!r}"
            )
        near_miss = item["near_miss_of"]
        if near_miss not in benchmark_ids:
            raise ValueError(f"refusal {name} near_miss_of {near_miss!r} is not a benchmark ID")
        covered_near_misses.add(near_miss)

    if len(covered_near_misses) < MINIMUM_REFUSAL_NEAR_MISS_COVERAGE:
        raise ValueError(
            f"refusals must sit adjacent to at least {MINIMUM_REFUSAL_NEAR_MISS_COVERAGE} "
            f"distinct benchmarks; only {len(covered_near_misses)} covered"
        )
    return list(refusals)


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
        _check_expectation_asserts_something(item)
        benchmark_sql.append({"benchmark": item, "sql": sql})

    # Refusals live under their own key precisely because they carry no
    # sql_file/expected_columns/result_expectation, so the loop above never sees
    # them and the --execute path can never submit one.
    refusals = validate_refusals(benchmark_doc.get("refusals", []), set(ids))

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
        "refusals": refusals,
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


def _check_expectation_asserts_something(item: dict[str, Any]) -> None:
    """Reject a ``result_expectation`` that asserts nothing.

    This is a class rule over the expectation's keys, not a carve-out for any
    single benchmark ID. An expectation is substantive when it pins an exact
    ``row_count``, demands at least one row, or asserts a grain via
    ``distinct_key_columns``. ``minimum_row_count: 0`` alone is trivially true
    for every possible result, so on its own it is vacuous; the same expectation
    combined with ``distinct_key_columns`` is row-count-independent yet still
    asserts grain, and is therefore allowed.
    """
    expectation = item["result_expectation"]
    if not isinstance(expectation, dict):
        raise ValueError(f"benchmark {item['id']} result_expectation must be an object")
    asserts_row_count = "row_count" in expectation or expectation.get("minimum_row_count", 0) > 0
    asserts_grain = bool(expectation.get("distinct_key_columns"))
    if not (asserts_row_count or asserts_grain):
        raise ValueError(
            f"benchmark {item['id']} result_expectation {expectation!r} asserts nothing; "
            "pin a row_count, require at least one row, or assert distinct_key_columns"
        )
    key_columns = expectation.get("distinct_key_columns", [])
    if key_columns:
        unknown = [column for column in key_columns if column not in item["expected_columns"]]
        if unknown:
            raise ValueError(
                f"benchmark {item['id']} distinct_key_columns {unknown} are not expected columns"
            )


def _check_result_grain(item: dict[str, Any], response: dict[str, Any]) -> None:
    """Assert the declared key columns are unique across the returned rows."""
    key_columns = item["result_expectation"].get("distinct_key_columns", [])
    if not key_columns:
        return
    # _check_benchmark_result has already asserted the actual columns equal
    # expected_columns exactly and in order, so these positions are the
    # positions in every data_array row.
    positions = [item["expected_columns"].index(column) for column in key_columns]
    rows = response.get("result", {}).get("data_array") or []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        if not isinstance(row, list) or len(row) <= max(positions):
            raise RuntimeError(f"benchmark {item['id']} returned a row narrower than its columns")
        key = tuple(row[position] for position in positions)
        if key in seen:
            raise RuntimeError(
                f"benchmark {item['id']} repeats key {key!r} for {key_columns}; "
                "the declared grain is not unique"
            )
        seen.add(key)


def _check_benchmark_result(item: dict[str, Any], response: dict[str, Any]) -> None:
    _check_expectation_asserts_something(item)
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
    _check_result_grain(item, response)


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
        f"{len(assets['refusals'])} contract-cited refusals, "
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
