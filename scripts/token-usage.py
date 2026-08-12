#!/usr/bin/env python3
"""Report agent token usage for this session and refresh the README badge.

Reads the pi session transcript named by ``PI_SESSION_FILE`` (a JSONL file, one
record per line) and totals the ``usage`` block that the harness attaches to each
assistant message.

Two different totals matter and are easy to conflate:

*   **Billed tokens** — the sum of every call's ``input`` plus ``output``. A chat
    agent re-sends the whole conversation on every turn, so ``input`` grows
    roughly linearly and the sum is dominated by re-reading context. This is
    what a provider invoices.
*   **Conversation size** — the final call's ``input`` plus all ``output`` ever
    generated, i.e. roughly the unique content produced. Much smaller.

Reporting only the first figure overstates the work done; reporting only the
second understates the cost. Both are emitted.

Usage::

    python3 scripts/token-usage.py            # print a report
    python3 scripts/token-usage.py --write     # also refresh the README badge
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
BEGIN = "<!-- token-usage:begin -->"
END = "<!-- token-usage:end -->"


def _humanise(value: int) -> str:
    """Render a token count compactly: 14_531_389 -> '14.5M'."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def collect(session_file: Path) -> dict:
    totals = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "reasoning": 0}
    cost = 0.0
    calls = 0
    last_input = 0
    last_timestamp = None

    for line in session_file.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            # A transcript being appended to concurrently can end mid-record.
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        calls += 1
        for key in totals:
            totals[key] += usage.get(key) or 0
        cost += (usage.get("cost") or {}).get("total") or 0.0
        last_input = usage.get("input") or last_input
        last_timestamp = record.get("timestamp") or last_timestamp

    billed = totals["input"] + totals["output"]
    return {
        "calls": calls,
        "billed": billed,
        "conversation": last_input + totals["output"],
        "context_last": last_input,
        "cost": cost,
        "timestamp": last_timestamp,
        **totals,
    }


def render_badge(stats: dict) -> str:
    """A shields.io badge plus the caveat, as one README block."""
    billed = _humanise(stats["billed"])
    output = _humanise(stats["output"])
    return (
        f"{BEGIN}\n"
        f"![agent tokens](https://img.shields.io/badge/agent%20tokens-"
        f"{billed}%20billed%20%7C%20{output}%20generated-blue)\n"
        f"\n"
        f"<sub>Token usage for the AI agent session that produced the recent "
        f"commits: **{stats['billed']:,} billed** across {stats['calls']} model "
        f"calls, of which **{stats['output']:,}** are generated output. Billed "
        f"input is dominated by re-sending the conversation each turn; the unique "
        f"conversation is about {stats['conversation']:,} tokens. Refresh with "
        f"`python3 scripts/token-usage.py --write`. See "
        f"[`docs/test-evidence/agent-token-usage.md`]"
        f"(docs/test-evidence/agent-token-usage.md).</sub>\n"
        f"{END}"
    )


def write_badge(stats: dict) -> bool:
    text = README.read_text()
    badge = render_badge(stats)
    if BEGIN in text and END in text:
        updated = re.sub(
            re.escape(BEGIN) + r".*?" + re.escape(END), badge, text, flags=re.DOTALL
        )
    else:
        # Insert directly under the H1 title so it reads as a subtitle.
        lines = text.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith("# "):
                lines.insert(index + 1, "\n" + badge + "\n")
                break
        else:
            raise SystemExit("README.md has no '# ' title to anchor the badge to")
        updated = "".join(lines)
    if updated == text:
        return False
    README.write_text(updated)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="refresh the README badge")
    parser.add_argument("--session-file", default=os.environ.get("PI_SESSION_FILE", ""))
    args = parser.parse_args()

    if not args.session_file:
        print(
            "PI_SESSION_FILE is not set, so there is no transcript to measure.\n"
            "This script only works inside an agent session that records usage.",
            file=sys.stderr,
        )
        return 2
    session_file = Path(args.session_file)
    if not session_file.is_file():
        print(f"session transcript not found: {session_file}", file=sys.stderr)
        return 2

    stats = collect(session_file)
    if not stats["calls"]:
        print("no usage records found in the transcript", file=sys.stderr)
        return 1

    print(f"model calls        : {stats['calls']:,}")
    print(f"input  (summed)    : {stats['input']:,}")
    print(f"output (summed)    : {stats['output']:,}")
    print(f"cache read/write   : {stats['cacheRead']:,} / {stats['cacheWrite']:,}")
    print(f"reasoning          : {stats['reasoning']:,}")
    print(f"BILLED total       : {stats['billed']:,}  ({_humanise(stats['billed'])})")
    print(f"conversation size  : {stats['conversation']:,}  (last context + all output)")
    print(f"final context      : {stats['context_last']:,}")
    print(f"reported cost      : {stats['cost']}  (0 when the harness does not price calls)")
    print(f"last activity      : {stats['timestamp']}")

    if args.write:
        print("README badge updated" if write_badge(stats) else "README badge already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
