#!/usr/bin/env python3
"""Fail when NEMWEB pipeline sources use legacy APIs or runtime side effects."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "agentic_energy" / "nemweb" / "pipeline"

FORBIDDEN_TEXT = {
    "legacy dlt import": re.compile(r"(?:^|\n)\s*(?:from\s+dlt\s+|import\s+dlt\b)"),
    "legacy dlt read": re.compile(r"\bdlt\.read(?:_stream)?\s*\("),
    "legacy dp read": re.compile(r"\bdp\.read(?:_stream)?\s*\("),
    "legacy LIVE prefix": re.compile(r"\bLIVE\."),
    "legacy CREATE LIVE": re.compile(r"\bCREATE\s+(?:STREAMING\s+)?LIVE\b", re.I),
    "legacy apply_changes": re.compile(r"\b(?:dlt|dp)\.apply_changes\s*\("),
    "deprecated input_file_name": re.compile(r"\binput_file_name\s*\("),
    "managed checkpoint override": re.compile(r"checkpointLocation|schemaLocation"),
}
FORBIDDEN_IMPORT_ROOTS = {"requests", "urllib", "httpx", "socket"}
FORBIDDEN_CALL_NAMES = {"open"}
FORBIDDEN_CALL_ATTRIBUTES = {
    "write",
    "writeStream",
    "save",
    "saveAsTable",
    "start",
    "toPandas",
    "collect",
    "write_text",
    "write_bytes",
    "mkdir",
    "unlink",
    "rename",
    "replace",
}


def _call_name(node: ast.Call) -> str | None:
    target = node.func
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def findings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems = [label for label, pattern in FORBIDDEN_TEXT.items() if pattern.search(text)]
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            for root in sorted(roots & FORBIDDEN_IMPORT_ROOTS):
                problems.append(f"network import {root}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in FORBIDDEN_IMPORT_ROOTS:
                problems.append(f"network import {root}")
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name in FORBIDDEN_CALL_NAMES:
                problems.append(f"arbitrary file call {name}()")
            elif name in FORBIDDEN_CALL_ATTRIBUTES:
                problems.append(f"runtime side-effect call .{name}()")
    return sorted(set(problems))


def main() -> int:
    paths = sorted(PIPELINE.glob("*.py"))
    if not paths:
        print("ERROR: no NEMWEB pipeline Python sources found", file=sys.stderr)
        return 1
    failures = {path: findings(path) for path in paths}
    failures = {path: items for path, items in failures.items() if items}
    if failures:
        for path, items in failures.items():
            relative = path.relative_to(ROOT)
            for item in items:
                print(f"{relative}: {item}", file=sys.stderr)
        return 1
    print(f"Modern pipeline API check passed: {len(paths)} Python sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
