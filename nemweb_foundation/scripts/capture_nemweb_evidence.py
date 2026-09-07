#!/usr/bin/env python3
"""Capture one authoritative NEMWEB cycle and append it to an evidence pack.

The caller must provide the exact Lakeflow pipeline update ID.  This command is
read-only in the workspace: it polls that update, reads its events and queries
published tables.  It never starts, refreshes, deploys, pauses or unpauses a
resource.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import fields
from pathlib import Path

from agentic_energy.nemweb.evidence import (
    DatabricksCLI,
    EvidenceRow,
    REQUIRED_PROFILE,
    capture_live_evidence,
    evidence_document,
    render_markdown,
)


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("rows") if isinstance(document, dict) else document
    if not isinstance(rows, list):
        raise ValueError("existing evidence JSON has no rows list")
    return rows


def _last_by_subject(rows: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        latest[str(row["subject"])] = row
    return latest


def _row_from_dict(value: dict) -> EvidenceRow:
    names = {field.name for field in fields(EvidenceRow)}
    unknown = set(value) - names
    missing = names - set(value)
    if unknown or missing:
        raise ValueError(f"evidence row schema mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
    value = dict(value)
    value["raw_zip_checksums"] = tuple(value["raw_zip_checksums"])
    return EvidenceRow(**value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=REQUIRED_PROFILE)
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--pipeline-id", required=True)
    parser.add_argument("--pipeline-update-id", required=True)
    parser.add_argument("--orchestration-run-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    parser.add_argument("--append", action="store_true", help="append to an existing evidence pack")
    args = parser.parse_args()
    if args.profile != REQUIRED_PROFILE:
        parser.error(f"workspace-aware capture requires --profile {REQUIRED_PROFILE}")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if args.output_json.exists() and not args.append:
        parser.error("output JSON already exists; use --append to preserve prior cycles")

    existing = _load_rows(args.output_json) if args.append else []
    previous = _last_by_subject(existing)
    current = capture_live_evidence(
        client=DatabricksCLI(args.profile), catalog=args.catalog, schema=args.schema,
        warehouse_id=args.warehouse_id, pipeline_id=args.pipeline_id,
        pipeline_update_id=args.pipeline_update_id,
        orchestration_run_id=args.orchestration_run_id,
        timeout_seconds=args.timeout_seconds, previous=previous,
    )
    all_rows = [_row_from_dict(row) for row in existing] + current
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(evidence_document(all_rows), indent=2) + "\n", encoding="utf-8")
    args.output_markdown.write_text(render_markdown(all_rows), encoding="utf-8")
    cycle_count = len({row.orchestration_run_id for row in all_rows})
    print(f"Captured {len(current)} critical subject rows; evidence pack now has {cycle_count} cycle(s) and {len(all_rows)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
