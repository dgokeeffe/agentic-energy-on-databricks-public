"""Append-only NEMWEB Settlements recovery and residue context.

Current Settlements ZIPs are issued per settlement run (commonly intra-day) and
contain FCASREGIONRECOVERY.v6 and IRSURPLUS.v6. This is financial settlement
context, not operational FCAS dispatch.
"""

from pyspark import pipelines as dp

from agentic_energy.nemweb.pipeline.io import COMMON_VALIDITY_SQL, quarantine, section_stream

_FCAS_COLUMNS = (
    ("SETTLEMENTDATE", "settlementdate", "timestamp"),
    ("VERSIONNO", "source_version_no", "long"),
    ("BIDTYPE", "fcas_service", "string"),
    ("REGIONID", "region_id", "string"),
    ("PERIODID", "period_id", "int"),
    ("GENERATORREGIONENERGY", "generator_region_energy_mwh", "double"),
    ("CUSTOMERREGIONENERGY", "customer_region_energy_mwh", "double"),
    ("REGIONRECOVERY", "region_recovery_factor", "double"),
    ("REGION_ACE_MWH", "region_ace_mwh", "double"),
    ("REGION_ASOE_MWH", "region_asoe_mwh", "double"),
    ("REGIONRECOVERYAMOUNT_ACE", "recovery_amount_ace_aud", "double"),
    ("REGIONRECOVERYAMOUNT_ASOE", "recovery_amount_asoe_aud", "double"),
    ("REGIONRECOVERYAMOUNT", "recovery_amount_aud", "double"),
    ("LASTCHANGED", "source_last_changed", "timestamp"),
)
_IRSR_COLUMNS = (
    ("SETTLEMENTDATE", "settlementdate", "timestamp"),
    ("SETTLEMENTRUNNO", "settlement_run_no", "long"),
    ("PERIODID", "period_id", "int"),
    ("INTERCONNECTORID", "interconnector_id", "string"),
    ("REGIONID", "region_id", "string"),
    ("MWFLOW", "mw_flow", "double"),
    ("LOSSFACTOR", "loss_factor", "double"),
    ("SURPLUSVALUE", "surplus_value_aud", "double"),
    ("UNADJUSTED_IRSR", "unadjusted_irsr_aud", "double"),
    ("CSP_DEROGATION_AMOUNT", "csp_derogation_amount_aud", "double"),
    ("LASTCHANGED", "source_last_changed", "timestamp"),
)
_FCAS_VALID = f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND source_version_no IS NOT NULL AND fcas_service IS NOT NULL AND region_id IS NOT NULL AND period_id IS NOT NULL"
_IRSR_VALID = f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND settlement_run_no IS NOT NULL AND period_id IS NOT NULL AND interconnector_id IS NOT NULL AND region_id IS NOT NULL"


@dp.temporary_view(name="_raw_nem_settlement_fcas_recovery")
def raw_nem_settlement_fcas_recovery():
    return section_stream(spark, report_family="settlement", section_group="SETTLEMENTS", section_name="FCASREGIONRECOVERY", columns=_FCAS_COLUMNS)


@dp.table(
    name="bronze_nem_settlement_fcas_recovery",
    comment="Append-only SETTLEMENTS FCASREGIONRECOVERY.v6 financial recovery rows. VERSIONNO corrections retained; amounts are AUD and energy is MWh.",
    table_properties={"quality": "bronze", "source.cadence": "settlement_run", "freshness.expectation": "refresh daily after the latest source-issued settlement run", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_settlement_fcas_recovery_contract", _FCAS_VALID)
def bronze_nem_settlement_fcas_recovery():
    return spark.readStream.table("_raw_nem_settlement_fcas_recovery")


@dp.table(name="quarantine_nem_settlement_fcas_recovery", comment="Rejected FCASREGIONRECOVERY rows with immutable source lineage.")
def quarantine_nem_settlement_fcas_recovery():
    return quarantine(spark.readStream.table("_raw_nem_settlement_fcas_recovery"), _FCAS_VALID, "INVALID_SETTLEMENT_FCAS_RECOVERY_CONTRACT")


@dp.temporary_view(name="_raw_nem_settlement_irsurplus")
def raw_nem_settlement_irsurplus():
    return section_stream(spark, report_family="settlement", section_group="SETTLEMENTS", section_name="IRSURPLUS", columns=_IRSR_COLUMNS)


@dp.table(
    name="bronze_nem_settlement_irsurplus",
    comment="Append-only SETTLEMENTS IRSURPLUS.v6 inter-regional settlement residue rows. SETTLEMENTRUNNO corrections retained; AEMO source flow sign is unchanged.",
    table_properties={"quality": "bronze", "source.cadence": "settlement_run", "freshness.expectation": "refresh daily after the latest source-issued settlement run", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_settlement_irsurplus_contract", _IRSR_VALID)
def bronze_nem_settlement_irsurplus():
    return spark.readStream.table("_raw_nem_settlement_irsurplus")


@dp.table(name="quarantine_nem_settlement_irsurplus", comment="Rejected IRSURPLUS rows with immutable source lineage.")
def quarantine_nem_settlement_irsurplus():
    return quarantine(spark.readStream.table("_raw_nem_settlement_irsurplus"), _IRSR_VALID, "INVALID_SETTLEMENT_IRSURPLUS_CONTRACT")
