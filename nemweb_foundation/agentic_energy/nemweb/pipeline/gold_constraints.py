"""Analyst-facing binding constraints at five-minute dispatch grain."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_binding_constraints_5min",
    comment="Binding DISPATCH CONSTRAINT rows at interval-ending five-minute grain. is_binding is the documented Silver derivation MARGINALVALUE <> 0. Both intervention runs remain; default analytics must filter is_effective_run.",
    table_properties={"quality": "gold", "grain": "five_minutes", "binding.rule": "marginal_value_non_zero"},
    cluster_by=["constraint_id", "interval_end"],
)
@dp.expect_or_drop(
    "valid_gold_binding_constraint_key",
    "interval_end IS NOT NULL AND constraint_id IS NOT NULL AND intervention IS NOT NULL AND is_binding",
)
def gold_nem_binding_constraints_5min():
    source = spark.read.table("silver_nem_dispatch_constraint").where(F.col("is_binding"))
    return source.select(
        "interval_end",
        F.col("interval_end").alias("source_interval_watermark"),
        "constraint_id",
        "intervention",
        "is_effective_run",
        "is_binding",
        "rhs",
        "lhs",
        "marginal_value",
        "violation_degree",
        "source_run_no",
        "report_version",
        "source_publication_at",
        "silver_published_at",
        F.current_timestamp().alias("gold_published_at"),
    )
