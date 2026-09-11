"""SCADA-backed five-minute unit/facility output without fabricated availability."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_unit_dispatch_5min",
    comment="Per-DUID actual SCADA generation (MW) at interval-ending five-minute grain, enriched from the monthly NEMWEB facility dimension. This is actual output, never a dispatch target; AEMO Current does not publish five-minute unit availability.",
    table_properties={"quality": "gold", "grain": "five_minutes", "availability": "not_published_in_current"},
    cluster_by=["duid", "interval_end"],
)
@dp.expect_or_drop(
    "valid_gold_unit_dispatch_key",
    "interval_end IS NOT NULL AND duid IS NOT NULL AND actual_generation_mw IS NOT NULL",
)
@dp.expect_or_fail(
    "known_dimension_match_status",
    "dimension_match_status IN ('REGION_AND_FUEL', 'REGION_ONLY', 'FUEL_ONLY', 'UNMATCHED')",
)
def gold_nem_unit_dispatch_5min():
    scada = spark.read.table("silver_nem_dispatch_unit_scada").alias("s")
    facilities = spark.read.table("silver_nem_facility_dimension").alias("f")
    return scada.join(facilities, "duid", "left").select(
        F.col("s.interval_end").alias("interval_end"),
        F.col("s.interval_end").alias("source_interval_watermark"),
        F.col("duid"),
        F.col("s.actual_generation_mw"),
        F.coalesce(F.col("f.region_id"), F.lit("UNKNOWN")).alias("region_id"),
        F.coalesce(F.col("f.fuel_type"), F.lit("UNKNOWN")).alias("fuel_type"),
        F.col("f.station_id"),
        F.col("f.genset_id"),
        F.col("f.dispatch_type"),
        F.col("f.schedule_type"),
        F.col("f.registered_capacity_mw"),
        F.col("f.maximum_capacity_mw"),
        F.coalesce(F.col("f.dimension_match_status"), F.lit("UNMATCHED")).alias("dimension_match_status"),
        F.col("s.source_publication_at"),
        F.col("s.silver_published_at"),
        F.current_timestamp().alias("gold_published_at"),
    )
