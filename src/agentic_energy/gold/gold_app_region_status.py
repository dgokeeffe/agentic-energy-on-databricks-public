"""Compact lakehouse-owned serving table for the regional operations app."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_app_region_status",
    comment=(
        "One effective row per NEM region and interval for application serving. "
        "Constraint count and interconnector count/source-sign flow are market-wide values "
        "repeated on each region row; there is no regional allocation and no directional interpretation."
    ),
    table_properties={
        "quality": "gold",
        "grain": "region_interval",
        "delta.enableRowTracking": "true",
        "delta.enableChangeDataFeed": "true",
        "flow.sign": "aemo_source",
    },
    cluster_by=["region_id", "interval_end"],
)
@dp.expect_or_drop(
    "valid_app_region_status_key",
    "region_id IS NOT NULL AND interval_end IS NOT NULL AND is_effective_run",
)
def gold_nem_app_region_status():
    regional = spark.read.table("gold_nem_region_dispatch_5min").where(
        F.col("is_effective_run")
    )
    constraints = (
        spark.read.table("gold_nem_binding_constraints_5min")
        .where(F.col("is_effective_run") & F.col("is_binding"))
        .groupBy("interval_end")
        .agg(F.count("*").alias("market_wide_binding_constraint_count"))
    )
    interconnectors = (
        spark.read.table("gold_nem_interconnector_flows_5min")
        .where(F.col("is_effective_run"))
        .groupBy("interval_end")
        .agg(
            F.countDistinct("interconnector_id").alias("market_wide_interconnector_count"),
            F.sum("mw_flow").alias("market_wide_interconnector_source_sign_flow_mw"),
        )
    )
    return (
        regional.join(constraints, "interval_end", "left")
        .join(interconnectors, "interval_end", "left")
        .select(
            F.sha2(
                F.concat_ws("|", F.col("region_id"), F.col("interval_end").cast("string")),
                256,
            ).alias("serving_key"),
            "region_id",
            "interval_end",
            "intervention",
            "is_effective_run",
            "rrp_aud_per_mwh",
            "total_demand_mw",
            "price_source_run_no",
            "demand_source_run_no",
            "source_interval_watermark",
            "source_publication_at",
            F.col("gold_published_at").alias("regional_gold_published_at"),
            F.current_timestamp().alias("gold_published_at"),
            F.coalesce(F.col("market_wide_binding_constraint_count"), F.lit(0)).cast("long").alias("market_wide_binding_constraint_count"),
            F.coalesce(F.col("market_wide_interconnector_count"), F.lit(0)).cast("long").alias("market_wide_interconnector_count"),
            F.coalesce(F.col("market_wide_interconnector_source_sign_flow_mw"), F.lit(0.0)).cast("double").alias("market_wide_interconnector_source_sign_flow_mw"),
        )
    )
