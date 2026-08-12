"""Publish a promoted run's layers as governed Unity Catalog Delta tables.

The pipeline's durable evidence is the immutable JSONL run directory under the
landing Volume. That is the right contract for reconciliation, but a Volume of
JSONL is not consumable by the business: it cannot be queried, granted, or
described. This module registers each run's layers as governed Delta tables so
Bronze/Silver/Quarantine/Gold are queryable in Unity Catalog.

Three properties matter more than convenience here:

1. **Publication never mutates the run evidence.** It reads the promoted output
   directory and only writes to Unity Catalog. A publication failure therefore
   cannot corrupt the manifest a run is reconciled against.

2. **Republishing a run is idempotent.** Every table is keyed by ``run_id`` and
   a republish deletes that run's rows before appending. A retried job task must
   not double-count Bronze rows, because the manifest counts are the acceptance
   evidence.

3. **Table shape is declared, not inferred.** Schemas are explicit DDL and
   created with ``CREATE TABLE IF NOT EXISTS``. Inferring a schema from whatever
   the first run happened to contain lets a nullable measure silently land as
   the wrong type, or a later run widen a column and break a downstream metric
   view. Sources stay data, not code: one Silver table carries nullable market
   and weather measures rather than one table per source.

Nested lineage and freshness structs are flattened into stable typed columns.
Business consumers should not have to dig through structs, and flattening keeps
the tables compatible with metric views. The raw record is preserved verbatim as
JSON text in Bronze, so nothing is lost.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

UTC = timezone.utc

# Unity Catalog identifiers are interpolated into DDL, so they are validated
# against a strict allowlist rather than quoted. A rejected name fails the run
# instead of producing a surprising table somewhere else.
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,254}")

BRONZE_TABLE = "bronze_records"
SILVER_TABLE = "silver_observations"
QUARANTINE_TABLE = "quarantine_rejections"
GOLD_TABLE = "gold_market_weather"
MANIFEST_TABLE = "run_manifest"

# Ordered column contracts. Order is part of the contract: the writer builds
# positional rows from it, so a reordering is a visible change here.
TABLE_SCHEMAS: dict[str, tuple[tuple[str, str], ...]] = {
    BRONZE_TABLE: (
        ("run_id", "STRING"),
        ("metadata_snapshot_id", "STRING"),
        ("mode", "STRING"),
        ("source_id", "STRING"),
        ("source_file", "STRING"),
        ("source_row_number", "BIGINT"),
        ("raw_line", "STRING"),
        ("raw_record_json", "STRING"),
        ("ingested_at", "TIMESTAMP"),
    ),
    SILVER_TABLE: (
        ("run_id", "STRING"),
        ("source_id", "STRING"),
        ("provider", "STRING"),
        ("dataset", "STRING"),
        ("region", "STRING"),
        ("interval_utc", "TIMESTAMP"),
        ("demand_mw", "DOUBLE"),
        ("price_per_mwh", "DOUBLE"),
        ("temperature_c", "DOUBLE"),
        ("ingestion_sequence", "BIGINT"),
        ("source_version", "STRING"),
        ("licensing_provenance", "STRING"),
        ("source_file", "STRING"),
        ("source_row_number", "BIGINT"),
    ),
    QUARANTINE_TABLE: (
        ("run_id", "STRING"),
        ("source_id", "STRING"),
        ("source_file", "STRING"),
        ("source_row_number", "BIGINT"),
        ("reason_codes", "ARRAY<STRING>"),
        ("reason_codes_text", "STRING"),
        ("rejected_at", "TIMESTAMP"),
        ("raw_record_json", "STRING"),
    ),
    GOLD_TABLE: (
        ("run_id", "STRING"),
        ("region", "STRING"),
        ("interval_utc", "TIMESTAMP"),
        ("demand_mw", "DOUBLE"),
        ("price_per_mwh", "DOUBLE"),
        ("temperature_c", "DOUBLE"),
        ("pipeline_ingested_at", "TIMESTAMP"),
        ("latest_event_utc", "TIMESTAMP"),
        ("market_source_id", "STRING"),
        ("market_provider", "STRING"),
        ("market_licensing_provenance", "STRING"),
        ("weather_source_id", "STRING"),
    ),
    MANIFEST_TABLE: (
        ("run_id", "STRING"),
        ("metadata_snapshot_id", "STRING"),
        ("mode", "STRING"),
        ("metadata_sha256", "STRING"),
        ("pipeline_ingested_at", "TIMESTAMP"),
        ("source_ids", "ARRAY<STRING>"),
        ("bronze_count", "BIGINT"),
        ("silver_count", "BIGINT"),
        ("quarantine_count", "BIGINT"),
        ("gold_count", "BIGINT"),
    ),
}

TABLE_COMMENTS: dict[str, str] = {
    BRONZE_TABLE: "Immutable raw source records with retrieval lineage, one row per acquired record.",
    SILVER_TABLE: "Typed, timezone-normalized, deduplicated observations. Market and weather measures are nullable by source.",
    QUARANTINE_TABLE: "Rejected source records with reason codes, reconciled against Bronze counts.",
    GOLD_TABLE: "Business-facing market and weather projection, one row per region and dispatch interval.",
    MANIFEST_TABLE: "Per-run reconciliation evidence: layer counts, metadata hash, mode, and freshness.",
}

# Silver measure columns are absent, not null, for a source that does not carry
# them; the projection below distinguishes the two deliberately.
_SILVER_MEASURES = ("demand_mw", "price_per_mwh", "temperature_c")


class TableWriter(Protocol):
    """Minimal surface publication needs from the execution engine.

    Kept this narrow so the table contracts can be tested offline without a
    Spark session. The wheel must stay importable and unit-testable on a laptop
    with no Databricks runtime.
    """

    def execute(self, statement: str) -> None:
        ...

    def append(self, table: str, schema: tuple[tuple[str, str], ...], rows: list[tuple]) -> None:
        ...


class SparkTableWriter:
    """`TableWriter` backed by an active Spark session (serverless job runtime)."""

    def __init__(self, spark) -> None:
        self._spark = spark

    def execute(self, statement: str) -> None:
        self._spark.sql(statement)

    def append(self, table: str, schema: tuple[tuple[str, str], ...], rows: list[tuple]) -> None:
        if not rows:
            return
        ddl = ", ".join(f"{name} {sql_type}" for name, sql_type in schema)
        frame = self._spark.createDataFrame(rows, schema=ddl)
        # Append by name against the pre-created table so publication can never
        # silently redefine a governed schema.
        frame.write.mode("append").saveAsTable(table)


def _validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"INVALID_{label}")
    return value


def _validate_run_id(run_id: str) -> str:
    # Interpolated into DELETE predicates, so it is allowlisted the same way as
    # identifiers rather than escaped.
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", run_id):
        raise ValueError("INVALID_RUN_ID")
    return run_id


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _json_text(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _float(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _row(schema: tuple[tuple[str, str], ...], values: dict) -> tuple:
    return tuple(values.get(name) for name, _ in schema)


def _bronze_rows(output: Path, run_id: str, manifest: dict) -> list[tuple]:
    schema = TABLE_SCHEMAS[BRONZE_TABLE]
    rows = []
    for path in sorted((output / "bronze").glob("*.jsonl")):
        for record in _read_jsonl(path):
            rows.append(_row(schema, {
                "run_id": run_id,
                "metadata_snapshot_id": manifest.get("metadata_snapshot_id"),
                "mode": manifest.get("mode"),
                "source_id": record.get("source_id"),
                "source_file": record.get("source_file"),
                "source_row_number": record.get("source_row_number"),
                "raw_line": record.get("raw_line"),
                "raw_record_json": _json_text(record.get("raw_record")),
                "ingested_at": _timestamp(record.get("_ingested_at")),
            }))
    return rows


def _silver_rows(output: Path, run_id: str) -> list[tuple]:
    schema = TABLE_SCHEMAS[SILVER_TABLE]
    rows = []
    for path in sorted((output / "silver").glob("*.jsonl")):
        for record in _read_jsonl(path):
            lineage = record.get("lineage") or {}
            values = {
                "run_id": run_id,
                "source_id": record.get("source_id"),
                "provider": lineage.get("provider"),
                "dataset": lineage.get("dataset"),
                "region": record.get("region"),
                "interval_utc": _timestamp(record.get("interval_utc")),
                "ingestion_sequence": record.get("ingestion_sequence"),
                "source_version": lineage.get("source_version"),
                "licensing_provenance": lineage.get("licensing_provenance"),
                "source_file": record.get("source_file"),
                "source_row_number": record.get("source_row_number"),
            }
            for measure in _SILVER_MEASURES:
                values[measure] = _float(record.get(measure))
            rows.append(_row(schema, values))
    return rows


def _quarantine_rows(output: Path, run_id: str) -> list[tuple]:
    schema = TABLE_SCHEMAS[QUARANTINE_TABLE]
    rows = []
    for record in _read_jsonl(output / "quarantine" / "rejected.jsonl"):
        reason_codes = [str(code) for code in record.get("reason_codes") or []]
        rows.append(_row(schema, {
            "run_id": run_id,
            "source_id": record.get("source_id"),
            "source_file": record.get("source_file"),
            "source_row_number": record.get("source_row_number"),
            "reason_codes": reason_codes,
            # Arrays are awkward in BI and natural-language surfaces; the text
            # projection keeps quarantine triage usable there.
            "reason_codes_text": ",".join(reason_codes),
            "rejected_at": _timestamp(record.get("rejected_at")),
            "raw_record_json": _json_text(record.get("raw_record")),
        }))
    return rows


def _gold_rows(output: Path, run_id: str) -> list[tuple]:
    schema = TABLE_SCHEMAS[GOLD_TABLE]
    rows = []
    for record in _read_jsonl(output / "gold" / "market_weather.jsonl"):
        lineage = record.get("lineage") or {}
        market = lineage.get("market") or {}
        weather = lineage.get("weather") or {}
        freshness = record.get("freshness") or {}
        rows.append(_row(schema, {
            "run_id": run_id,
            "region": record.get("region"),
            "interval_utc": _timestamp(record.get("interval_utc")),
            "demand_mw": _float(record.get("demand_mw")),
            "price_per_mwh": _float(record.get("price_per_mwh")),
            "temperature_c": _float(record.get("temperature_c")),
            "pipeline_ingested_at": _timestamp(freshness.get("pipeline_ingested_at")),
            "latest_event_utc": _timestamp(freshness.get("latest_event_utc")),
            "market_source_id": market.get("source_id"),
            "market_provider": market.get("provider"),
            "market_licensing_provenance": market.get("licensing_provenance"),
            # Null weather is a real signal: the interval had no matching
            # observation, so it must stay distinguishable downstream.
            "weather_source_id": weather.get("source_id"),
        }))
    return rows


def _manifest_rows(run_id: str, manifest: dict) -> list[tuple]:
    layers = manifest.get("layers") or {}
    return [_row(TABLE_SCHEMAS[MANIFEST_TABLE], {
        "run_id": run_id,
        "metadata_snapshot_id": manifest.get("metadata_snapshot_id"),
        "mode": manifest.get("mode"),
        "metadata_sha256": manifest.get("metadata_sha256"),
        "pipeline_ingested_at": _timestamp(manifest.get("pipeline_ingested_at")),
        "source_ids": list(manifest.get("source_ids") or []),
        "bronze_count": layers.get("bronze"),
        "silver_count": layers.get("silver"),
        "quarantine_count": layers.get("quarantine"),
        "gold_count": layers.get("gold"),
    })]


def create_table_statements(catalog: str, schema: str) -> list[str]:
    """Return the idempotent DDL that governs the published tables."""
    _validate_identifier(catalog, "CATALOG")
    _validate_identifier(schema, "SCHEMA")
    statements = []
    for table, columns in TABLE_SCHEMAS.items():
        column_ddl = ",\n  ".join(f"{name} {sql_type}" for name, sql_type in columns)
        statements.append(
            f"CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table} (\n  {column_ddl}\n) "
            f"USING DELTA COMMENT '{TABLE_COMMENTS[table]}'"
        )
    return statements


def publish_run(
    output_dir: str | Path,
    *,
    catalog: str,
    schema: str,
    run_id: str,
    writer: TableWriter,
) -> dict[str, int]:
    """Register a promoted run directory as governed Delta tables.

    Returns per-table published row counts. Reconciled against the run manifest
    before any table is touched, so a partially written or mismatched run
    directory fails before it can publish misleading numbers to the business.
    """
    _validate_identifier(catalog, "CATALOG")
    _validate_identifier(schema, "SCHEMA")
    _validate_run_id(run_id)
    output = Path(output_dir)
    manifest_path = output / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("RUN_MANIFEST_NOT_FOUND")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest_run_id = manifest.get("run_id")
    if manifest_run_id is not None and manifest_run_id != run_id:
        # Publishing run A's evidence under run B's key would make the manifest
        # and the tables disagree about what was ingested.
        raise ValueError("RUN_ID_DOES_NOT_MATCH_MANIFEST")

    payloads = {
        BRONZE_TABLE: _bronze_rows(output, run_id, manifest),
        SILVER_TABLE: _silver_rows(output, run_id),
        QUARANTINE_TABLE: _quarantine_rows(output, run_id),
        GOLD_TABLE: _gold_rows(output, run_id),
        MANIFEST_TABLE: _manifest_rows(run_id, manifest),
    }

    layers = manifest.get("layers") or {}
    for table, layer in (
        (BRONZE_TABLE, "bronze"),
        (SILVER_TABLE, "silver"),
        (QUARANTINE_TABLE, "quarantine"),
        (GOLD_TABLE, "gold"),
    ):
        expected = layers.get(layer)
        if expected is not None and expected != len(payloads[table]):
            raise RuntimeError(f"PUBLISH_RECONCILIATION_FAILED:{layer}")

    for statement in create_table_statements(catalog, schema):
        writer.execute(statement)

    published: dict[str, int] = {}
    for table, rows in payloads.items():
        qualified = f"{catalog}.{schema}.{table}"
        # Delete-then-append keyed by run_id makes a retried task idempotent.
        # Delta has no multi-table transaction, so each table is individually
        # consistent and the manifest row is written last: if publication dies
        # midway, the run is absent from run_manifest and is not treated as
        # published.
        writer.execute(f"DELETE FROM {qualified} WHERE run_id = '{run_id}'")
        writer.append(qualified, TABLE_SCHEMAS[table], rows)
        published[table] = len(rows)
    return published


def resolve_spark_writer() -> SparkTableWriter:
    """Build a writer from the ambient Spark session.

    Imported lazily so the wheel stays importable, testable, and runnable in
    fixture mode on a machine with no PySpark installed.
    """
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:  # pragma: no cover - exercised only off-cluster
        raise RuntimeError("UC_PUBLICATION_REQUIRES_SPARK") from exc
    spark = SparkSession.getActiveSession() or SparkSession.builder.getOrCreate()
    return SparkTableWriter(spark)
