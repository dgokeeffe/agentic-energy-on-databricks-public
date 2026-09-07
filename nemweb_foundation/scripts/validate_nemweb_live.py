#!/usr/bin/env python3
"""Audit a captured NEMWEB evidence pack for the three-cycle live closure gate."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import fields
from datetime import datetime
from pathlib import Path

from agentic_energy.nemweb.evidence import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceRow,
    SUBJECTS,
)

_SECRET = re.compile(r"(?i)(dapi[a-z0-9]{20,}|token\s*[=:]|https://[^\s]*\.cloud\.databricks\.com|\?o=\d+)")


def _load(path: Path) -> list[EvidenceRow]:
    raw = path.read_text(encoding="utf-8")
    if _SECRET.search(raw):
        raise ValueError("evidence contains a token, private workspace URL or tenant identifier")
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError("evidence JSON must be a versioned document")
    if document.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ValueError(
            f"evidence schema version must be {EVIDENCE_SCHEMA_VERSION}"
        )
    values = document.get("rows", [])
    expected = {field.name for field in fields(EvidenceRow)}
    rows: list[EvidenceRow] = []
    for value in values:
        if set(value) != expected:
            raise ValueError("evidence row does not match the versioned contract")
        value = dict(value)
        value["raw_zip_checksums"] = tuple(value["raw_zip_checksums"])
        row = EvidenceRow(**value)
        row.validate()
        rows.append(row)
    return rows


def validate(rows: list[EvidenceRow], minimum_cycles: int = 3) -> tuple[int, int]:
    expected_subjects = {spec.subject for spec in SUBJECTS}
    cycles: dict[str, list[EvidenceRow]] = {}
    for row in rows:
        cycles.setdefault(row.orchestration_run_id, []).append(row)
    if len(cycles) < minimum_cycles:
        raise ValueError(f"need at least {minimum_cycles} cycles, found {len(cycles)}")
    ordered = sorted(cycles.values(), key=lambda group: group[0].cycle_started_at)
    cycle_update_ids: list[str] = []
    for group in ordered:
        if {row.subject for row in group} != expected_subjects or len(group) != len(expected_subjects):
            raise ValueError("every cycle must contain exactly one row for each critical subject")
        update_ids = {row.pipeline_update_id for row in group}
        if len(update_ids) != 1:
            raise ValueError("a cycle contains more than one pipeline update ID")
        cycle_update_ids.append(next(iter(update_ids)))
        for row in group:
            if row.landed_row_count < row.bronze_row_count:
                raise ValueError("Bronze count exceeds landed rows for a subject")
            # EvidenceRow.validate() reconciles every reported lag to its named
            # timestamp pair. A signed source-to-Gold lag is legitimate only for
            # an explicitly tolerated post-cycle listing lead; represented
            # Bronze and landing chronology must remain non-negative.
            if (
                row.bronze_interval_to_gold_lag_seconds is not None
                and row.bronze_interval_to_gold_lag_seconds < 0
            ):
                raise ValueError("Gold publication precedes its Bronze interval")
            if row.landed_to_gold_processing_lag_seconds is not None and row.landed_to_gold_processing_lag_seconds < 0:
                raise ValueError("Gold publication precedes landing")
    if len(cycle_update_ids) != len(set(cycle_update_ids)):
        raise ValueError(
            "each cycle must reference a distinct pipeline update ID"
        )
    # A five-minute periodic trigger can start late, and max_concurrent_runs: 1
    # plus queueing means an overrunning cycle delays the next start. Measured
    # live end-to-end wall clock is ~340-480s, so successive start-to-start
    # spacing can exceed one dispatch interval without skipping a cycle. Bound
    # the gap at two dispatch intervals so a missing intermediate cycle still
    # fails while a queued consecutive pair is accepted.
    starts = [datetime.fromisoformat(group[0].cycle_started_at) for group in ordered]
    for previous, current in zip(starts, starts[1:]):
        spacing = (current - previous).total_seconds()
        if not 240 <= spacing <= 600:
            raise ValueError(f"cycles are not consecutive five-minute executions ({spacing:.0f}s apart)")
    return len(cycles), len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json", type=Path)
    parser.add_argument("--minimum-cycles", type=int, default=3)
    args = parser.parse_args()
    rows = _load(args.evidence_json)
    cycle_count, row_count = validate(rows, args.minimum_cycles)
    print(f"Live evidence valid: {cycle_count} consecutive cycle(s), {row_count} subject rows, exact update IDs terminal and all quality/key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
