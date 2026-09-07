"""Daily T+1 authoritative unit dispatch/availability and SCADA reconciliation."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_unit_dispatch_availability_t1",
    comment="Authoritative Next_Day_Dispatch UNIT_SOLUTION target and availability published at daily T+1 cadence. Overlapping five-minute SCADA actual MW is provided only for reconciliation; this table must never be represented as Current five-minute availability. Both intervention rows remain.",
    table_properties={"quality": "gold", "source.cadence": "daily_t_plus_1", "availability": "authoritative_t_plus_1"},
    cluster_by=["duid", "interval_end"],
)
@dp.expect_or_drop(
    "valid_gold_unit_solution_key",
    "interval_end IS NOT NULL AND duid IS NOT NULL AND intervention IS NOT NULL",
)
def gold_nem_unit_dispatch_availability_t1():
    target = spark.read.table("silver_nem_dispatch_unit_solution_t1").alias("t")
    scada = spark.read.table("silver_nem_dispatch_unit_scada").select(
        "interval_end", "duid", "actual_generation_mw",
        F.col("source_publication_at").alias("scada_source_publication_at"),
    ).alias("s")
    facilities = spark.read.table("silver_nem_facility_dimension").alias("f")
    joined = target.join(scada, ["interval_end", "duid"], "left").join(
        facilities, "duid", "left"
    )
    return joined.select(
        F.col("interval_end"),
        F.col("interval_end").alias("source_interval_watermark"),
        F.col("duid"),
        F.col("t.intervention"),
        F.col("t.is_effective_run"),
        F.col("t.trade_type"),
        F.col("t.connection_point_id"),
        F.col("t.dispatch_mode"),
        F.col("t.agc_status"),
        F.col("t.initial_mw"),
        F.col("t.total_cleared_mw"),
        F.col("t.availability_mw"),
        F.col("t.uigf_mw"),
        F.col("t.minimum_availability_mw"),
        F.col("t.ramp_down_rate_mw_per_min"),
        F.col("t.ramp_up_rate_mw_per_min"),
        F.col("s.actual_generation_mw").alias("overlapping_scada_actual_mw"),
        (F.col("s.actual_generation_mw") - F.col("t.total_cleared_mw")).alias("scada_minus_dispatch_target_mw"),
        F.abs(F.col("s.actual_generation_mw") - F.col("t.total_cleared_mw")).alias("absolute_scada_dispatch_variance_mw"),
        F.coalesce(F.col("f.region_id"), F.lit("UNKNOWN")).alias("region_id"),
        F.coalesce(F.col("f.fuel_type"), F.lit("UNKNOWN")).alias("fuel_type"),
        F.coalesce(F.col("f.dimension_match_status"), F.lit("UNMATCHED")).alias("dimension_match_status"),
        F.col("t.source_run_no"),
        F.col("t.report_version"),
        F.col("t.source_publication_at").alias("unit_solution_source_publication_at"),
        F.col("s.scada_source_publication_at"),
        F.greatest(F.col("t.source_publication_at"), F.col("s.scada_source_publication_at")).alias("source_publication_at"),
        F.col("t.silver_published_at"),
        F.current_timestamp().alias("gold_published_at"),
    )
