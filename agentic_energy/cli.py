from __future__ import annotations
import argparse
import json
from pathlib import Path
from .pipeline import DEFAULT_LIVE_METADATA, DEFAULT_METADATA, run_pipeline
from .publish import publish_run, resolve_spark_writer


def _completed_run(output_dir: str, run_id: str | None) -> dict | None:
    """Return layer counts if *output_dir* already holds this run's evidence.

    Only a directory whose manifest carries exactly *run_id* qualifies, so a
    stale or unrelated run directory is never silently adopted: publishing one
    run's data under another run's key would make the manifest and the tables
    disagree. Returns None when there is nothing trustworthy to resume from, in
    which case the caller runs the pipeline and its write-once guard still
    applies.
    """
    if not run_id:
        return None
    manifest_path = Path(output_dir) / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict) or manifest.get("run_id") != run_id:
        return None
    layers = manifest.get("layers")
    return layers if isinstance(layers, dict) else None


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
    # Unity Catalog publication is opt-in. Absent these, the run behaves exactly
    # as before and writes only the immutable JSONL evidence, so the local
    # fixture path still needs no workspace, Spark, or credentials.
    parser.add_argument(
        "--publish-catalog",
        nargs="?",
        const="",
        help="Unity Catalog catalog to publish the run's Delta tables into",
    )
    parser.add_argument(
        "--publish-schema",
        nargs="?",
        const="",
        help="Unity Catalog schema to publish the run's Delta tables into",
    )
    args = parser.parse_args()
    publish_catalog = args.publish_catalog or None
    publish_schema = args.publish_schema or None
    if bool(publish_catalog) != bool(publish_schema):
        parser.error("--publish-catalog and --publish-schema must be provided together")
    # A published run must be identifiable by run_id, otherwise republishing
    # cannot be idempotent and rows from separate runs become indistinguishable
    # in the governed tables.
    if publish_catalog and not (args.run_id or None):
        parser.error("--run-id is required when publishing to Unity Catalog")
    metadata = args.metadata or (DEFAULT_LIVE_METADATA if args.mode == "live" else DEFAULT_METADATA)
    # A retried task must be able to converge. Run evidence is write-once, so the
    # pipeline refuses to overwrite an existing run directory. If an attempt
    # wrote its evidence and then failed during publication, re-running the
    # pipeline can never succeed: every retry dies on OUTPUT_ALREADY_EXISTS,
    # which masks the original cause. Resume at publication instead, which is
    # safe because publication is idempotent per run_id.
    completed = _completed_run(args.output, args.run_id or None)
    if completed is None:
        counts = run_pipeline(
            metadata,
            args.output,
            metadata_root=args.metadata_root if args.metadata else None,
            mode=args.mode,
            run_id=args.run_id or None,
            metadata_snapshot_id=args.metadata_snapshot_id or None,
        )
        print("Pipeline complete: " + ", ".join(f"{key}={counts[key]}" for key in ("bronze", "silver", "quarantine", "gold")))
    else:
        counts = completed
        print(
            f"Run evidence for run_id {args.run_id} already complete; "
            "resuming at publication: "
            + ", ".join(f"{key}={counts.get(key)}" for key in ("bronze", "silver", "quarantine", "gold"))
        )
    if publish_catalog and publish_schema:
        published = publish_run(
            args.output,
            catalog=publish_catalog,
            schema=publish_schema,
            run_id=args.run_id,
            writer=resolve_spark_writer(),
        )
        print(
            f"Published to {publish_catalog}.{publish_schema}: "
            + ", ".join(f"{table}={published[table]}" for table in sorted(published))
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
