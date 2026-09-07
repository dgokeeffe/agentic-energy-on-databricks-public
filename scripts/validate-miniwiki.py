#!/usr/bin/env python3
"""Validate the small, committed workshop miniwiki.

This is intentionally a link-and-presence check, not a task database. Markdown
pages remain free-form; the validator only protects the navigation spine and
prevents broken relative links from making a handoff disappear.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "miniwiki"
REQUIRED = ("index.md", "now.md", "guardrails.md", "session-template.md")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def split_target(raw_target: str) -> tuple[str, str]:
    raw_target = unquote(raw_target.strip())
    target, _, fragment = raw_target.partition("#")
    target = target.split("?", 1)[0]
    return target, fragment


def resolve_link(page: Path, raw_target: str) -> tuple[Path, str] | None:
    target, fragment = split_target(raw_target)
    if target.startswith(("http://", "https://", "mailto:")):
        return None
    if not target:
        return page.resolve(), fragment
    candidate = (page.parent / target).resolve()
    if candidate.is_dir():
        candidate /= "index.md"
    return candidate, fragment


def heading_slugs(page: Path) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for heading in HEADING_RE.findall(page.read_text(encoding="utf-8")):
        plain = re.sub(r"[`*_]", "", heading).lower()
        base = re.sub(r"[^\w\s-]", "", plain).strip().replace(" ", "-")
        if not base:
            continue
        number = counts.get(base, 0)
        slug = base if number == 0 else f"{base}-{number}"
        counts[base] = number + 1
        slugs.add(slug)
    return slugs


def main() -> int:
    if not WIKI.is_dir():
        print(f"FAIL miniwiki directory missing: {WIKI}")
        return 1

    pages = sorted(WIKI.rglob("*.md"))
    failures: list[str] = []
    known = set(pages)
    for relative in REQUIRED:
        page = WIKI / relative
        if page not in known:
            failures.append(f"missing required page: miniwiki/{relative}")
        elif not page.read_text(encoding="utf-8").strip():
            failures.append(f"empty required page: miniwiki/{relative}")

    for page in pages:
        text = page.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            resolved = resolve_link(page, raw_target)
            if resolved is None:
                continue
            target, fragment = resolved
            if not target.exists():
                failures.append(
                    f"{page.relative_to(ROOT)} links to missing path: {raw_target}"
                )
                continue
            if fragment and target.suffix == ".md":
                if fragment.lower() not in heading_slugs(target):
                    failures.append(
                        f"{page.relative_to(ROOT)} links to missing heading: {raw_target}"
                    )

    if failures:
        print("Miniwiki validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1

    print(f"Miniwiki valid: {len(pages)} Markdown pages; relative links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
