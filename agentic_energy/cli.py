from __future__ import annotations
import argparse
from .pipeline import DEFAULT_LIVE_METADATA, DEFAULT_METADATA, run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Agentic Energy metadata pipeline")
    parser.add_argument(
        "--metadata",
        nargs="?",
        const="",
        help="Metadata contract path; defaults to the packaged fixture or live contract",
    )
    parser.add_argument("--output", default="output")
    parser.add_argument(
        "--metadata-root",
        help="Approved root for external metadata and source files",
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--run-id", help="External orchestration run identifier")
    parser.add_argument(
        "--metadata-snapshot-id",
        nargs="?",
        const="",
        help="Immutable metadata snapshot identifier",
    )
    args = parser.parse_args()
    metadata = args.metadata or (DEFAULT_LIVE_METADATA if args.mode == "live" else DEFAULT_METADATA)
    counts = run_pipeline(
        metadata,
        args.output,
        metadata_root=args.metadata_root if args.metadata else None,
        mode=args.mode,
        run_id=args.run_id or None,
        metadata_snapshot_id=args.metadata_snapshot_id or None,
    )
    print("Pipeline complete: " + ", ".join(f"{key}={counts[key]}" for key in ("bronze", "silver", "quarantine", "gold")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
