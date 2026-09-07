"""Installed-wheel entry point for the attributed deterministic NEMWEB snapshot."""

from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path
from typing import Sequence

from .lander import land_snapshot


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume-path", required=True)
    parser.add_argument("--cycle-id", default="snapshot-v1")
    parser.add_argument("--snapshot-root")
    args = parser.parse_args(argv)
    root = Path(args.snapshot_root) if args.snapshot_root else Path(str(files("agentic_energy.resources").joinpath("nemweb_snapshot/v1")))
    result = land_snapshot(root, args.volume_path, run_id=args.cycle_id)
    print(result.manifest_path)
    return 0 if result.status == "success" else 1
