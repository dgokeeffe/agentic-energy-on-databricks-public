"""Daily T+1 authoritative unit dispatch target and availability contract."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.silver_common import latest_correction, with_effective_run

_KEY = ("interval_end", "duid", "intervention")


@dp.materialized_view(
    name="silver_nem_dispatch_unit_solution_t1",
    comment="Latest Next_Day_Dispatch UNIT_SOLUTION target and availability at daily T+1 source cadence. It must never be represented as five-minute-current availability. Both intervention runs remain.",
    table_properties={"quality": "silver", "source.cadence": "daily_t_plus_1", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_unit_solution_key", "interval_end IS NOT NULL AND duid IS NOT NULL AND intervention IS NOT NULL")
def silver_nem_dispatch_unit_solution_t1():
    latest = latest_correction(spark.read.table("bronze_nem_dispatch_unit_solution_t1"), _KEY)
    selected = latest.select(
        "interval_end", "duid", "intervention", "trade_type", "dispatch_interval",
        "connection_point_id", "dispatch_mode", "agc_status", "initial_mw",
        "total_cleared_mw", "availability_mw", "uigf_mw", "minimum_availability_mw",
        "ramp_down_rate_mw_per_min", "ramp_up_rate_mw_per_min", "source_run_no",
        "report_version", "source_publication_at", "ingested_at",
        F.col("ingested_at").alias("silver_published_at"),
    )
    return with_effective_run(selected, ("interval_end", "duid"))
