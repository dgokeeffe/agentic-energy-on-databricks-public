#!/usr/bin/env python3
"""Validate local links in tracked Markdown without network access."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    failures: list[str] = []
    tracked = subprocess.check_output(["git", "ls-files", "*.md"], cwd=ROOT, text=True).splitlines()
    for relative in tracked:
        path = ROOT / relative
        # A tracked path can be absent when a deletion is staged but not yet
        # committed. Skip it rather than crashing before any link is checked.
        if not path.is_file():
            continue
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            target = target.strip().split(" ", 1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (path.parent / target_path).resolve()
            if not resolved.exists():
                failures.append(f"{relative}: missing {target}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Markdown links valid: {len(tracked)} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
