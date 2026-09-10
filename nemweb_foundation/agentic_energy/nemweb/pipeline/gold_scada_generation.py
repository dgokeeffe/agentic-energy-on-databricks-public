"""Five-minute SCADA generation aggregated by governed region and fuel.

Enrichment health is asserted per market interval, not per row. ``region_id`` and
``fuel_type`` are grouping keys here, so a row whose region is UNKNOWN is a
legitimate result: registered pseudo units carry a region without a fuel, and
AEMO does not supply a fuel for every DUID. A per-row expectation would therefore
reject valid data.

What is *not* legitimate is an interval in which nothing enriched at all. That is
the signature of an absent registration/context load rather than of genuinely
unknown metadata, and the previous count-only expectation could not see it: a
fully unmatched interval still reports ``facility_count > 0``, so 100% UNKNOWN
enrichment passed as healthy.

The interval-scoped counts below make that distinction explicit and mirror
``registration_enrichment_quality().validate()``: at least one known region and at
least one known fuel must be present, while individual UNKNOWN groups survive.
Rows are never dropped to obtain a pass.
"""

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window


@dp.materialized_view(
    name="gold_nem_scada_generation_5min",
    comment="Actual SCADA generation MW summed at interval-ending five-minute, region and AEMO fuel-source grain. Missing dimensions are retained as UNKNOWN rather than dropping DUIDs; negative load/storage values remain in the signed sum.",
    table_properties={"quality": "gold", "grain": "five_minutes", "source.timezone": "AEST"},
    cluster_by=["region_id", "fuel_type", "interval_end"],
)
@dp.expect_or_drop(
    "valid_gold_scada_generation_key",
    "interval_end IS NOT NULL AND region_id IS NOT NULL AND fuel_type IS NOT NULL",
)
@dp.expect_or_fail(
    "valid_scada_enrichment_counts",
    "facility_count > 0 AND partially_enriched_facility_count BETWEEN 0 AND facility_count",
)
@dp.expect_or_fail(
    # Fails an absent registration/context load without rejecting a legitimately
    # UNKNOWN group. Scoped to the interval so one stale interval cannot be
    # averaged away by healthy neighbours.
    "registration_context_present_per_interval",
    "interval_known_region_facility_count > 0 AND interval_known_fuel_facility_count > 0",
)
def gold_nem_scada_generation_5min():
    scada = spark.read.table("silver_nem_dispatch_unit_scada").alias("s")
    facilities = spark.read.table("silver_nem_facility_dimension").alias("f")
    enriched = scada.join(facilities, "duid", "left").select(
        F.col("s.interval_end").alias("interval_end"),
        F.coalesce(F.col("f.region_id"), F.lit("UNKNOWN")).alias("region_id"),
        F.coalesce(F.col("f.fuel_type"), F.lit("UNKNOWN")).alias("fuel_type"),
        F.col("duid"),
        F.col("s.actual_generation_mw"),
        F.coalesce(F.col("f.dimension_match_status"), F.lit("UNMATCHED")).alias("dimension_match_status"),
        F.col("s.source_publication_at"),
        F.col("s.silver_published_at"),
        # Carried from the dimension so a consumer can tell which registration
        # window priced these intervals. NULL for an unmatched DUID, which is
        # why the aggregate below takes the max over the group.
        F.col("f.registration_effective_at"),
    )
    grouped = enriched.groupBy("interval_end", "region_id", "fuel_type").agg(
        F.sum("actual_generation_mw").alias("actual_generation_mw"),
        F.countDistinct("duid").alias("facility_count"),
        F.sum(F.when(F.col("dimension_match_status") != "REGION_AND_FUEL", 1).otherwise(0)).alias("partially_enriched_facility_count"),
        F.sum(F.when(F.col("region_id") != "UNKNOWN", 1).otherwise(0)).alias("known_region_facility_count"),
        F.sum(F.when(F.col("fuel_type") != "UNKNOWN", 1).otherwise(0)).alias("known_fuel_facility_count"),
        F.sum(F.when(F.col("dimension_match_status") == "UNMATCHED", 1).otherwise(0)).alias("unmatched_facility_count"),
        F.max("source_publication_at").alias("source_publication_at"),
        F.max("silver_published_at").alias("silver_published_at"),
        F.max("registration_effective_at").alias("registration_effective_at"),
    )
    # Interval-wide totals, published so an operator reads the enrichment health
    # of the interval a figure came from rather than re-deriving it. The
    # expectation above reads these, so they are columns, not a transient check.
    interval = Window.partitionBy("interval_end")
    return (
        grouped.withColumn(
            "interval_known_region_facility_count",
            F.sum("known_region_facility_count").over(interval),
        )
        .withColumn(
            "interval_known_fuel_facility_count",
            F.sum("known_fuel_facility_count").over(interval),
        )
        .withColumn(
            "interval_facility_count", F.sum("facility_count").over(interval)
        )
        .withColumn("source_interval_watermark", F.col("interval_end"))
        .withColumn("gold_published_at", F.current_timestamp())
    )
