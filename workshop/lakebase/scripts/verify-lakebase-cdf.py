#!/usr/bin/env python3
"""Verify prepared Lakebase CDF history and deterministic current state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "nemweb_foundation"))

from workshop.lakebase.cdf import reduce_current_state, validate_update_pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("history", type=Path)
    parser.add_argument("--current", type=Path)
    args = parser.parse_args()
    text = args.history.read_text().strip()
    events = [json.loads(line) for line in text.splitlines()] if args.history.suffix == ".jsonl" else json.loads(text)
    kinds = {row["_pg_change_type"] for row in events}
    required = {"insert", "update_preimage", "update_postimage", "delete"}
    validate_update_pairs(events)
    current = reduce_current_state(events)
    if args.current:
        expected = json.loads(args.current.read_text())
        if current != expected:
            print(json.dumps({"status": "mismatch", "actual": current}, sort_keys=True))
            return 1
    print(json.dumps({"status": "pass", "events": len(events), "current_rows": len(current)}, sort_keys=True))
    return 0 if required <= kinds else 1


if __name__ == "__main__":
    raise SystemExit(main())
