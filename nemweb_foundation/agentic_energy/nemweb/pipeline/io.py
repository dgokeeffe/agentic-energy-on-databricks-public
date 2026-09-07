"""Supported Auto Loader input and Bronze provenance helpers.

Modified from the reference pipeline's streaming utility concepts; see
``NOTICE.md``.  The implementation reads deterministic parsed JSONL plus the
lander's immutable manifests.  It does not perform HTTP requests, start a
stream, configure checkpoints, or write arbitrary files.
"""

from __future__ import annotations

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

from agentic_energy.nemweb.pipeline.config import PipelineConfig

# Required on every critical Bronze table.  ``source_values`` and
# ``_unknown_columns`` are retained in addition to this common contract so an
# observed source addition cannot disappear before schema review.
PROVENANCE_COLUMNS = (
    "source_mode",
    "source_url_path",
    "source_archive",
    "source_archive_sha256",
    "source_csv_member",
    "report_family",
    "section_name",
    "report_version",
    "run_no",
    "source_publication_at",
    "source_publication_basis",
    "interval_end",
    "landed_at",
    "ingested_at",
    "ingestion_run_id",
    "ingestion_sequence",
    "_rescued_data",
)

FIVE_MINUTE_BOUNDARY_SQL = (
    "pmod(minute(interval_end), 5) = 0 AND second(interval_end) = 0"
)

COMMON_VALIDITY_SQL = " AND ".join(
    (
        "source_mode IN ('live', 'snapshot')",
        "source_url_path IS NOT NULL",
        "source_archive IS NOT NULL",
        "source_archive_sha256 RLIKE '^[0-9a-f]{64}$'",
        "source_csv_member IS NOT NULL",
        "report_family IS NOT NULL",
        "section_name IS NOT NULL",
        "report_version IS NOT NULL",
        "source_publication_at IS NOT NULL",
        "source_publication_basis IN ('listing_or_http', 'retrieval_fallback')",
        "landed_at IS NOT NULL",
        "ingested_at IS NOT NULL",
        "ingestion_run_id IS NOT NULL",
        "ingestion_sequence IS NOT NULL",
        "_rescued_data IS NULL",
    )
)

_RAW_RECORD_SCHEMA = T.StructType(
    (
        T.StructField("report_family", T.StringType(), False),
        T.StructField("section_group", T.StringType(), False),
        T.StructField("section_name", T.StringType(), False),
        T.StructField("report_version", T.StringType(), False),
        T.StructField("csv_member", T.StringType(), False),
        T.StructField("row_number", T.LongType(), False),
        T.StructField("values", T.MapType(T.StringType(), T.StringType()), True),
        T.StructField("unknown_columns", T.ArrayType(T.StringType()), True),
        T.StructField("_rescued_data", T.StringType(), True),
    )
)

_MANIFEST_SCHEMA = T.StructType(
    (
        T.StructField("run_id", T.StringType(), False),
        T.StructField("source_mode", T.StringType(), False),
        T.StructField("landed_at", T.StringType(), False),
        T.StructField(
            "archives",
            T.ArrayType(
                T.StructType(
                    (
                        T.StructField("input_sequence", T.LongType(), False),
                        T.StructField("report_family", T.StringType(), False),
                        T.StructField("publication", T.StringType(), True),
                        T.StructField("source_publication_at", T.StringType(), True),
                        T.StructField("source_publication_basis", T.StringType(), True),
                        T.StructField("source_filename", T.StringType(), False),
                        T.StructField("source_url_path", T.StringType(), False),
                        T.StructField("source_archive_sha256", T.StringType(), False),
                    )
                )
            ),
            False,
        ),
    )
)


def _manifest_index(spark_session, config: PipelineConfig):
    """Return one immutable provenance row per exact landed archive.

    A repeated checksum may appear in later manifests after a harmless source
    re-listing.  Choosing the first landing prevents an exact duplicate file
    from multiplying Bronze rows, while changed correction archives retain
    their distinct checksum and remain append-only.
    """

    manifests = spark_session.read.schema(_MANIFEST_SCHEMA).json(
        f"{config.landing_path}/manifests/*.json"
    )
    archives = (
        manifests.select(
            "run_id",
            "source_mode",
            "landed_at",
            F.explode("archives").alias("archive"),
        )
        .select(
            F.col("archive.report_family").alias("manifest_report_family"),
            F.col("archive.publication").alias("source_interval_token"),
            F.col("archive.source_publication_at").alias("source_publication_timestamp"),
            F.col("archive.source_publication_basis").alias("source_publication_basis"),
            F.col("archive.source_filename").alias("source_archive"),
            F.col("archive.source_url_path").alias("source_url_path"),
            F.col("archive.source_archive_sha256").alias(
                "manifest_archive_sha256"
            ),
            F.col("archive.input_sequence").alias("archive_sequence"),
            F.col("run_id").alias("ingestion_run_id"),
            F.col("source_mode").alias("manifest_source_mode"),
            F.to_timestamp("landed_at").alias("landed_at"),
        )
    )
    first_landing = Window.partitionBy(
        "manifest_report_family", "manifest_archive_sha256"
    ).orderBy(
        F.col("landed_at").asc(),
        F.col("ingestion_run_id").asc(),
        F.col("archive_sequence").asc(),
    )
    return (
        archives.withColumn("_landing_rank", F.row_number().over(first_landing))
        .where(F.col("_landing_rank") == 1)
        .drop("_landing_rank")
    )


def read_parsed_records(spark_session):
    """Read the selected mode sibling and attach immutable provenance.

    ``PipelineConfig.landing_path`` is already resolved to
    ``<volume-parent>/<source_mode>``. Keeping every manifest and parsed read
    relative to that one value prevents snapshot/live cross-reading and keeps
    Auto Loader aligned with the lander's mode-scoped write root.
    """

    config = PipelineConfig.from_spark(spark_session)
    parsed = (
        spark_session.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("cloudFiles.includeExistingFiles", "true")
        .option("recursiveFileLookup", "true")
        .option("pathGlobFilter", "*.jsonl")
        .schema(_RAW_RECORD_SCHEMA)
        .load(f"{config.landing_path}/parsed")
        .withColumn("_source_file_path", F.col("_metadata.file_path"))
        .withColumn(
            "_path_archive_sha256",
            F.regexp_extract(
                "_source_file_path", r"/parsed/[^/]+/([0-9a-f]{64})/", 1
            ),
        )
    )
    manifests = _manifest_index(spark_session, config)
    joined = parsed.join(
        F.broadcast(manifests),
        (parsed.report_family == manifests.manifest_report_family)
        & (parsed._path_archive_sha256 == manifests.manifest_archive_sha256),
        "left",
    )
    return joined.select(
        F.coalesce("manifest_source_mode", F.lit(config.source_mode)).alias(
            "source_mode"
        ),
        "source_url_path",
        "source_archive",
        F.col("_path_archive_sha256").alias("source_archive_sha256"),
        F.col("csv_member").alias("source_csv_member"),
        parsed.report_family,
        "section_group",
        parsed.section_name,
        parsed.report_version,
        F.col("values").getItem("RUNNO").cast("long").alias("run_no"),
        F.to_timestamp("source_publication_timestamp").alias("source_publication_at"),
        "source_publication_basis",
        F.to_timestamp(F.col("values").getItem("SETTLEMENTDATE")).alias(
            "interval_end"
        ),
        "landed_at",
        F.current_timestamp().alias("ingested_at"),
        "ingestion_run_id",
        # landed_at is globally ordered across runs; row number is the stable
        # final tie-break within an archive. Silver also orders by landed_at.
        F.col("row_number").alias("ingestion_sequence"),
        parsed._rescued_data,
        F.col("unknown_columns").alias("_unknown_columns"),
        F.col("values").alias("source_values"),
        F.col("row_number").alias("source_row_number"),
    )


# NOTE: the _nemweb_parsed_records temporary view is deliberately NOT declared
# here. This module is imported by every Bronze dataset module, and a
# pyspark.pipelines decorator registers its dataset globally on evaluation, so
# declaring it in an imported helper registered it once per importer and failed
# the update with "Found duplicate dataset `_nemweb_parsed_records`" (observed on
# pipeline update 19d20ebe, 2026-09-02). It is declared exactly once in the
# dedicated dataset module parsed_records.py, which is the only file listed as a
# pipeline library for it.


def section_stream(
    spark_session,
    *,
    report_family: str,
    section_group: str,
    section_name: str,
    columns: tuple[tuple[str, str, str], ...],
):
    """Select one section and project typed business columns without data loss."""

    frame = spark_session.readStream.table("_nemweb_parsed_records").where(
        (F.col("report_family") == report_family)
        & (F.col("section_group") == section_group)
        & (F.col("section_name") == section_name)
    )
    projected = [
        F.col("source_values").getItem(source).cast(data_type).alias(target)
        for source, target, data_type in columns
    ]
    return frame.select(
        *projected,
        *PROVENANCE_COLUMNS,
        "section_group",
        "source_values",
        "_unknown_columns",
        "source_row_number",
    )


def quarantine(frame, validity_sql: str, reason: str):
    """Return the exact complement of a Bronze validity expectation."""

    # SQL ``NOT NULL`` is NULL and would otherwise lose malformed rows from
    # both branches. Coalescing the predicate makes quarantine the exact
    # complement of expectation success.
    return frame.where(f"NOT COALESCE(({validity_sql}), FALSE)").withColumn(
        "quarantine_reason", F.lit(reason)
    )
