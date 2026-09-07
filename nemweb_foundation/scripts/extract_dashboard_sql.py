#!/usr/bin/env python3
"""Extract one SQL statement per AI/BI dashboard dataset.

The manifest is deterministic and is consumed by the workspace SQL gate. This
script never creates, updates or publishes a dashboard.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def extract_dashboard_sql(dashboard_path: Path) -> list[dict[str, str]]:
    payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    extracted: list[dict[str, str]] = []
    seen: set[str] = set()
    for dataset in payload.get("datasets", []):
        name = dataset.get("name")
        lines = dataset.get("queryLines")
        if not isinstance(name, str) or not name:
            raise ValueError("every dashboard dataset requires a non-empty name")
        if name in seen:
            raise ValueError(f"duplicate dashboard dataset name: {name}")
        seen.add(name)
        if not isinstance(lines, list) or not lines or not all(isinstance(line, str) for line in lines):
            raise ValueError(f"dataset {name!r} requires non-empty string queryLines")
        sql = "".join(lines).strip()
        if not sql:
            raise ValueError(f"dataset {name!r} has empty SQL")
        # A terminal semicolon is harmless, but an internal semicolon would make
        # this more than the one allowed statement per dashboard dataset.
        if ";" in sql.rstrip(";"):
            raise ValueError(f"dataset {name!r} contains multiple SQL statements")
        extracted.append(
            {
                "dataset": name,
                "sql": sql.rstrip(";") + ";\n",
                "sha256": hashlib.sha256(sql.rstrip(";").encode("utf-8")).hexdigest(),
            }
        )
    if not extracted:
        raise ValueError("dashboard has no SQL datasets")
    return extracted


def write_extracted(extracted: list[dict[str, str]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []
    for item in extracted:
        path = output / f"{item['dataset']}.sql"
        path.write_text(item["sql"], encoding="utf-8")
        manifest.append({"dataset": item["dataset"], "file": path.name, "sha256": item["sha256"]})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dashboard", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    extracted = extract_dashboard_sql(args.dashboard)
    write_extracted(extracted, args.output)
    print(f"Extracted {len(extracted)} dashboard SQL statements to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
