"""Analyst-facing regional dispatch price and demand at five-minute grain."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_region_dispatch_5min",
    comment="Interval-ending five-minute regional dispatch price ($/MWh) and demand (MW). Both intervention rows remain; default analytics must filter is_effective_run to avoid double counting.",
    table_properties={"quality": "gold", "grain": "five_minutes", "source.timezone": "AEST"},
    cluster_by=["region_id", "interval_end"],
)
@dp.expect_or_drop(
    "valid_gold_region_dispatch_key",
    "interval_end IS NOT NULL AND region_id IS NOT NULL AND intervention IS NOT NULL",
)
def gold_nem_region_dispatch_5min():
    source = spark.read.table("silver_nem_region_dispatch")
    return source.select(
        "interval_end",
        F.col("interval_end").alias("source_interval_watermark"),
        "region_id",
        "intervention",
        "is_effective_run",
        "rrp_aud_per_mwh",
        "total_demand_mw",
        "price_source_run_no",
        "demand_source_run_no",
        "available_generation_mw",
        "available_load_mw",
        "demand_forecast_mw",
        "dispatchable_generation_mw",
        "dispatchable_load_mw",
        "net_interchange_mw",
        "energy_excess_price_aud_per_mwh",
        "regional_override_price_aud_per_mwh",
        "administered_price_cap_flag",
        "market_suspended_flag",
        "source_publication_at",
        "silver_published_at",
        F.current_timestamp().alias("gold_published_at"),
    )
