#!/usr/bin/env python3
"""Validate the attributed NEMWEB snapshot by two independent deterministic runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from agentic_energy.ingestion.lander import land_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "tests" / "fixtures" / "nemweb" / "v1"


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def validate(snapshot_root: Path) -> dict[str, object]:
    source_manifest = json.loads((snapshot_root / "manifest.json").read_text(encoding="utf-8"))
    if source_manifest.get("snapshot_version") != "v1":
        raise ValueError("snapshot_version must be v1")
    required = set(source_manifest.get("required_families", []))
    if required != {"dispatchis", "dispatch_scada", "next_day_dispatch", "registration"}:
        raise ValueError(f"snapshot critical families differ from contract: {sorted(required)}")
    for item in source_manifest.get("artifacts", []):
        if not isinstance(item.get("synthetic"), bool) or "not live evidence" not in item.get("classification", ""):
            raise ValueError("every snapshot artifact must declare synthetic status and that it is not live evidence")

    with tempfile.TemporaryDirectory(prefix="nemweb-snapshot-a-") as a, tempfile.TemporaryDirectory(prefix="nemweb-snapshot-b-") as b:
        first = land_snapshot(snapshot_root, Path(a), run_id="snapshot-validation")
        second = land_snapshot(snapshot_root, Path(b), run_id="snapshot-validation")
        if first.status != "success" or second.status != "success":
            raise ValueError("snapshot lander did not succeed twice")
        first_hashes, second_hashes = _hash_tree(Path(a)), _hash_tree(Path(b))
        if first_hashes != second_hashes:
            changed = sorted(set(first_hashes) ^ set(second_hashes) | {k for k in first_hashes.keys() & second_hashes.keys() if first_hashes[k] != second_hashes[k]})
            raise ValueError(f"snapshot runs are not byte deterministic: {changed}")
        manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
        if manifest["parsed_row_count"] != sum(item["row_count"] for item in manifest["archives"]):
            raise ValueError("snapshot manifest row reconciliation failed")
        return {
            "snapshot_version": source_manifest["snapshot_version"],
            "manifest_sha256": first.manifest_sha256,
            "archive_count": first.archive_count,
            "unique_archive_count": first.unique_archive_count,
            "parsed_row_count": first.parsed_row_count,
            "quarantine_count": first.quarantine_count,
            "file_count": len(first_hashes),
            "deterministic": True,
            "idempotency_method": "two isolated write-once roots with equal relative-path SHA-256 maps",
            "live_evidence": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.snapshot_root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
