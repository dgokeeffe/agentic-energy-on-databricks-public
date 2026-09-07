"""Append-only five-minute DISPATCH UNIT_SCADA Bronze contract."""

from pyspark import pipelines as dp

from agentic_energy.nemweb.pipeline.io import (
    COMMON_VALIDITY_SQL,
    FIVE_MINUTE_BOUNDARY_SQL,
    quarantine,
    section_stream,
)

_SCADA_COLUMNS = (
    ("SETTLEMENTDATE", "settlementdate", "timestamp"),
    ("DUID", "duid", "string"),
    # Negative values are legitimate for batteries and dispatchable load.
    ("SCADAVALUE", "actual_generation_mw", "double"),
    ("LASTCHANGED", "source_last_changed", "timestamp"),
)
_SCADA_VALID = (
    f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND duid IS NOT NULL "
    f"AND actual_generation_mw IS NOT NULL AND {FIVE_MINUTE_BOUNDARY_SQL}"
)


@dp.temporary_view(name="_raw_nem_dispatch_unit_scada")
def raw_nem_dispatch_unit_scada():
    return section_stream(
        spark,
        report_family="dispatch_scada",
        section_group="DISPATCH",
        section_name="UNIT_SCADA",
        columns=_SCADA_COLUMNS,
    )


@dp.table(
    name="bronze_nem_dispatch_unit_scada",
    comment="Append-only per-DUID SCADA actual generation MW at interval-ending five-minute AEST grain. Negative battery/load values are retained; this is not a dispatch target or availability measure.",
    table_properties={"quality": "bronze", "source.cadence": "five_minutes", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_dispatch_unit_scada_contract", _SCADA_VALID)
def bronze_nem_dispatch_unit_scada():
    return spark.readStream.table("_raw_nem_dispatch_unit_scada")


@dp.table(
    name="quarantine_nem_dispatch_unit_scada",
    comment="Rejected DISPATCH UNIT_SCADA parsed rows with complete source lineage.",
)
def quarantine_nem_dispatch_unit_scada():
    return quarantine(
        spark.readStream.table("_raw_nem_dispatch_unit_scada"),
        _SCADA_VALID,
        "INVALID_DISPATCH_UNIT_SCADA_CONTRACT",
    )
