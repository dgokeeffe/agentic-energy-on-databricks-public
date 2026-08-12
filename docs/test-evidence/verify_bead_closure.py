#!/usr/bin/env python3
"""Verify the foundation bead is closed with reconciliation evidence.

Not part of the pytest suite on purpose: the Beads Dolt database is gitignored
(`.beads/.gitignore` ignores `embeddeddolt/`), so a test asserting work-graph
state would fail on every fresh clone and in CI. Run it locally and cite the
output.

Usage:  python3 docs/test-evidence/verify_bead_closure.py
Exit:   0 = all checks passed, 1 = one or more failed
"""
import json
import subprocess
import sys

FOUNDATION = "agentic-energy-93y"
DEPENDENTS = [
    "agentic-energy-zwh",  # Engineering: inspect and improve the metadata contract
    "agentic-energy-02f",  # Defect: local market timestamps are not normalized correctly
    "agentic-energy-yx8",  # Defect: malformed rows are not safely quarantined
    "agentic-energy-5g3",  # Defect: annotation access does not enforce identity boundaries
    "agentic-energy-aln",  # Defect: synchronized Gold reconciliation is inconsistent
]
# Tokens the close reason must cite, so a bare "done" cannot pass.
REQUIRED_CITATIONS = ["bronze=11", "silver=6", "quarantine=3", "gold=3",
                      "e2235552", "24 passed", "identical replay"]

failures: list[str] = []


def bd(*args):
    result = subprocess.run(["bd", *args], capture_output=True, text=True)
    if not result.stdout.strip():
        raise SystemExit(f"bd {' '.join(args)} produced no output:\n{result.stderr}")
    return json.loads(result.stdout)


def one(payload):
    return payload[0] if isinstance(payload, list) else payload


def check(label, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got!r}"
          + ("" if ok else f" (expected {want!r})"))
    if not ok:
        failures.append(label)


issue = one(bd("show", FOUNDATION, "--json"))
check("foundation status", issue["status"], "closed")
check("foundation id", issue["id"], FOUNDATION)
check("closed_at present", bool(issue.get("closed_at")), True)

reason = issue.get("close_reason") or ""
check("close reason non-trivial (>500 chars)", len(reason) > 500, True)
for token in REQUIRED_CITATIONS:
    check(f"close reason cites {token!r}", token in reason, True)

ready = {row["id"] for row in bd("ready", "--json")}
for dependent in DEPENDENTS:
    check(f"{dependent} unblocked", dependent in ready, True)
check("foundation absent from ready", FOUNDATION not in ready, True)

print("-" * 60)
print("ALL CHECKS PASSED" if not failures
      else f"{len(failures)} FAILURE(S): {', '.join(failures)}")
sys.exit(1 if failures else 0)
