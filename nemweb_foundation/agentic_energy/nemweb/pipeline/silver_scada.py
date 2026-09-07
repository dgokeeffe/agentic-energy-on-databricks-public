"""Correction-aware per-DUID SCADA actual MW; negative load/storage values survive."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.silver_common import latest_correction


@dp.materialized_view(
    name="silver_nem_dispatch_unit_scada",
    comment="Latest DISPATCH UNIT_SCADA actual generation MW per interval-ending five-minute AEST interval and DUID. Negative battery/load MW is valid; this is not dispatch target or availability.",
    table_properties={"quality": "silver", "grain": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_scada_key", "interval_end IS NOT NULL AND duid IS NOT NULL")
def silver_nem_dispatch_unit_scada():
    return latest_correction(
        spark.read.table("bronze_nem_dispatch_unit_scada"),
        ("interval_end", "duid"),
    ).select(
        "interval_end", "duid", "actual_generation_mw", "source_last_changed",
        "report_version", "source_publication_at", "ingested_at",
        F.col("ingested_at").alias("silver_published_at"),
    )
