"""Latest correction-aware TradingIS settlement prices."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.silver_common import latest_correction

_KEY = ("interval_end", "region_id")


@dp.materialized_view(
    name="silver_nem_trading_price",
    comment="Latest TradingIS settlement price per interval-ending AEST interval and NEM region. RUNNO is correction order. This settlement series is distinct from five-minute DISPATCHIS dispatch price.",
    table_properties={"quality": "silver", "source.cadence": "five_minutes", "natural_key": "interval_end,region_id", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_silver_trading_price_key", "interval_end IS NOT NULL AND region_id IS NOT NULL")
def silver_nem_trading_price():
    selected = latest_correction(spark.read.table("bronze_nem_trading_price"), _KEY)
    return selected.select(
        *_KEY, "period_id", "settlement_price_aud_per_mwh",
        "energy_excess_price_aud_per_mwh", "regional_override_price_aud_per_mwh",
        "invalid_flag", "price_status", "source_run_no", "report_version",
        "source_last_changed", "source_archive", "source_archive_sha256",
        "source_publication_at", "landed_at", "ingested_at", "ingestion_sequence",
    ).withColumn("silver_published_at", F.current_timestamp())
