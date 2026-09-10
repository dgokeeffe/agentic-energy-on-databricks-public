"""Governed regional dispatch-price spike flag at five-minute grain.

The threshold and boundary come from ``resources/metadata/spike_rule.json`` and
are validated before the dataset is defined, so an unreviewed rule cannot reach a
Gold row. This is dispatch price (RRP) in AUD/MWh, never settlement price and
never a forecast. Negative dispatch prices are valid and are never spikes.

Every interval is retained, spike or not, so a caller can distinguish "no spike"
from "no data". Freshness is a label on the row, never a filter: a stale spike is
still reported rather than being silently dropped.
"""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.spike import load_spike_rule, rule_fingerprint

# Fails closed at pipeline load if the metadata is malformed.
_RULE = load_spike_rule()
_FINGERPRINT = rule_fingerprint(_RULE)


@dp.materialized_view(
    name="gold_nem_dispatch_price_spike_5min",
    comment=(
        "Regional dispatch-price spike flag at interval-ending five-minute AEST "
        "(UTC+10, no daylight saving) grain, one row per region and interval. "
        f"is_price_spike is the documented rule rrp_aud_per_mwh > {_RULE.threshold_aud_per_mwh} "
        "AUD/MWh with a strict boundary, so a price exactly at the threshold is not a spike. "
        "The threshold is a workshop-configured level carried in metadata, not an AEMO-published "
        "spike definition. Dispatch price, not settlement price. Negative prices are valid and are "
        "never spikes; a missing price is labelled UNKNOWN_PRICE rather than treated as normal. "
        "Derived from effective intervention runs only; the five-minute regional Gold table retains "
        "both intervention runs for audit. spike_freshness_status labels the answer and never filters it."
    ),
    table_properties={
        "quality": "gold",
        "grain": "five_minutes",
        "source.timezone": "AEST",
        "derived.from": "gold_nem_region_dispatch_5min",
        "spike.rule": "absolute_dispatch_price_over_threshold",
        "spike.boundary": "strict",
        "spike.threshold_aud_per_mwh": str(_RULE.threshold_aud_per_mwh),
        "spike.rule_fingerprint": _FINGERPRINT,
    },
    cluster_by=["region_id", "interval_end"],
)
@dp.expect_or_drop(
    "valid_gold_price_spike_key",
    "interval_end IS NOT NULL AND region_id IS NOT NULL AND is_effective_run",
)
def gold_nem_dispatch_price_spike_5min():
    source = spark.read.table("gold_nem_region_dispatch_5min").where(
        F.col("is_effective_run")
    )
    # current_timestamp() is constant within a single query execution, so the lag
    # and gold_published_at below share one UTC instant. It is written inline at
    # each use so the processing-timestamp contract can verify it statically.
    lag_seconds = F.unix_timestamp(F.current_timestamp()) - F.unix_timestamp(
        F.col("source_publication_at")
    )
    return source.select(
        "interval_end",
        F.col("interval_end").alias("source_interval_watermark"),
        "region_id",
        "intervention",
        "is_effective_run",
        "rrp_aud_per_mwh",
        "total_demand_mw",
        # A null price must not silently become either a spike or a normal
        # interval. coalesce keeps the flag non-null while price_status records
        # that the measure was unavailable.
        F.coalesce(
            F.col("rrp_aud_per_mwh") > F.lit(_RULE.threshold_aud_per_mwh), F.lit(False)
        ).alias("is_price_spike"),
        F.when(F.col("rrp_aud_per_mwh").isNull(), F.lit("UNKNOWN_PRICE"))
        .otherwise(F.lit("PRESENT"))
        .alias("price_status"),
        F.lit(_RULE.rule).alias("spike_rule"),
        F.lit(_RULE.boundary).alias("spike_boundary"),
        F.lit(_RULE.threshold_aud_per_mwh).cast("double").alias("spike_threshold_aud_per_mwh"),
        F.lit(_FINGERPRINT).alias("spike_rule_fingerprint"),
        # Operator context for a flagged interval: an administered cap or a
        # suspended market changes how a high price should be read.
        "administered_price_cap_flag",
        "market_suspended_flag",
        "price_source_run_no",
        "demand_source_run_no",
        lag_seconds.cast("double").alias("source_publication_lag_seconds"),
        F.when(
            lag_seconds > F.lit(_RULE.stale_after_seconds), F.lit("STALE")
        ).otherwise(F.lit("CURRENT")).alias("spike_freshness_status"),
        "source_publication_at",
        F.col("gold_published_at").alias("regional_gold_published_at"),
        F.current_timestamp().alias("gold_published_at"),
    )
