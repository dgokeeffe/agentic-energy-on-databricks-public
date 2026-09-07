#!/usr/bin/env python3
"""Fail closed on repository layout, retired APIs, schedules, and private values."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RETIRED = {
    "import dlt": re.compile(r"(?:^|\n)\s*(?:import dlt|from dlt import)"),
    "dlt.read": re.compile(r"\bdlt\.read(?:_stream)?\s*\("),
    "dp.read": re.compile(r"\bdp\.read(?:_stream)?\s*\("),
    "LIVE prefix": re.compile(r"\bLIVE\."),
    "CREATE LIVE": re.compile(r"\bCREATE\s+(?:STREAMING\s+)?LIVE\b", re.I),
    "old apply_changes": re.compile(r"\b(?:dlt|dp)\.apply_changes\s*\("),
    "retired synced bundle": re.compile(r"synced_database_tables"),
    "retired database CLI": re.compile(r"\bdatabricks\s+database\b"),
    "retired apps update": re.compile(r"\bdatabricks\s+apps\s+update\b"),
}
PRIVATE = {
    "token": re.compile(r"\bdapi[a-zA-Z0-9]{12,}"),
    "private workspace host": re.compile(r"https://adb-[0-9]+\.[0-9]+\.[a-z]+databricks\.net"),
    "tenant UUID": re.compile(r"\btenant[_-]?id\s*[:=]\s*[0-9a-f-]{20,}", re.I),
    "principal UUID": re.compile(r"\b(?:service[_-]?principal|client)[_-]?id\s*[:=]\s*[0-9a-f-]{20,}", re.I),
}


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    failures: list[str] = []
    retired_path = "reference" + "_solution/"
    if any(name.startswith(retired_path) for name in tracked):
        failures.append("tracked retired foundation path remains")
    executable_suffixes = {".py", ".ts", ".tsx", ".js", ".yml", ".yaml", ".sql"}
    for name in tracked:
        path = ROOT / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in PRIVATE.items():
            if pattern.search(text):
                failures.append(f"{name}: {label}")
        product_code = (
            "tests" not in path.parts
            and path.resolve() != Path(__file__).resolve()
            and not path.name.startswith("check_modern_pipeline_apis")
        )
        if path.suffix in executable_suffixes and product_code:
            for label, pattern in RETIRED.items():
                if pattern.search(text):
                    failures.append(f"{name}: {label}")
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required for schedule validation") from exc
    for name in tracked:
        if not name.endswith((".yml", ".yaml")) or not (ROOT / name).is_file():
            continue
        try:
            document = yaml.safe_load((ROOT / name).read_text())
        except Exception:
            continue
        for node in _walk(document):
            schedule = node.get("schedule")
            trigger = node.get("trigger")
            if isinstance(schedule, dict) and schedule.get("pause_status") != "PAUSED":
                failures.append(f"{name}: schedule is not paused")
            if isinstance(trigger, dict) and trigger.get("pause_status") != "PAUSED":
                failures.append(f"{name}: trigger is not paused")
    if failures:
        raise SystemExit("\n".join(sorted(set(failures))))
    print(f"Repository safety valid: {len(tracked)} tracked and untracked candidate files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
