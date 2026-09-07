"""Additional 30-minute and daily products derived after five-minute Gold contracts."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


def _effective_region_dispatch():
    return spark.read.table("gold_nem_region_dispatch_5min").where(F.col("is_effective_run"))


@dp.materialized_view(
    name="gold_nem_dispatch_price_30min",
    comment="Additional 30-minute regional summary derived only from effective five-minute dispatch runs; the five-minute Gold table remains the primary product.",
    table_properties={"quality": "gold", "grain": "thirty_minutes", "derived.from": "gold_nem_region_dispatch_5min"},
)
def gold_nem_dispatch_price_30min():
    source = _effective_region_dispatch().withColumn(
        "period",
        F.window(F.col("interval_end") - F.expr("INTERVAL 1 MICROSECOND"), "30 minutes"),
    )
    return source.groupBy("period", "region_id").agg(
        F.avg("rrp_aud_per_mwh").alias("average_dispatch_price_aud_per_mwh"),
        F.avg("total_demand_mw").alias("average_demand_mw"),
        F.count("*").alias("five_minute_interval_count"),
        F.max("interval_end").alias("source_interval_watermark"),
        F.max("source_publication_at").alias("source_publication_at"),
    ).select(
        F.col("period.start").alias("period_start"),
        F.col("period.end").alias("period_end"),
        "region_id", "average_dispatch_price_aud_per_mwh", "average_demand_mw",
        "five_minute_interval_count", "source_interval_watermark", "source_publication_at",
        F.current_timestamp().alias("gold_published_at"),
    )


@dp.materialized_view(
    name="gold_nem_dispatch_price_daily",
    comment="Additional AEST market-day regional summary derived only from effective five-minute dispatch runs.",
    table_properties={"quality": "gold", "grain": "market_day", "derived.from": "gold_nem_region_dispatch_5min"},
)
def gold_nem_dispatch_price_daily():
    source = _effective_region_dispatch().withColumn(
        "market_date",
        F.to_date(F.col("interval_end") - F.expr("INTERVAL 1 MICROSECOND")),
    )
    return source.groupBy("market_date", "region_id").agg(
        F.avg("rrp_aud_per_mwh").alias("average_dispatch_price_aud_per_mwh"),
        F.min("rrp_aud_per_mwh").alias("minimum_dispatch_price_aud_per_mwh"),
        F.max("rrp_aud_per_mwh").alias("maximum_dispatch_price_aud_per_mwh"),
        F.avg("total_demand_mw").alias("average_demand_mw"),
        F.count("*").alias("five_minute_interval_count"),
        F.max("interval_end").alias("source_interval_watermark"),
        F.max("source_publication_at").alias("source_publication_at"),
    ).withColumn("gold_published_at", F.current_timestamp())


@dp.materialized_view(
    name="gold_nem_interconnector_flow_30min",
    comment="Additional 30-minute interconnector summary derived only from effective five-minute source-sign flow rows.",
    table_properties={"quality": "gold", "grain": "thirty_minutes", "derived.from": "gold_nem_interconnector_flows_5min"},
)
def gold_nem_interconnector_flow_30min():
    source = spark.read.table("gold_nem_interconnector_flows_5min").where(
        F.col("is_effective_run")
    ).withColumn(
        "period",
        F.window(F.col("interval_end") - F.expr("INTERVAL 1 MICROSECOND"), "30 minutes"),
    )
    return source.groupBy("period", "interconnector_id").agg(
        F.avg("mw_flow").alias("average_mw_flow"),
        F.sum("mw_losses").alias("total_mw_losses"),
        F.count("*").alias("five_minute_interval_count"),
        F.max("interval_end").alias("source_interval_watermark"),
        F.max("source_publication_at").alias("source_publication_at"),
    ).select(
        F.col("period.start").alias("period_start"),
        F.col("period.end").alias("period_end"),
        "interconnector_id", "average_mw_flow", "total_mw_losses",
        "five_minute_interval_count", "source_interval_watermark", "source_publication_at",
        F.current_timestamp().alias("gold_published_at"),
    )
