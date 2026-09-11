"""Append-only Bronze contracts for mandatory NEMWEB dimensions.

These tables retain the real monthly MMSDM DUDETAILSUMMARY, DUALLOC and
GENUNITS values required by the proven DUID-to-region/fuel relationship. Fuel
comes from GENUNITS.CO2E_ENERGY_SOURCE, never GENSETTYPE.
"""

from pyspark import pipelines as dp

from agentic_energy.common.io import (
    COMMON_VALIDITY_SQL,
    quarantine,
    section_stream,
)

# Typed projections for all three tables are owned by source_registry.
_GENUNITS_VALID = f"{COMMON_VALIDITY_SQL} AND genset_id IS NOT NULL"
_DUDETAIL_VALID = f"{COMMON_VALIDITY_SQL} AND duid IS NOT NULL AND start_date IS NOT NULL AND region_id IS NOT NULL"
_DUALLOC_VALID = f"{COMMON_VALIDITY_SQL} AND duid IS NOT NULL AND genset_id IS NOT NULL AND effective_at IS NOT NULL"


@dp.temporary_view(name="_raw_nem_genunits")
def raw_nem_genunits():
    return section_stream(
        spark,
        subject_key="genunits",
    )


@dp.table(name="bronze_nem_genunits", comment="Append-only monthly MMSDM GENUNITS versions. CO2E_ENERGY_SOURCE is retained as the authoritative raw fuel field; GENSETTYPE is not fuel.", table_properties={"quality": "bronze", "source.cadence": "monthly", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"})
@dp.expect_or_drop("valid_genunits_contract", _GENUNITS_VALID)
def bronze_nem_genunits():
    return spark.readStream.table("_raw_nem_genunits")


@dp.table(name="quarantine_nem_genunits", comment="Rejected GENUNITS parsed rows with complete source lineage.")
def quarantine_nem_genunits():
    return quarantine(spark.readStream.table("_raw_nem_genunits"), _GENUNITS_VALID, "INVALID_GENUNITS_CONTRACT")


@dp.temporary_view(name="_raw_nem_dudetail")
def raw_nem_dudetail():
    return section_stream(
        spark,
        subject_key="dudetail",
    )


@dp.table(name="bronze_nem_dudetail", comment="Append-only monthly MMSDM DUDETAILSUMMARY effective rows supplying DUID region, station and dispatch classification.", table_properties={"quality": "bronze", "source.cadence": "monthly", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"})
@dp.expect_or_drop("valid_dudetail_contract", _DUDETAIL_VALID)
def bronze_nem_dudetail():
    return spark.readStream.table("_raw_nem_dudetail")


@dp.table(name="quarantine_nem_dudetail", comment="Rejected DUDETAILSUMMARY parsed rows with complete source lineage.")
def quarantine_nem_dudetail():
    return quarantine(spark.readStream.table("_raw_nem_dudetail"), _DUDETAIL_VALID, "INVALID_DUDETAIL_CONTRACT")


@dp.temporary_view(name="_raw_nem_dualloc")
def raw_nem_dualloc():
    return section_stream(
        spark,
        subject_key="dualloc",
    )


@dp.table(name="bronze_nem_dualloc", comment="Append-only MMSDM DUALLOC DUID-to-GENSETID effective versions with source provenance.", table_properties={"quality": "bronze", "source.cadence": "monthly", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"})
@dp.expect_or_drop("valid_dualloc_contract", _DUALLOC_VALID)
def bronze_nem_dualloc():
    return spark.readStream.table("_raw_nem_dualloc")


@dp.table(name="quarantine_nem_dualloc", comment="Rejected DUALLOC rows with complete source lineage.")
def quarantine_nem_dualloc():
    return quarantine(spark.readStream.table("_raw_nem_dualloc"), _DUALLOC_VALID, "INVALID_DUALLOC_CONTRACT")

# STATION, interconnector-master and region-master sources are deliberately not
# declared: no bounded source contract/discovery path has been proven. Critical
# interconnector flows use DISPATCHIS.INTERCONNECTORRES directly.
