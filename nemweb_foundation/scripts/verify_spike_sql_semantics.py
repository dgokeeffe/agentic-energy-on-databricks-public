#!/usr/bin/env python3
"""Verify the spike rule's SQL semantics against the pure-Python rule, on a warehouse.

Every other test for this measure is static or pure Python. Nothing proved that
Spark would even *accept* the window, let alone compute the same median as
``statistics.median``. This closes that gap.

It is read-only by construction: every case runs over ``range(...)`` literals, so
it creates no table, reads no governed data, and needs only CAN_USE on a warehouse.

Run:
  uv run --project nemweb_foundation python \\
    nemweb_foundation/scripts/verify_spike_sql_semantics.py \\
    --profile <name> --warehouse-id <id>

Exit 0 means the deployed SQL semantics match the tested rule. Exit 1 names the
divergence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from statistics import median

#: Fixed by the governed rule: 288 five-minute intervals is 24 hours.
BASELINE_INTERVALS = 288
#: Only for these checks. The real threshold is operator-supplied with no default.
TEST_MULTIPLE = 3.0

PROFILE_REQUIRED = "an explicit --profile <name> is required; no implicit default"


@dataclass
class Case:
    name: str
    sql: str
    why: str
    expect_failure: bool = False
    #: Rows the pure-Python rule must agree with, as (id, expected) pairs.
    expected: list = field(default_factory=list)


def run_sql(sql: str, *, profile: str, warehouse_id: str, timeout: int) -> dict:
    payload = {"warehouse_id": warehouse_id, "statement": sql, "wait_timeout": "50s"}
    result = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements",
         "--profile", profile, "--json", json.dumps(payload)],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        return {"status": {"state": "TRANSPORT_ERROR", "error": {"message": result.stderr[:400]}}}
    return json.loads(result.stdout)


def rows_of(response: dict) -> list[list]:
    return response.get("result", {}).get("data_array") or []


def python_rule(prices: list[float]) -> list[bool | None]:
    """The rule as tested offline, used here as the reference implementation."""

    verdicts: list[bool | None] = []
    for index, price in enumerate(prices):
        window = prices[max(0, index - BASELINE_INTERVALS):index]
        if len(window) < BASELINE_INTERVALS:
            verdicts.append(None)
            continue
        centre = median(window)
        verdicts.append(None if centre <= 0 else price >= centre * TEST_MULTIPLE)
    return verdicts


def synthetic_prices() -> list[float]:
    """Flat 50, then a spike, an on-boundary price and a just-under price.

    The boundary values mirror test_price_spike_rule.py exactly: 150.0 is 3x the
    baseline and must be a spike (the rule is inclusive); 149.99 must not be.
    """

    prices = [50.0] * 330
    prices[300] = 500.0
    prices[310] = 149.99
    prices[320] = 150.0
    return prices


def build_cases() -> list[Case]:
    prices = synthetic_prices()
    reference = python_rule(prices)
    probes = [0, 287, 288, 300, 310, 320]
    # CASE arms are whitespace separated; a comma here is a parse error.
    values = " ".join(f"WHEN id = {i} THEN {prices[i]}" for i in (300, 310, 320))
    frame = f"ORDER BY id ROWS BETWEEN {BASELINE_INTERVALS} PRECEDING AND 1 PRECEDING"

    return [
        Case(
            name="median() rejects a window frame",
            why=(
                "This is why the rule cannot use median() OVER: Spark raises "
                "INVALID_WINDOW_SPEC_FOR_AGGREGATION_FUNC. Asserted so nobody "
                "'simplifies' percentile() back to median() later."
            ),
            expect_failure=True,
            sql=f"SELECT median(v) OVER ({frame}) FROM (SELECT id, CAST(id AS DOUBLE) v FROM range(0,5))",
        ),
        Case(
            name="percentile_approx diverges from an exact median",
            why=(
                "percentile_approx IS accepted over a ROWS frame, which makes it a "
                "tempting fix, but it is approximate: for [0,1] it returns 0.0 where "
                "the exact median is 0.5. Using it would silently disagree with every "
                "offline test."
            ),
            sql=(
                "SELECT percentile_approx(v, 0.5) OVER (ORDER BY id ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) "
                "AS approx FROM (SELECT id, CAST(id AS DOUBLE) v FROM range(0,3)) ORDER BY id"
            ),
            expected=[("approx@2", "0.0")],
        ),
        Case(
            name="percentile() matches statistics.median exactly",
            why="The chosen mechanism. Exact, and accepted over a ROWS frame.",
            sql=(
                "SELECT id, percentile(v, 0.5) OVER (ORDER BY id ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS m "
                "FROM (SELECT id, CAST(id AS DOUBLE) v FROM range(0,6)) ORDER BY id"
            ),
            expected=[
                (str(i), None if not (w := [float(x) for x in range(max(0, i - 3), i)]) else median(w))
                for i in range(6)
            ],
        ),
        Case(
            name="full rule agrees with the pure-Python rule",
            why=(
                "End to end over 330 intervals: incomplete baseline yields NULL not "
                "false, the boundary is inclusive, and a spike is detected without "
                "inflating its own baseline."
            ),
            sql=(
                f"WITH s AS (SELECT id, CASE {values} ELSE 50.0 END AS rrp FROM range(0, {len(prices)})), "
                f"w AS (SELECT id, rrp, percentile(rrp, 0.5) OVER ({frame}) AS med, "
                f"count(rrp) OVER ({frame}) AS n FROM s) "
                f"SELECT id, CASE WHEN n >= {BASELINE_INTERVALS} AND med > 0 "
                f"THEN rrp >= med * {TEST_MULTIPLE} END AS is_price_spike "
                f"FROM w WHERE id IN ({', '.join(map(str, probes))}) ORDER BY id"
            ),
            expected=[(str(i), reference[i]) for i in probes],
        ),
    ]


def check(case: Case, response: dict) -> list[str]:
    state = response.get("status", {}).get("state")
    if case.expect_failure:
        if state == "FAILED":
            return []
        return [f"expected the statement to be rejected, got {state}"]
    if state != "SUCCEEDED":
        message = response.get("status", {}).get("error", {}).get("message", "")
        return [f"statement {state}: {message[:200]}"]

    problems: list[str] = []
    rows = rows_of(response)
    if case.name.startswith("percentile_approx"):
        # Assert the divergence exists, so the reason for rejecting it is evidenced
        # rather than asserted from documentation.
        if not rows or rows[-1][0] not in ("0.0", "0"):
            problems.append(
                f"percentile_approx no longer diverges at [0,1] (got {rows[-1] if rows else 'no rows'}); "
                "re-evaluate whether it is now safe"
            )
        return problems

    actual = {row[0]: row[-1] for row in rows}
    for key, want in case.expected:
        got = actual.get(key)
        if want is None:
            if got is not None:
                problems.append(f"id={key}: expected NULL, got {got!r}")
        elif isinstance(want, bool):
            if got != ("true" if want else "false"):
                problems.append(f"id={key}: expected {str(want).lower()}, got {got!r}")
        elif got is None or abs(float(got) - float(want)) > 1e-9:
            problems.append(f"id={key}: expected {want}, got {got!r}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Databricks CLI profile name")
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    if not args.profile.strip():
        parser.error(PROFILE_REQUIRED)

    print("Read-only: every case runs over range() literals. No table is read or created.")
    failures = 0
    for case in build_cases():
        response = run_sql(
            case.sql, profile=args.profile,
            warehouse_id=args.warehouse_id, timeout=args.timeout_seconds,
        )
        problems = check(case, response)
        if problems:
            failures += 1
            print(f"\nFAIL  {case.name}")
            print(f"      {case.why}")
            for problem in problems:
                print(f"      - {problem}")
        else:
            print(f"  ok  {case.name}")

    if failures:
        print(f"\n{failures} case(s) diverged. The deployed SQL would not match the tested rule.")
        return 1
    print("\nAll cases match the pure-Python rule. percentile() is the correct mechanism.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
