"""Correction-aware regional dispatch price and demand at five-minute grain."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.silver_common import latest_correction, with_effective_run
from agentic_energy.nemweb.source_registry import get_subject_by_key

_KEY = ("interval_end", "region_id", "intervention")


@dp.materialized_view(
    name="silver_nem_region_dispatch",
    comment="Five-minute interval-ending NEM regional price ($/MWh) and demand (MW). Both intervention runs remain; is_effective_run marks the highest available intervention flag and must be used by default aggregations.",
    table_properties={"quality": "silver", "grain": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop(
    "complete_region_dispatch_pair",
    "interval_end IS NOT NULL AND region_id IS NOT NULL AND intervention IS NOT NULL "
    "AND rrp_aud_per_mwh IS NOT NULL AND total_demand_mw IS NOT NULL",
)
def silver_nem_region_dispatch():
    price = latest_correction(spark.read.table("bronze_nem_dispatch_price"), _KEY,
                              correction_order=get_subject_by_key("dispatch_price").correction_order).alias("p")
    demand = latest_correction(spark.read.table("bronze_nem_dispatch_region_sum"), _KEY,
                               correction_order=get_subject_by_key("dispatch_region_sum").correction_order).alias("d")
    # PRICE and REGIONSUM are a single analyst contract. An incomplete section
    # pair must not supersede a complete effective run with a null measure.
    joined = price.join(demand, list(_KEY), "inner").select(
        *[F.col(name) for name in _KEY],
        F.col("p.rrp_aud_per_mwh"), F.col("p.energy_excess_price_aud_per_mwh"),
        F.col("p.regional_override_price_aud_per_mwh"), F.col("p.administered_price_cap_flag"),
        F.col("p.market_suspended_flag"), F.col("d.total_demand_mw"),
        F.col("p.source_run_no").alias("price_source_run_no"),
        F.col("d.source_run_no").alias("demand_source_run_no"),
        F.col("d.available_generation_mw"), F.col("d.available_load_mw"),
        F.col("d.demand_forecast_mw"), F.col("d.dispatchable_generation_mw"),
        F.col("d.dispatchable_load_mw"), F.col("d.net_interchange_mw"),
        F.greatest(F.col("p.source_publication_at"), F.col("d.source_publication_at")).alias("source_publication_at"),
        F.greatest(F.col("p.ingested_at"), F.col("d.ingested_at")).alias("silver_published_at"),
    )
    return with_effective_run(joined, ("interval_end", "region_id"))
