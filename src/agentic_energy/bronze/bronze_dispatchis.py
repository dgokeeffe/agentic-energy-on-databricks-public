"""Append-only Bronze contracts for all critical DISPATCHIS sections.

DISPATCHIS is landed once per five-minute cycle; this file fans the single
all-section parsed stream into price, demand, constraint and interconnector
subjects without deleting prior report versions or intervention runs.
"""

from pyspark import pipelines as dp

from agentic_energy.common.io import (
    COMMON_VALIDITY_SQL,
    FIVE_MINUTE_BOUNDARY_SQL,
    quarantine,
    section_stream,
)

# Typed projections for all four sections are owned by source_registry.

_PRICE_VALID = (
    f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND region_id IS NOT NULL "
    f"AND intervention IS NOT NULL AND rrp_aud_per_mwh IS NOT NULL AND {FIVE_MINUTE_BOUNDARY_SQL}"
)
_REGION_SUM_VALID = (
    f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND region_id IS NOT NULL "
    f"AND intervention IS NOT NULL AND total_demand_mw IS NOT NULL AND {FIVE_MINUTE_BOUNDARY_SQL}"
)
_CONSTRAINT_VALID = (
    f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND constraint_id IS NOT NULL "
    f"AND intervention IS NOT NULL AND {FIVE_MINUTE_BOUNDARY_SQL}"
)
_INTERCONNECTOR_VALID = (
    f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL "
    "AND interconnector_id IS NOT NULL AND intervention IS NOT NULL "
    f"AND mw_flow IS NOT NULL AND {FIVE_MINUTE_BOUNDARY_SQL}"
)


@dp.temporary_view(name="_raw_nem_dispatch_price")
def raw_nem_dispatch_price():
    return section_stream(
        spark,
        subject_key="dispatch_price",
    )


@dp.table(
    name="bronze_nem_dispatch_price",
    comment="Append-only DISPATCHIS PRICE rows at interval-ending AEST grain; all source versions and intervention runs retained.",
    table_properties={"quality": "bronze", "source.cadence": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_dispatch_price_contract", _PRICE_VALID)
def bronze_nem_dispatch_price():
    return spark.readStream.table("_raw_nem_dispatch_price")


@dp.table(name="quarantine_nem_dispatch_price", comment="Rejected DISPATCHIS PRICE parsed rows with complete source lineage.")
def quarantine_nem_dispatch_price():
    return quarantine(
        spark.readStream.table("_raw_nem_dispatch_price"),
        _PRICE_VALID,
        "INVALID_DISPATCH_PRICE_CONTRACT",
    )


@dp.temporary_view(name="_raw_nem_dispatch_region_sum")
def raw_nem_dispatch_region_sum():
    return section_stream(
        spark,
        subject_key="dispatch_region_sum",
    )


@dp.table(
    name="bronze_nem_dispatch_region_sum",
    comment="Append-only DISPATCHIS REGIONSUM rows at interval-ending AEST grain; all source versions and intervention runs retained.",
    table_properties={"quality": "bronze", "source.cadence": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_dispatch_region_sum_contract", _REGION_SUM_VALID)
def bronze_nem_dispatch_region_sum():
    return spark.readStream.table("_raw_nem_dispatch_region_sum")


@dp.table(name="quarantine_nem_dispatch_region_sum", comment="Rejected DISPATCHIS REGIONSUM parsed rows with complete source lineage.")
def quarantine_nem_dispatch_region_sum():
    return quarantine(
        spark.readStream.table("_raw_nem_dispatch_region_sum"),
        _REGION_SUM_VALID,
        "INVALID_DISPATCH_REGION_SUM_CONTRACT",
    )


@dp.temporary_view(name="_raw_nem_dispatch_constraint")
def raw_nem_dispatch_constraint():
    return section_stream(
        spark,
        subject_key="dispatch_constraint",
    )


@dp.table(
    name="bronze_nem_dispatch_constraint",
    comment="Append-only DISPATCHIS CONSTRAINT rows; binding interpretation is deferred to a proven Silver contract.",
    table_properties={"quality": "bronze", "source.cadence": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_dispatch_constraint_contract", _CONSTRAINT_VALID)
def bronze_nem_dispatch_constraint():
    return spark.readStream.table("_raw_nem_dispatch_constraint")


@dp.table(name="quarantine_nem_dispatch_constraint", comment="Rejected DISPATCHIS CONSTRAINT parsed rows with complete source lineage.")
def quarantine_nem_dispatch_constraint():
    return quarantine(
        spark.readStream.table("_raw_nem_dispatch_constraint"),
        _CONSTRAINT_VALID,
        "INVALID_DISPATCH_CONSTRAINT_CONTRACT",
    )


@dp.temporary_view(name="_raw_nem_dispatch_interconnector_res")
def raw_nem_dispatch_interconnector_res():
    return section_stream(
        spark,
        subject_key="dispatch_interconnector_res",
    )


@dp.table(
    name="bronze_nem_dispatch_interconnector_res",
    comment="Append-only DISPATCHIS INTERCONNECTORRES rows; source flow sign and both intervention runs are retained unchanged.",
    table_properties={"quality": "bronze", "source.cadence": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_dispatch_interconnector_contract", _INTERCONNECTOR_VALID)
def bronze_nem_dispatch_interconnector_res():
    return spark.readStream.table("_raw_nem_dispatch_interconnector_res")


@dp.table(name="quarantine_nem_dispatch_interconnector_res", comment="Rejected DISPATCHIS INTERCONNECTORRES parsed rows with complete source lineage.")
def quarantine_nem_dispatch_interconnector_res():
    return quarantine(
        spark.readStream.table("_raw_nem_dispatch_interconnector_res"),
        _INTERCONNECTOR_VALID,
        "INVALID_DISPATCH_INTERCONNECTOR_CONTRACT",
    )
