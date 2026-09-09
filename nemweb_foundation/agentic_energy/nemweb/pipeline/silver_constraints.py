"""Correction-aware dispatch constraints with an explicit binding interpretation."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.silver_common import latest_correction, with_effective_run
from agentic_energy.nemweb.source_registry import get_subject_by_key

_KEY = ("interval_end", "constraint_id", "intervention")


@dp.materialized_view(
    name="silver_nem_dispatch_constraint",
    comment="Five-minute DISPATCH CONSTRAINT rows. is_binding is a derived interpretation defined exactly as MARGINALVALUE <> 0; raw RHS/LHS/marginal/violation fields remain and no constraint is filtered out. Both intervention runs remain.",
    table_properties={"quality": "silver", "grain": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_constraint_key", "interval_end IS NOT NULL AND constraint_id IS NOT NULL AND intervention IS NOT NULL")
def silver_nem_dispatch_constraint():
    latest = latest_correction(spark.read.table("bronze_nem_dispatch_constraint"), _KEY,
                               correction_order=get_subject_by_key("dispatch_constraint").correction_order)
    derived = latest.withColumn(
        "is_binding", F.coalesce(F.col("marginal_value") != F.lit(0.0), F.lit(False))
    ).select(
        "interval_end", "constraint_id", "intervention", "rhs", "lhs",
        "marginal_value", "violation_degree", "is_binding", "source_run_no",
        "report_version", "source_publication_at", "ingested_at",
        F.col("ingested_at").alias("silver_published_at"),
    )
    return with_effective_run(derived, ("interval_end", "constraint_id"))
