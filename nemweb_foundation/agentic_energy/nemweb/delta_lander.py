"""Append-only Delta landing for the eight app-critical NEMWEB subjects.

Pure preparation is independent of Spark and is covered locally.  Workspace
writes use insert-only Delta MERGE statements; only run metadata may transition
from STARTED to a terminal state. Source versions and run associations are never
updated or deleted.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence

from .lander import ArchiveInput
from .parser import canonical_record_json, parse_zip_bytes
from .source_registry import APP_CRITICAL_SUBJECTS, SourceSubject, get_subject_by_section, subjects_for_scope

COMPLETE_STATUSES = frozenset({"COMPLETE_NEW_DATA", "COMPLETE_NO_NEW_SOURCE"})
TERMINAL_STATUSES = COMPLETE_STATUSES | {"PARTIAL", "FAILED"}


@dataclass(frozen=True)
class LandingProvenance:
    source_filename: str
    source_url_path: str
    archive_sha256: str
    csv_member: str
    source_row_number: int
    source_publication_at: str | None
    retrieved_at: str
    landed_at: str


@dataclass(frozen=True)
class LandingRecord:
    subject_key: str
    source_record_id: str
    source_version_id: str
    landing_run_id: str
    source_mode: str
    typed_values: Mapping[str, object]
    unexpected_values: Mapping[str, str]
    provenance: LandingProvenance


@dataclass(frozen=True)
class LandingFile:
    report_family: str
    source_filename: str
    archive_sha256: str
    source_publication_at: str | None
    retrieved_at: str
    row_count: int


@dataclass(frozen=True)
class LandingReject:
    report_family: str
    archive_sha256: str
    code: str
    message: str
    csv_member: str
    row_number: int


@dataclass(frozen=True)
class LandingSubjectResult:
    subject_key: str
    row_count: int
    reject_count: int
    present: bool


@dataclass(frozen=True)
class LandingBatch:
    run_id: str
    source_mode: str
    scope: str
    records_by_subject: Mapping[str, tuple[LandingRecord, ...]]
    files: tuple[LandingFile, ...]
    rejects: tuple[LandingReject, ...]
    subject_results: tuple[LandingSubjectResult, ...]
    status: str
    landed_at: str


def _digest(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def prepare_landing_batch(archives: Sequence[ArchiveInput], *, run_id: str, source_mode: str, scope: str, landed_at: str | None = None) -> LandingBatch:
    landed = landed_at or datetime.now(timezone.utc).isoformat()
    required = subjects_for_scope(scope)
    records: dict[str, list[LandingRecord]] = {s.key: [] for s in required}
    rejects: list[LandingReject] = []
    files: list[LandingFile] = []
    for archive in archives:
        checksum = hashlib.sha256(archive.data).hexdigest()
        parsed = parse_zip_bytes(archive.data, archive.report_family)
        accepted = 0
        for issue in parsed.issues:
            if issue.severity == "error":
                rejects.append(LandingReject(archive.report_family, checksum, issue.code, issue.message, issue.csv_member, issue.row_number))
        for row in parsed.records:
            subject = get_subject_by_section(archive.report_family, *row.section_key)
            if subject is None or subject.required_scope != scope:
                continue
            field_names = {field.source_name for field in subject.fields}
            typed = {field.source_name: row.values.get(field.source_name) for field in subject.fields}
            unexpected = {key: str(value) for key, value in row.values.items() if key not in field_names and value is not None}
            identity = {
                "source_mode": source_mode, "report_family": archive.report_family,
                "section": row.section_key, "archive_sha256": checksum,
                "csv_member": row.csv_member, "row_number": row.row_number,
                "values": typed,
            }
            version = {"source_mode": source_mode, "report_family": archive.report_family,
                       "filename": archive.filename, "publication": archive.publication,
                       "archive_sha256": checksum}
            provenance = LandingProvenance(
                archive.filename, archive.source_url_path, checksum,
                row.csv_member, row.row_number, archive.source_publication_at,
                archive.retrieved_at, landed,
            )
            records[subject.key].append(LandingRecord(
                subject.key, _digest(identity), _digest(version), run_id,
                source_mode, typed, unexpected, provenance,
            ))
            accepted += 1
        files.append(LandingFile(archive.report_family, archive.filename, checksum,
                                 archive.source_publication_at, archive.retrieved_at, accepted))
    subject_results = tuple(LandingSubjectResult(
        subject.key, len(records[subject.key]),
        sum(1 for r in rejects if r.report_family == subject.report_family),
        bool(records[subject.key]),
    ) for subject in required)
    missing = [result.subject_key for result in subject_results if not result.present]
    status = "COMPLETE_NEW_DATA" if not missing and not rejects else ("PARTIAL" if records and any(records.values()) else "FAILED")
    return LandingBatch(run_id, source_mode, scope,
                        {key: tuple(value) for key, value in records.items()},
                        tuple(files), tuple(rejects), subject_results, status, landed)


class LandingBackend(Protocol):
    def insert_source(self, table: str, records: Sequence[LandingRecord]) -> int: ...
    def insert_run_records(self, batch: LandingBatch) -> int: ...
    def append_metadata(self, table: str, rows: Sequence[Mapping[str, object]]) -> None: ...


def write_landing_batch_to_backend(backend: LandingBackend, batch: LandingBatch) -> tuple[str, int]:
    inserted = 0
    backend.append_metadata("landing_nem_runs", ({"run_id": batch.run_id, "source_mode": batch.source_mode, "scope": batch.scope, "status": "STARTED", "event_at": batch.landed_at},))
    for subject in subjects_for_scope(batch.scope):
        inserted += backend.insert_source(subject.landing_table, batch.records_by_subject.get(subject.key, ()))
    backend.insert_run_records(batch)
    backend.append_metadata("landing_nem_files", tuple(asdict(item) | {"run_id": batch.run_id} for item in batch.files))
    backend.append_metadata("landing_nem_rejections", tuple(asdict(item) | {"run_id": batch.run_id} for item in batch.rejects))
    backend.append_metadata("landing_nem_run_subjects", tuple(asdict(item) | {"run_id": batch.run_id, "status": batch.status} for item in batch.subject_results))
    final = batch.status
    if final in COMPLETE_STATUSES and inserted == 0:
        final = "COMPLETE_NO_NEW_SOURCE"
    backend.append_metadata("landing_nem_run_events", ({"run_id": batch.run_id, "status": final, "event_at": datetime.now(timezone.utc).isoformat()},))
    return final, inserted


def _qualified(catalog: str, schema: str, table: str) -> str:
    for value in (catalog, schema, table):
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("unsafe Unity Catalog identifier")
    return f"`{catalog}`.`{schema}`.`{table}`"


def ensure_landing_tables(spark, catalog: str, schema: str) -> None:
    common = "source_record_id STRING, source_version_id STRING, source_mode STRING, subject_key STRING, typed_values MAP<STRING,STRING>, unexpected_values MAP<STRING,STRING>, source_filename STRING, source_url_path STRING, source_archive_sha256 STRING, source_csv_member STRING, source_row_number BIGINT, source_publication_at TIMESTAMP, retrieved_at TIMESTAMP, landed_at TIMESTAMP"
    for subject in APP_CRITICAL_SUBJECTS:
        spark.sql(f"CREATE TABLE IF NOT EXISTS {_qualified(catalog, schema, subject.landing_table)} ({common}) USING DELTA TBLPROPERTIES ('delta.appendOnly'='true')")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {_qualified(catalog, schema, 'landing_nem_run_records')} (run_id STRING, subject_key STRING, source_record_id STRING, source_version_id STRING, associated_at TIMESTAMP) USING DELTA TBLPROPERTIES ('delta.appendOnly'='true')")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {_qualified(catalog, schema, 'landing_nem_run_events')} (run_id STRING, status STRING, event_at TIMESTAMP) USING DELTA TBLPROPERTIES ('delta.appendOnly'='true')")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {_qualified(catalog, schema, 'landing_nem_runs')} (run_id STRING, source_mode STRING, scope STRING, status STRING, landed_at TIMESTAMP, completed_at TIMESTAMP) USING DELTA")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {_qualified(catalog, schema, 'landing_nem_run_subjects')} (run_id STRING, subject_key STRING, row_count BIGINT, reject_count BIGINT, present BOOLEAN, status STRING) USING DELTA TBLPROPERTIES ('delta.appendOnly'='true')")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {_qualified(catalog, schema, 'landing_nem_files')} (run_id STRING, report_family STRING, source_filename STRING, archive_sha256 STRING, source_publication_at TIMESTAMP, retrieved_at TIMESTAMP, row_count BIGINT) USING DELTA TBLPROPERTIES ('delta.appendOnly'='true')")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {_qualified(catalog, schema, 'landing_nem_rejections')} (run_id STRING, report_family STRING, archive_sha256 STRING, code STRING, message STRING, csv_member STRING, row_number BIGINT) USING DELTA TBLPROPERTIES ('delta.appendOnly'='true')")


def successful_run_records(spark, subject: SourceSubject, catalog: str, schema: str):
    associations = spark.readStream.table(_qualified(catalog, schema, "landing_nem_run_records"))
    runs = spark.read.table(_qualified(catalog, schema, "landing_nem_runs")).where("status IN ('COMPLETE_NEW_DATA','COMPLETE_NO_NEW_SOURCE')")
    # Associations are the incremental driver. Immutable source rows and the
    # terminal-run snapshot are static joins observed when each triggered update
    # starts, avoiding an unbounded stream-stream join.
    source = spark.read.table(_qualified(catalog, schema, subject.landing_table))
    return (associations.where(f"subject_key = '{subject.key}'")
            .join(runs.select("run_id"), "run_id", "inner")
            .join(source, ["source_record_id", "source_version_id"], "inner")
            .dropDuplicates(["source_record_id"]))
