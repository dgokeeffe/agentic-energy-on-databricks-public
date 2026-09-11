#!/usr/bin/env python3
"""Spark Python task for bounded NEMWEB-to-Delta landing."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from agentic_energy.ingestion.delta_lander import (
    COMPLETE_STATUSES,
    ensure_landing_tables,
    prepare_landing_batch,
)
from agentic_energy.ingestion.lander import (
    ArchiveInput,
    LanderLimits,
    NemwebClient,
    _discover_live,
    land_archives,
)
from agentic_energy.ingestion.source_registry import get_subject_by_key, subjects_for_scope


def _safe(name: str) -> str:
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("unsafe identifier")
    return f"`{name}`"


def _table(catalog: str, schema: str, table: str) -> str:
    return ".".join((_safe(catalog), _safe(schema), _safe(table)))


def _snapshot_inputs(root: Path, mode: str, scope: str) -> list[ArchiveInput]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    families = {subject.report_family for subject in subjects_for_scope(scope)}
    result = []
    for item in manifest["artifacts"]:
        if item["report_family"] not in families:
            continue
        result.append(ArchiveInput(
            item["report_family"], item["publication"], item["source_filename"],
            (root / item["path"]).read_bytes(), urlsplit(item["source_url"]).path, mode,
            item["retrieved_at"], bool(item.get("synthetic", False)),
            item.get("source_publication_at") or item["retrieved_at"],
        ))
    return result


def _merge_insert_only(spark, target: str, rows: list[dict], keys: tuple[str, ...], casts: dict[str, str] | None = None) -> int:
    if not rows:
        return 0
    view = "_nemweb_landing_batch"
    spark.createDataFrame(rows).dropDuplicates(list(keys)).createOrReplaceTempView(view)
    columns = tuple(rows[0])
    select = ", ".join(f"CAST({key} AS {casts[key]}) AS {key}" if casts and key in casts else key for key in columns)
    source = f"(SELECT {select} FROM {view})"
    condition = " AND ".join(f"target.{key} <=> source.{key}" for key in keys)
    before = spark.sql(f"SELECT COUNT(*) AS c FROM {target}").first()[0]
    spark.sql(f"MERGE INTO {target} target USING {source} source ON {condition} WHEN NOT MATCHED THEN INSERT ({', '.join(columns)}) VALUES ({', '.join('source.' + c for c in columns)})")
    after = spark.sql(f"SELECT COUNT(*) AS c FROM {target}").first()[0]
    return int(after - before)


def _write(spark, batch, catalog: str, schema: str) -> tuple[str, int]:
    ensure_landing_tables(spark, catalog, schema)
    run_table = _table(catalog, schema, "landing_nem_runs")
    run_rows = [{"run_id": batch.run_id, "source_mode": batch.source_mode, "scope": batch.scope, "status": "STARTED", "landed_at": batch.landed_at, "completed_at": batch.landed_at}]
    _merge_insert_only(spark, run_table, run_rows, ("run_id",), {"landed_at": "TIMESTAMP", "completed_at": "TIMESTAMP"})
    inserted = 0
    association_rows = []
    for key, records in batch.records_by_subject.items():
        subject = get_subject_by_key(key)
        rows = []
        for record in records:
            p = record.provenance
            rows.append({
                "source_record_id": record.source_record_id, "source_version_id": record.source_version_id,
                "source_mode": record.source_mode, "subject_key": key,
                "typed_values": {k: None if v is None else str(v) for k, v in record.typed_values.items()},
                "unexpected_values": dict(record.unexpected_values) or {"__none__": ""}, "source_filename": p.source_filename,
                "source_url_path": p.source_url_path, "source_archive_sha256": p.archive_sha256,
                "source_csv_member": p.csv_member, "source_row_number": p.source_row_number,
                "source_publication_at": p.source_publication_at, "retrieved_at": p.retrieved_at,
                "landed_at": p.landed_at,
            })
            association_rows.append({"run_id": batch.run_id, "subject_key": key,
                "source_record_id": record.source_record_id, "source_version_id": record.source_version_id,
                "associated_at": batch.landed_at})
        inserted += _merge_insert_only(spark, _table(catalog, schema, subject.landing_table), rows,
                                       ("source_record_id",), {"source_publication_at":"TIMESTAMP", "retrieved_at":"TIMESTAMP", "landed_at":"TIMESTAMP"})
    _merge_insert_only(spark, _table(catalog, schema, "landing_nem_run_records"), association_rows,
                       ("run_id", "subject_key", "source_record_id"), {"associated_at":"TIMESTAMP"})
    _merge_insert_only(spark, _table(catalog, schema, "landing_nem_files"),
        [asdict(x) | {"run_id": batch.run_id} for x in batch.files], ("run_id", "archive_sha256"),
        {"source_publication_at":"TIMESTAMP", "retrieved_at":"TIMESTAMP"})
    _merge_insert_only(spark, _table(catalog, schema, "landing_nem_rejections"),
        [asdict(x) | {"run_id": batch.run_id} for x in batch.rejects], ("run_id", "archive_sha256", "csv_member", "row_number"))
    _merge_insert_only(spark, _table(catalog, schema, "landing_nem_run_subjects"),
        [asdict(x) | {"run_id": batch.run_id, "status": batch.status} for x in batch.subject_results], ("run_id", "subject_key"))
    status = batch.status if inserted else ("COMPLETE_NO_NEW_SOURCE" if batch.status in COMPLETE_STATUSES else batch.status)
    spark.sql(f"UPDATE {run_table} SET status='{status}', completed_at=current_timestamp() WHERE run_id='{batch.run_id}' AND status='STARTED'")
    _merge_insert_only(spark, _table(catalog, schema, "landing_nem_run_events"),
        [{"run_id": batch.run_id, "status": "STARTED", "event_at": batch.landed_at},
         {"run_id": batch.run_id, "status": status, "event_at": batch.landed_at}], ("run_id", "status"), {"event_at":"TIMESTAMP"})
    return status, inserted


def main() -> int:
    from pyspark.sql import SparkSession

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("snapshot", "live"), required=True)
    parser.add_argument("--scope", choices=("critical", "context", "regional"), required=True)
    parser.add_argument("--catalog", required=True); parser.add_argument("--schema", required=True)
    parser.add_argument("--volume-path", required=True); parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--allow-live", choices=("true", "false"), default="false")
    parser.add_argument("--snapshot-version", choices=("v1", "v2"), default="v2")
    parser.add_argument("--snapshot-root"); parser.add_argument("--critical-lookback-hours", type=int, default=2)
    parser.add_argument("--context-lookback-days", type=int, default=3); parser.add_argument("--max-files", type=int, default=100)
    parser.add_argument("--network-timeout-seconds", type=float, default=30); parser.add_argument("--network-retry-count", type=int, default=3)
    args = parser.parse_args()
    if args.mode == "live" and args.allow_live != "true":
        raise RuntimeError("live mode requires deployment-controlled approval")
    limits = LanderLimits(timeout_seconds=args.network_timeout_seconds, retry_count=args.network_retry_count, max_files_per_cycle=args.max_files)
    if args.mode == "snapshot":
        root = Path(args.snapshot_root) if args.snapshot_root else Path(str(files("agentic_energy.resources").joinpath(f"nemweb_snapshot/{args.snapshot_version}")))
        archives = _snapshot_inputs(root, args.mode, args.scope)
    else:
        archives, _ = _discover_live(args.scope, NemwebClient(limits), critical_lookback_hours=args.critical_lookback_hours, context_lookback_days=args.context_lookback_days)
    # Raw archive and manifest evidence remain immutable on the Volume.
    file_result = land_archives(archives, args.volume_path, run_id=args.cycle_id, source_mode=args.mode,
                               required_families=tuple(sorted({s.report_family for s in subjects_for_scope(args.scope)})), limits=limits, raise_on_failure=False)
    batch = prepare_landing_batch(archives, run_id=args.cycle_id, source_mode=args.mode, scope=args.scope)
    if file_result.status != "success" and batch.status in COMPLETE_STATUSES:
        batch = type(batch)(**{**batch.__dict__, "status": "FAILED"})
    status, inserted = _write(SparkSession.getActiveSession() or SparkSession.builder.getOrCreate(), batch, args.catalog, args.schema)
    print(json.dumps({"run_id": args.cycle_id, "status": status, "inserted_source_rows": inserted, "rejections": len(batch.rejects), "archive_status": file_result.status, "manifest_path": str(file_result.manifest_path)}, sort_keys=True))
    return 0 if status in COMPLETE_STATUSES else 1


if __name__ == "__main__":
    exit_code = main()
    if exit_code:
        raise RuntimeError(f"NEMWEB Delta landing failed with status code {exit_code}")
