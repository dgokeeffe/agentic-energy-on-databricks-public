"""Correction-aware daily energy and FCAS offer contracts."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.silver_common import latest_correction

_DAY_KEY = ("settlement_date", "duid", "bid_type", "direction")
_PERIOD_KEY = (*_DAY_KEY, "period_id")
_PRICE_COLUMNS = tuple(f"price_band_{i}_aud_per_mwh" for i in range(1, 11))
_AVAIL_COLUMNS = tuple(f"band_availability_{i}_mw" for i in range(1, 11))


@dp.materialized_view(
    name="silver_nem_bid_day_offer",
    comment="Latest valid BIDDAYOFFER_D version for each settlement date, DUID, bid type and direction. Prices are AUD/MWh and NEM market timestamps are interval-ending AEST (UTC+10).",
    table_properties={"quality": "silver", "source.cadence": "daily", "natural_key": "settlement_date,duid,bid_type,direction", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_silver_bid_day_key", "settlement_date IS NOT NULL AND duid IS NOT NULL AND bid_type IS NOT NULL AND direction IS NOT NULL")
def silver_nem_bid_day_offer():
    selected = latest_correction(
        spark.read.table("bronze_nem_bid_day_offer"),
        _DAY_KEY,
        source_revision="source_version_no",
    )
    return selected.select(
        *_DAY_KEY,
        "bid_settlement_at", "offer_at", "source_version_no", "participant_id",
        "daily_energy_constraint_mwh", "rebid_explanation", *_PRICE_COLUMNS,
        "minimum_load_mw", "entry_type", "source_last_changed",
        "source_archive", "source_archive_sha256", "source_publication_at",
        "landed_at", "ingested_at", "ingestion_sequence",
    ).withColumn("silver_published_at", F.current_timestamp())


@dp.materialized_view(
    name="silver_nem_bid_period_offer",
    comment="Latest valid BIDPEROFFER_D version per settlement date, DUID, bid type, direction and PERIODID. MW availability is source-reported and never inferred from price bands.",
    table_properties={"quality": "silver", "source.cadence": "daily", "natural_key": "settlement_date,duid,bid_type,direction,period_id", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_silver_bid_period_key", "settlement_date IS NOT NULL AND duid IS NOT NULL AND bid_type IS NOT NULL AND direction IS NOT NULL AND period_id IS NOT NULL")
def silver_nem_bid_period_offer():
    selected = latest_correction(
        spark.read.table("bronze_nem_bid_period_offer"),
        _PERIOD_KEY,
        source_revision="source_version_no",
    )
    return selected.select(
        *_PERIOD_KEY,
        "bid_settlement_at", "offer_at", "offer_interval_end", "source_version_no",
        "maximum_availability_mw", "fixed_load_mw", "ramp_up_rate_mw_per_min",
        "ramp_down_rate_mw_per_min", "enablement_min_mw", "enablement_max_mw",
        "low_breakpoint_mw", "high_breakpoint_mw", *_AVAIL_COLUMNS,
        "pasa_availability_mw", "energy_limit_mwh", "recall_period_minutes",
        "source_last_changed", "source_archive", "source_archive_sha256",
        "source_publication_at", "landed_at", "ingested_at", "ingestion_sequence",
    ).withColumn("silver_published_at", F.current_timestamp())
