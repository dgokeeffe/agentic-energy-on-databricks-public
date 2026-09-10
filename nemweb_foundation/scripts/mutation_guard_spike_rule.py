#!/usr/bin/env python3
"""Prove the dispatch-price spike tests can still detect the defects they target.

A passing test suite says nothing about whether a test would *fail* if the code
were wrong. Eight specific defects were checked by hand when the spike measure
was written, and that evidence lived only in a commit message. Prose evidence
decays: a later refactor can weaken a guard while every test stays green.

This script re-runs those eight checks mechanically. Each mutant is a single
targeted edit to the source, paired with the test that must go red. A mutant that
*survives* (tests still pass) is a failure of the test suite, not of the mutant,
and this script exits non-zero.

The source file is always restored, including on exception or SIGINT.

Run: make mutation-spike
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FOUNDATION = Path(__file__).resolve().parents[1]
RULE = FOUNDATION / "agentic_energy/nemweb/corrections.py"
VIEW = FOUNDATION / "agentic_energy/nemweb/pipeline/gold_additional_aggregates.py"
RULE_TESTS = "tests/nemweb/test_price_spike_rule.py"
CONTRACT_TESTS = "tests/nemweb/test_gold_contracts.py"


@dataclass(frozen=True)
class Mutant:
    """One deliberate defect, and the test that must notice it."""

    name: str
    path: Path
    old: str
    new: str
    tests: str
    why: str
    #: Test that must be among the failures. Guards against a mutant being caught
    #: only by an unrelated test, which would mean the intended guard is absent.
    expect_failure_in: str


MUTANTS = (
    Mutant(
        name="baseline-includes-judged-interval",
        path=RULE,
        old="        median_price, is_spike = _spike_verdict(",
        new="        baseline = baseline + [price]\n        median_price, is_spike = _spike_verdict(",
        tests=RULE_TESTS,
        why="A price entering its own baseline lifts the median and masks its own spike.",
        expect_failure_in="test_the_judged_interval_is_excluded_from_its_own_baseline",
    ),
    Mutant(
        name="insufficient-history-returns-false",
        path=RULE,
        old="        return None, None",
        new="        return None, False",
        tests=RULE_TESTS,
        why="Reports 'checked, no spike' for intervals where no comparison was possible.",
        expect_failure_in="test_insufficient_history_withholds_the_flag_rather_than_returning_false",
    ),
    Mutant(
        name="non-positive-baseline-not-withheld",
        path=RULE,
        old="    if median_price <= 0:\n        return median_price, None\n",
        new="",
        tests=RULE_TESTS,
        why="A ratio against a negative median inverts: the lowest price reads as a spike.",
        expect_failure_in="test_a_negative_baseline_withholds_the_flag",
    ),
    Mutant(
        name="boundary-becomes-strict",
        path=RULE,
        old="return median_price, price >= median_price * baseline_multiple",
        new="return median_price, price > median_price * baseline_multiple",
        tests=RULE_TESTS,
        why="The agreed boundary is inclusive; strict silently drops on-threshold spikes.",
        expect_failure_in="test_a_price_exactly_on_the_multiple_is_a_spike",
    ),
    Mutant(
        name="effective-run-filter-dropped",
        path=RULE,
        old='effective = [dict(row) for row in rows if row.get("is_effective_run")]',
        new="effective = [dict(row) for row in rows]",
        tests=RULE_TESTS,
        why="Intervention pairs double count and inflate the baseline.",
        expect_failure_in="test_non_effective_runs_are_excluded_entirely",
    ),
    Mutant(
        name="deployed-frame-includes-current-row",
        path=VIEW,
        old=".rowsBetween(-SPIKE_BASELINE_INTERVALS, -1)",
        new=".rowsBetween(-SPIKE_BASELINE_INTERVALS, 0)",
        tests=CONTRACT_TESTS,
        why=(
            "The divergence defect shape recorded in miniwiki/decisions/"
            "facility-dimension-as-of.md: deployed Spark drifts from the tested "
            "pure function while every pure-function test stays green."
        ),
        expect_failure_in="test_the_deployed_spike_window_excludes_the_interval_it_judges",
    ),
    Mutant(
        name="deployed-null-becomes-false",
        path=VIEW,
        old='        ).alias("is_price_spike"),',
        new='        ).otherwise(F.lit(False)).alias("is_price_spike"),',
        tests=CONTRACT_TESTS,
        why="Asserts a comparison was made and failed, on intervals where none was possible.",
        expect_failure_in="test_the_spike_flag_is_withheld_rather_than_false_when_undecidable",
    ),
    Mutant(
        name="deployed-median-reverts-to-median-function",
        path=VIEW,
        old='F.expr("percentile(rrp_aud_per_mwh, 0.5)")',
        new='F.median("rrp_aud_per_mwh")',
        tests=CONTRACT_TESTS,
        why=(
            "median() over a ROWS frame raises INVALID_WINDOW_SPEC_FOR_AGGREGATION_FUNC, "
            "so the view would not analyse. Verified on a warehouse by "
            "scripts/verify_spike_sql_semantics.py."
        ),
        expect_failure_in="test_the_trailing_median_uses_exact_percentile_not_median_or_approx",
    ),
    Mutant(
        name="deployed-median-becomes-approximate",
        path=VIEW,
        old='F.expr("percentile(rrp_aud_per_mwh, 0.5)")',
        new='F.expr("percentile_approx(rrp_aud_per_mwh, 0.5)")',
        tests=CONTRACT_TESTS,
        why=(
            "percentile_approx is accepted over a ROWS frame but approximate: for "
            "[0, 1] it returns 0.0 where the exact median is 0.5. It would disagree "
            "with every offline test while the pipeline stayed green."
        ),
        expect_failure_in="test_the_trailing_median_uses_exact_percentile_not_median_or_approx",
    ),
    Mutant(
        name="deployed-threshold-hard-coded",
        path=VIEW,
        old="    multiple = spike_baseline_multiple(spark)",
        new="    multiple = 3.0",
        tests=CONTRACT_TESTS,
        why="Defeats the no-default decision: the view would publish an unstated threshold.",
        expect_failure_in="test_the_deployed_spike_threshold_is_never_a_literal",
    ),
)


def run_tests(target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "uv", "run", "--project", str(FOUNDATION), "--extra", "test",
            "python", "-m", "pytest", target, "-q", "--no-header",
            "-p", "no:cacheprovider",
        ],
        cwd=FOUNDATION,
        capture_output=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list", action="store_true", help="list the mutants without running them"
    )
    args = parser.parse_args()

    if args.list:
        for mutant in MUTANTS:
            print(f"{mutant.name}\n    {mutant.why}\n    caught by: {mutant.expect_failure_in}")
        return 0

    # A suite that is already red makes every mutant look caught.
    for target in (RULE_TESTS, CONTRACT_TESTS):
        baseline = run_tests(target)
        if baseline.returncode != 0:
            print(f"FAIL: {target} is red before any mutation; fix that first.")
            print(baseline.stdout[-2000:])
            return 1
    print(f"Baseline green. Injecting {len(MUTANTS)} mutants one at a time.")

    originals = {path: path.read_text() for path in {m.path for m in MUTANTS}}
    survivors: list[str] = []
    miscaught: list[str] = []
    try:
        for mutant in MUTANTS:
            source = originals[mutant.path]
            if source.count(mutant.old) != 1:
                print(
                    f"FAIL {mutant.name}: anchor text appears "
                    f"{source.count(mutant.old)} times in {mutant.path.name}; "
                    "expected exactly 1. The mutant is stale — update it."
                )
                return 1
            mutant.path.write_text(source.replace(mutant.old, mutant.new, 1))
            result = run_tests(mutant.tests)
            mutant.path.write_text(source)

            if result.returncode == 0:
                survivors.append(mutant.name)
                print(f"  SURVIVED  {mutant.name}  <-- no test detected this")
            elif mutant.expect_failure_in not in result.stdout:
                miscaught.append(mutant.name)
                print(
                    f"  caught    {mutant.name}  <-- but NOT by "
                    f"{mutant.expect_failure_in}"
                )
            else:
                print(f"  caught    {mutant.name}")
    finally:
        # Restore unconditionally: a half-mutated tree is worse than a failure.
        for path, text in originals.items():
            path.write_text(text)

    if survivors or miscaught:
        if survivors:
            print(f"\n{len(survivors)} mutant(s) survived: {', '.join(survivors)}")
            print("A surviving mutant means the test written to catch it no longer can.")
        if miscaught:
            print(f"\n{len(miscaught)} mutant(s) caught by the wrong test: {', '.join(miscaught)}")
            print("The intended guard is gone; an unrelated test happened to fail.")
        return 1

    print(f"\nAll {len(MUTANTS)} mutants caught by their intended tests. Sources restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
