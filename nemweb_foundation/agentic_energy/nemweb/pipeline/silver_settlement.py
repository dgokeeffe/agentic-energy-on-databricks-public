"""Correction-aware financial-settlement context."""

from pyspark import pipelines as dp
from pyspark.sql import functions as F

from agentic_energy.nemweb.pipeline.silver_common import latest_correction

_FCAS_KEY = ("interval_end", "region_id", "period_id", "fcas_service")
_IRSR_KEY = ("interval_end", "period_id", "interconnector_id", "region_id")


@dp.materialized_view(
    name="silver_nem_settlement_fcas_recovery",
    comment="Latest FCASREGIONRECOVERY settlement VERSIONNO per interval, region, period and FCAS service. Financial amounts are AUD; energy columns are MWh.",
    table_properties={"quality": "silver", "source.cadence": "settlement_run", "natural_key": "interval_end,region_id,period_id,fcas_service", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_silver_fcas_recovery_key", "interval_end IS NOT NULL AND region_id IS NOT NULL AND period_id IS NOT NULL AND fcas_service IS NOT NULL")
def silver_nem_settlement_fcas_recovery():
    selected = latest_correction(
        spark.read.table("bronze_nem_settlement_fcas_recovery"),
        _FCAS_KEY,
        source_revision="source_version_no",
    )
    return selected.select(
        *_FCAS_KEY, "source_version_no", "generator_region_energy_mwh",
        "customer_region_energy_mwh", "region_recovery_factor", "region_ace_mwh",
        "region_asoe_mwh", "recovery_amount_ace_aud", "recovery_amount_asoe_aud",
        "recovery_amount_aud", "source_last_changed", "source_archive",
        "source_archive_sha256", "source_publication_at", "landed_at",
        "ingested_at", "ingestion_sequence",
    ).withColumn("silver_published_at", F.current_timestamp())


@dp.materialized_view(
    name="silver_nem_settlement_irsurplus",
    comment="Latest IRSURPLUS SETTLEMENTRUNNO per interval, period, interconnector and region. Monetary columns are AUD; source MWFLOW sign is retained.",
    table_properties={"quality": "silver", "source.cadence": "settlement_run", "natural_key": "interval_end,period_id,interconnector_id,region_id", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_silver_irsurplus_key", "interval_end IS NOT NULL AND period_id IS NOT NULL AND interconnector_id IS NOT NULL AND region_id IS NOT NULL")
def silver_nem_settlement_irsurplus():
    selected = latest_correction(
        spark.read.table("bronze_nem_settlement_irsurplus"),
        _IRSR_KEY,
        source_revision="settlement_run_no",
    )
    return selected.select(
        *_IRSR_KEY, "settlement_run_no", "mw_flow", "loss_factor",
        "surplus_value_aud", "unadjusted_irsr_aud", "csp_derogation_amount_aud",
        "source_last_changed", "source_archive", "source_archive_sha256",
        "source_publication_at", "landed_at", "ingested_at", "ingestion_sequence",
    ).withColumn("silver_published_at", F.current_timestamp())
