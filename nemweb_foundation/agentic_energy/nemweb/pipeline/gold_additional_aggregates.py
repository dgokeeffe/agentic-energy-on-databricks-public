"""Additional 30-minute and daily products derived after five-minute Gold contracts."""

from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.config import (
    SPIKE_BASELINE_INTERVALS,
    spike_baseline_multiple,
)


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
    name="gold_nem_dispatch_price_spike_5min",
    comment=(
        "Relative dispatch-price spike flag at interval-ending five-minute AEST grain, "
        "derived only from effective five-minute dispatch runs. A spike is a price at or "
        "above spike_baseline_multiple times the median of the preceding "
        "288 intervals for the same region; the judged interval is excluded from its own "
        "baseline. is_price_spike is NULL, never false, when the baseline is incomplete or "
        "non-positive, because no comparison was made. price_formation_basis separates "
        "administered and suspended intervals from market-formed prices; an administered "
        "price is an intervention artefact, not a scarcity signal."
    ),
    table_properties={
        "quality": "gold",
        "grain": "five_minutes",
        "derived.from": "gold_nem_region_dispatch_5min",
    },
    cluster_by=["region_id", "interval_end"],
)
def gold_nem_dispatch_price_spike_5min():
    multiple = spike_baseline_multiple(spark)
    # Strictly preceding rows: -1 excludes the interval being judged, so a spike
    # can never inflate the baseline it is measured against.
    baseline = (
        Window.partitionBy("region_id")
        .orderBy("interval_end")
        .rowsBetween(-SPIKE_BASELINE_INTERVALS, -1)
    )
    source = _effective_region_dispatch().select(
        "interval_end",
        F.col("interval_end").alias("source_interval_watermark"),
        "region_id",
        "intervention",
        "is_effective_run",
        "rrp_aud_per_mwh",
        F.when(F.col("market_suspended_flag") == 1, F.lit("SUSPENDED"))
        .when(F.col("administered_price_cap_flag") == 1, F.lit("ADMINISTERED"))
        .otherwise(F.lit("MARKET"))
        .alias("price_formation_basis"),
        "source_publication_at",
    )
    # UNVERIFIED AT RUNTIME: F.median() over a ROWS frame has never been executed
    # here. The Databricks median reference allows OVER, but percentile functions
    # are documented elsewhere as RANGE-only and this pipeline has no precedent
    # (every other window use is row_number()). If the first authorised run raises
    # on the frame, replace only this median with collect_list over the same frame
    # plus percentile_approx on the array; the rule and its tests do not change.
    # See miniwiki/features/price-spike-detector.md.
    #
    # count() over the same frame proves the window is full. Without it a partial
    # window still yields a median, and an early interval would be judged against
    # a handful of rows as though it had a full day of history.
    measured = source.select(
        "*",
        F.median("rrp_aud_per_mwh").over(baseline).alias("_baseline_median"),
        F.count("rrp_aud_per_mwh").over(baseline).alias("_baseline_rows"),
    )
    complete_baseline = F.col("_baseline_rows") >= F.lit(SPIKE_BASELINE_INTERVALS)
    return measured.select(
        "interval_end",
        "source_interval_watermark",
        "region_id",
        "intervention",
        "is_effective_run",
        "rrp_aud_per_mwh",
        "price_formation_basis",
        F.when(complete_baseline, F.col("_baseline_median"))
        .alias("trailing_median_price_aud_per_mwh"),
        F.lit(SPIKE_BASELINE_INTERVALS).alias("spike_baseline_intervals"),
        F.lit(multiple).alias("spike_baseline_multiple"),
        # A non-positive baseline yields NULL, not false: a ratio against zero is
        # undefined, and against a negative median it inverts, so the most extreme
        # negative price in a window would otherwise report as a positive spike.
        F.when(
            complete_baseline & (F.col("_baseline_median") > 0),
            F.col("rrp_aud_per_mwh") >= F.col("_baseline_median") * F.lit(multiple),
        ).alias("is_price_spike"),
        "source_publication_at",
        F.current_timestamp().alias("gold_published_at"),
    )


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
