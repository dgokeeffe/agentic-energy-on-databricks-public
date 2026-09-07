"""Shared correction and intervention windows for NEMWEB Silver datasets."""

from pyspark.sql import functions as F
from pyspark.sql.window import Window


def latest_correction(frame, natural_key, *, source_revision=None):
    """Select the latest source correction without deleting Bronze history.

    ``source_revision`` names a report-specific VERSIONNO/SETTLEMENTRUNNO
    column where the section does not carry RUNNO. Section version always
    precedes that revision; publication and ingestion order are deterministic
    tie-breakers.
    """

    report_order = [F.col("report_version").cast("long").desc_nulls_last()]
    if source_revision is not None:
        report_order.append(F.col(source_revision).cast("long").desc_nulls_last())
    order = (
        *report_order,
        F.col("run_no").desc_nulls_last(),
        F.col("source_publication_at").desc_nulls_last(),
        F.col("landed_at").desc_nulls_last(),
        F.col("ingestion_run_id").desc_nulls_last(),
        F.col("ingestion_sequence").desc_nulls_last(),
    )
    window = Window.partitionBy(*natural_key).orderBy(*order)
    return frame.withColumn("_correction_rank", F.row_number().over(window)).where(
        F.col("_correction_rank") == 1
    ).drop("_correction_rank")


def with_effective_run(frame, key_without_intervention):
    """Retain both runs and mark the highest available intervention flag."""

    window = Window.partitionBy(*key_without_intervention)
    return frame.withColumn(
        "is_effective_run",
        F.coalesce(
            F.col("intervention") == F.max("intervention").over(window),
            F.lit(False),
        ),
    )
