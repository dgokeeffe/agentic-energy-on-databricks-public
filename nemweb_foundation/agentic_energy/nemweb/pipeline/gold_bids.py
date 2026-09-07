"""Curated daily bid stack joining price bands to period availability."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

_JOIN_KEY = ("settlement_date", "duid", "bid_type", "direction")


@dp.materialized_view(
    name="gold_nem_bid_stack",
    comment="Daily NEM bid stack at DUID, bid type, direction and period grain. Price bands are AUD/MWh; band availability and maximum availability are MW. Source BIDMOVE_COMPLETE is daily, so this is context rather than a five-minute dispatch product.",
    table_properties={"quality": "gold", "source.cadence": "daily", "grain": "duid_bid_type_direction_period"},
    cluster_by=["duid", "settlement_date"],
)
@dp.expect_or_drop("valid_gold_bid_stack_key", "settlement_date IS NOT NULL AND duid IS NOT NULL AND bid_type IS NOT NULL AND direction IS NOT NULL AND period_id IS NOT NULL")
def gold_nem_bid_stack():
    period = spark.read.table("silver_nem_bid_period_offer").alias("p")
    day = spark.read.table("silver_nem_bid_day_offer").alias("d")
    joined = period.join(day, list(_JOIN_KEY), "left")
    columns = [
        *[F.col(name) for name in _JOIN_KEY],
        F.col("p.period_id"),
        F.coalesce(F.col("p.offer_interval_end"), F.col("p.settlement_date")).alias("source_interval_watermark"),
        F.col("p.offer_interval_end"),
        F.col("p.maximum_availability_mw"),
        F.col("p.fixed_load_mw"),
        F.col("p.ramp_up_rate_mw_per_min"),
        F.col("p.ramp_down_rate_mw_per_min"),
        F.col("p.enablement_min_mw"),
        F.col("p.enablement_max_mw"),
        F.col("p.low_breakpoint_mw"),
        F.col("p.high_breakpoint_mw"),
        F.col("p.pasa_availability_mw"),
        F.col("p.energy_limit_mwh"),
        F.col("p.recall_period_minutes"),
        F.col("d.minimum_load_mw"),
        F.col("d.daily_energy_constraint_mwh"),
        F.col("d.rebid_explanation"),
    ]
    columns.extend(F.col(f"d.price_band_{i}_aud_per_mwh") for i in range(1, 11))
    columns.extend(F.col(f"p.band_availability_{i}_mw") for i in range(1, 11))
    columns.extend((
        F.col("p.source_version_no").alias("period_offer_version_no"),
        F.col("d.source_version_no").alias("day_offer_version_no"),
        F.greatest(F.col("p.source_publication_at"), F.col("d.source_publication_at")).alias("source_publication_at"),
        F.greatest(F.col("p.silver_published_at"), F.col("d.silver_published_at")).alias("silver_published_at"),
        F.current_timestamp().alias("gold_published_at"),
    ))
    return joined.select(*columns)
