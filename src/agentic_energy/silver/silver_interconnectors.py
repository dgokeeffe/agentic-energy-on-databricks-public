"""Repaired correction-aware INTERCONNECTORRES five-minute contract."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.common.silver_common import latest_correction, with_effective_run
from agentic_energy.ingestion.source_registry import get_subject_by_key

_KEY = ("interval_end", "interconnector_id", "intervention")


@dp.materialized_view(
    name="silver_nem_interconnector_flow",
    comment="Five-minute INTERCONNECTORRES source flow MW. Source sign is retained unchanged; direction requires the separately governed interconnector definition. Both intervention runs remain.",
    table_properties={"quality": "silver", "grain": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_interconnector_key", "interval_end IS NOT NULL AND interconnector_id IS NOT NULL AND intervention IS NOT NULL")
def silver_nem_interconnector_flow():
    latest = latest_correction(spark.read.table("bronze_nem_dispatch_interconnector_res"), _KEY,
                               correction_order=get_subject_by_key("dispatch_interconnector_res").correction_order)
    selected = latest.select(
        "interval_end", "interconnector_id", "intervention", "metered_mw_flow",
        "mw_flow", "mw_losses", "marginal_value", "violation_degree",
        "export_limit_mw", "import_limit_mw", "marginal_loss", "source_run_no",
        "report_version", "source_publication_at", "ingested_at",
        F.col("ingested_at").alias("silver_published_at"),
    )
    return with_effective_run(selected, ("interval_end", "interconnector_id"))
