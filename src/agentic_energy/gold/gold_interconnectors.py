"""Analyst-facing interconnector flows at five-minute dispatch grain."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_interconnector_flows_5min",
    comment="DISPATCH INTERCONNECTORRES flow at interval-ending five-minute grain. AEMO source sign is retained unchanged; positive/negative direction must be interpreted with the governed interconnector definition. Both intervention runs remain; default analytics filter is_effective_run.",
    table_properties={"quality": "gold", "grain": "five_minutes", "flow.sign": "aemo_source"},
    cluster_by=["interconnector_id", "interval_end"],
)
@dp.expect_or_drop(
    "valid_gold_interconnector_key",
    "interval_end IS NOT NULL AND interconnector_id IS NOT NULL AND intervention IS NOT NULL",
)
def gold_nem_interconnector_flows_5min():
    source = spark.read.table("silver_nem_interconnector_flow")
    return source.select(
        "interval_end",
        F.col("interval_end").alias("source_interval_watermark"),
        "interconnector_id",
        "intervention",
        "is_effective_run",
        "metered_mw_flow",
        "mw_flow",
        "mw_losses",
        "export_limit_mw",
        "import_limit_mw",
        "marginal_loss",
        "marginal_value",
        "violation_degree",
        "source_run_no",
        "report_version",
        "source_publication_at",
        "silver_published_at",
        F.current_timestamp().alias("gold_published_at"),
    )
