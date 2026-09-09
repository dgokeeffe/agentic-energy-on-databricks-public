"""Five-minute SCADA generation aggregated by governed region and fuel."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


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
    )
    return enriched.groupBy("interval_end", "region_id", "fuel_type").agg(
        F.sum("actual_generation_mw").alias("actual_generation_mw"),
        F.countDistinct("duid").alias("facility_count"),
        F.sum(F.when(F.col("dimension_match_status") != "REGION_AND_FUEL", 1).otherwise(0)).alias("partially_enriched_facility_count"),
        F.max("source_publication_at").alias("source_publication_at"),
        F.max("silver_published_at").alias("silver_published_at"),
    ).withColumn(
        "source_interval_watermark", F.col("interval_end")
    ).withColumn("gold_published_at", F.current_timestamp())
