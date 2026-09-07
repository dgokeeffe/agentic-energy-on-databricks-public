"""Governed FCAS recovery and inter-regional settlement residue products."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_nem_settlement_fcas_recovery",
    comment="Financial FCAS recovery by interval, region, period and service. Amounts are AUD, energy is MWh, and the source refreshes per settlement run rather than every five minutes.",
    table_properties={"quality": "gold", "source.cadence": "settlement_run", "semantic.role": "financial_settlement_context"},
    cluster_by=["region_id", "interval_end"],
)
@dp.expect_or_drop("valid_gold_fcas_recovery_key", "interval_end IS NOT NULL AND region_id IS NOT NULL AND period_id IS NOT NULL AND fcas_service IS NOT NULL")
def gold_nem_settlement_fcas_recovery():
    return spark.read.table("silver_nem_settlement_fcas_recovery").select(
        "interval_end", F.col("interval_end").alias("source_interval_watermark"),
        "region_id", "period_id", "fcas_service", "generator_region_energy_mwh",
        "customer_region_energy_mwh", "region_recovery_factor", "region_ace_mwh",
        "region_asoe_mwh", "recovery_amount_ace_aud", "recovery_amount_asoe_aud",
        "recovery_amount_aud", "source_version_no", "source_publication_at",
        "silver_published_at", F.current_timestamp().alias("gold_published_at"),
    )


@dp.materialized_view(
    name="gold_nem_interregional_settlement_surplus",
    comment="Inter-regional settlement residue in AUD by interval, period, interconnector and region. MWFLOW keeps the AEMO source sign; refresh cadence follows settlement runs.",
    table_properties={"quality": "gold", "source.cadence": "settlement_run", "flow.sign": "aemo_source", "semantic.role": "financial_settlement_context"},
    cluster_by=["interconnector_id", "interval_end"],
)
@dp.expect_or_drop("valid_gold_irsurplus_key", "interval_end IS NOT NULL AND period_id IS NOT NULL AND interconnector_id IS NOT NULL AND region_id IS NOT NULL")
def gold_nem_interregional_settlement_surplus():
    return spark.read.table("silver_nem_settlement_irsurplus").select(
        "interval_end", F.col("interval_end").alias("source_interval_watermark"),
        "period_id", "interconnector_id", "region_id", "mw_flow", "loss_factor",
        "surplus_value_aud", "unadjusted_irsr_aud", "csp_derogation_amount_aud",
        "settlement_run_no", "source_publication_at", "silver_published_at",
        F.current_timestamp().alias("gold_published_at"),
    )
