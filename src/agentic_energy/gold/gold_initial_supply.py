"""Workshop-only regional actual-supply summary."""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.labs.initial_supply import initial_supply_sql


@dp.materialized_view(
    name="gold_nem_initial_supply_5min",
    comment="Workshop snapshot: signed actual SCADA output by region/interval, not availability or total market supply. Missing attribution remains UNKNOWN. Market intervals are fixed AEST; publication timestamps are UTC instants.",
    table_properties={"quality": "gold", "grain": "five_minutes"},
    cluster_by=["region_id", "interval_end"],
)
@dp.expect_or_fail("valid_supply_key", "interval_end IS NOT NULL AND region_id IS NOT NULL")
@dp.expect_or_fail("valid_supply_coverage", "observed_unit_count > 0 AND partially_enriched_unit_count BETWEEN 0 AND observed_unit_count")
def gold_nem_initial_supply_5min():
    return spark.sql(initial_supply_sql()).withColumn("gold_published_at", F.current_timestamp())
