#!/usr/bin/env python3
"""Reconcile prepared source and synced-table JSON rows by deterministic key."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def load(path: Path) -> dict[tuple[str, str], dict]:
    rows = json.loads(path.read_text())
    keyed = {(str(row["region_id"]), str(row["interval_end"])): row for row in rows}
    if len(keyed) != len(rows):
        raise ValueError(f"duplicate region/interval key in {path}")
    return keyed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("synced", type=Path)
    parser.add_argument("--max-age-seconds", type=int, default=900)
    args = parser.parse_args()
    source, synced = load(args.source), load(args.synced)
    missing, extra = sorted(source.keys() - synced.keys()), sorted(synced.keys() - source.keys())
    mismatched = sorted(key for key in source.keys() & synced.keys() if source[key] != synced[key])
    newest = max(
        datetime.fromisoformat(row["gold_published_at"].replace("Z", "+00:00"))
        for row in synced.values()
    )
    age = (datetime.now(timezone.utc) - newest.astimezone(timezone.utc)).total_seconds()
    result = {"missing": missing, "extra": extra, "mismatched": mismatched, "age_seconds": age}
    print(json.dumps(result, default=list, sort_keys=True))
    return 0 if not missing and not extra and not mismatched and age <= args.max_age_seconds else 1


if __name__ == "__main__":
    raise SystemExit(main())
