"""Governed regional settlement-price context."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_trading_price",
    comment="NEM regional TradingIS settlement price in AUD/MWh at source interval-ending AEST grain. Distinct from the DISPATCHIS dispatch price used by the critical five-minute analyst subject.",
    table_properties={"quality": "gold", "source.cadence": "five_minutes", "semantic.role": "settlement_context"},
    cluster_by=["region_id", "interval_end"],
)
@dp.expect_or_drop("valid_gold_trading_price_key", "interval_end IS NOT NULL AND region_id IS NOT NULL")
def gold_nem_trading_price():
    return spark.read.table("silver_nem_trading_price").select(
        "interval_end",
        F.col("interval_end").alias("source_interval_watermark"),
        "region_id", "period_id", "settlement_price_aud_per_mwh",
        "energy_excess_price_aud_per_mwh", "regional_override_price_aud_per_mwh",
        "invalid_flag", "price_status", "source_run_no", "report_version",
        "source_publication_at", "silver_published_at",
        F.current_timestamp().alias("gold_published_at"),
    )
