#!/usr/bin/env python3
"""Backfill NEM DISPATCHIS history from the NEMWEB Archive/ daily reports.

Why this exists
---------------
`--mode live` in the pipeline fetches only the *latest* DISPATCHIS archive from
NEMWEB's ``Current/`` directory: five rows, one five-minute interval. That is
enough to prove live acquisition works, but not enough to analyse anything --
price spikes and negative-price runs are episodic, so a short window sees none
of them.

NEMWEB's ``Archive/`` directory holds roughly a year of *daily* zips, and each
daily zip contains ~288 nested five-minute zips. That means one HTTP request
yields a full day (1,440 rows across five regions) instead of 288 requests.

Rows are parsed with the pipeline's own ``parse_dispatchis_zip``, so output is
identical in shape to Silver-layer rows. This script deliberately does not
reimplement any parsing or validation.

Scope and non-goals
-------------------
This is an analyst-facing backfill utility, not part of the governed pipeline.
It writes plain JSONL to a local directory; it does not write to Unity Catalog,
register tables, or claim the determinism guarantees of ``--mode fixture``.
Upload is left to the caller (see --help epilog) so that catalog, schema, and
volume names stay out of this file, matching the repo convention of never
committing workspace-specific values.

Resumable: a day whose output file already exists and is non-empty is skipped,
so re-running after an interruption only fetches what is missing.

Usage
-----
    python scripts/backfill-nem-history.py --days 30 --out ./nem-history

Then upload wherever you need it, e.g. Hive-partitioned into a UC Volume:

    databricks fs mkdir dbfs:/Volumes/<cat>/<schema>/<vol>/live/history/dispatchis
    # ... one mkdir + cp per dispatch_date=YYYY-MM-DD partition

Data caveat: AEMO's ``PUBLIC_DISPATCHIS_<YYYYMMDD>.zip`` spans 00:05..24:00, so
its final ``00:00`` interval belongs to the *next* calendar day. Partition by
the row's ``interval_datetime`` (as ``--partition-by-interval`` does), not by
the source filename, or per-day aggregates will be off by one interval.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Import the pipeline's parser rather than duplicating it. Works when run from
# the repo root; falls back to inserting the repo root on sys.path.
try:
    from agentic_energy.acquisition import _request, parse_dispatchis_zip
except ModuleNotFoundError:  # pragma: no cover - convenience for direct runs
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agentic_energy.acquisition import _request, parse_dispatchis_zip

ARCHIVE_URL = "https://nemweb.com.au/Reports/Archive/DispatchIS_Reports/"
ALLOWED_HOST = "nemweb.com.au"
DAY_ZIP_RE = re.compile(r"PUBLIC_DISPATCHIS_(\d{8})\.zip$", re.IGNORECASE)


def list_archive_days() -> list[str]:
    """Return every YYYYMMDD available in NEMWEB Archive/, oldest first."""
    html = _request(ARCHIVE_URL, allowed_host=ALLOWED_HOST).decode("latin-1")
    hrefs = re.findall(r"href=[\"']([^\"']+\.zip)[\"']", html, flags=re.IGNORECASE)
    return sorted({m.group(1) for h in hrefs if (m := DAY_ZIP_RE.search(h))})


def fetch_day(day: str, out_dir: Path) -> tuple[str, int, int, str]:
    """Fetch and parse one daily archive.

    Returns (day, rows_written, member_failures, note). Never raises: a failed
    day is reported so the caller can decide, because a partial backfill with a
    known gap is more useful than an aborted run.
    """
    path = out_dir / f"{day}.jsonl"
    if path.exists() and path.stat().st_size > 0:
        with path.open() as handle:
            return day, sum(1 for _ in handle), 0, "cached"

    url = f"{ARCHIVE_URL}PUBLIC_DISPATCHIS_{day}.zip"
    try:
        payload = _request(url, allowed_host=ALLOWED_HOST)
    except Exception as exc:  # noqa: BLE001 - report, do not abort the batch
        return day, 0, 0, f"FETCH_FAILED {type(exc).__name__}: {str(exc)[:80]}"
    try:
        outer = zipfile.ZipFile(io.BytesIO(payload))
    except Exception as exc:  # noqa: BLE001
        return day, 0, 0, f"BAD_ZIP {type(exc).__name__}"

    rows: list[dict] = []
    failures = 0
    for name in outer.namelist():
        if not name.lower().endswith(".zip"):
            continue
        try:
            rows.extend(parse_dispatchis_zip(outer.read(name), f"{url}!{name}"))
        except Exception:  # noqa: BLE001 - one bad interval must not lose a day
            failures += 1

    tmp = path.with_suffix(".jsonl.part")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    tmp.replace(path)  # atomic, so an interrupted run never leaves a half file
    return day, len(rows), failures, "ok"


def repartition_by_interval(out_dir: Path, parts_dir: Path) -> tuple[int, int]:
    """Rewrite per-source-day files into dispatch_date=YYYY-MM-DD partitions.

    Partitioning uses each row's interval_datetime, which is what makes
    per-day aggregates correct despite AEMO's 00:05..24:00 file convention.
    """
    buckets: dict[str, list[dict]] = collections.defaultdict(list)
    for src in sorted(out_dir.glob("*.jsonl")):
        with src.open() as handle:
            for line in handle:
                row = json.loads(line)
                buckets[row["interval_datetime"][:10]].append(row)

    total = 0
    for date, rows in sorted(buckets.items()):
        target = parts_dir / f"dispatch_date={date}"
        target.mkdir(parents=True, exist_ok=True)
        rows.sort(key=lambda r: (r["interval_datetime"], r["region"]))
        with (target / "part-0000.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                total += 1
    return len(buckets), total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill NEM DISPATCHIS history from NEMWEB Archive/ daily zips.",
        epilog="Analyst utility; not part of the governed pipeline. Writes local JSONL only.",
    )
    parser.add_argument("--days", type=int, default=30, help="How many of the most recent days to fetch (default 30)")
    parser.add_argument("--out", default="./nem-history", help="Output directory (default ./nem-history)")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent daily-archive fetches (default 6)")
    parser.add_argument(
        "--partition-by-interval",
        action="store_true",
        help="Also emit dispatch_date=YYYY-MM-DD partitions for query engines that prune on path",
    )
    args = parser.parse_args()

    out_dir = Path(args.out) / "days"
    out_dir.mkdir(parents=True, exist_ok=True)

    available = list_archive_days()
    if not available:
        print("No daily archives found; NEMWEB layout may have changed.", file=sys.stderr)
        return 1
    days = available[-args.days :]
    print(f"Archive lists {len(available)} days; fetching newest {len(days)}: {days[0]}..{days[-1]}", flush=True)

    total = failures = 0
    bad_days: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for day, rows, member_failures, note in pool.map(lambda d: fetch_day(d, out_dir), days):
            total += rows
            failures += member_failures
            if note not in ("ok", "cached"):
                bad_days.append(day)
            suffix = "" if note in ("ok", "cached") else f"  <-- {note}"
            print(f"  {day}: rows={rows:6d} member_failures={member_failures:3d} {note}{suffix}", flush=True)

    print(f"\nTOTAL rows={total} member_failures={failures} days={len(days)}")
    if bad_days:
        print(f"INCOMPLETE: {len(bad_days)} day(s) failed: {', '.join(bad_days)}", file=sys.stderr)

    if args.partition_by_interval:
        parts_dir = Path(args.out) / "parts"
        n_parts, n_rows = repartition_by_interval(out_dir, parts_dir)
        print(f"Wrote {n_parts} dispatch_date partitions ({n_rows} rows) under {parts_dir}")

    return 1 if bad_days else 0


if __name__ == "__main__":
    raise SystemExit(main())
