"""Append-only NEMWEB TradingIS settlement-price context.

TradingIS PRICE.v3 is published approximately every five minutes. It is kept as
settlement context and must not be confused with DISPATCHIS dispatch prices.
"""

from pyspark import pipelines as dp

from agentic_energy.nemweb.pipeline.io import COMMON_VALIDITY_SQL, quarantine, section_stream

_COLUMNS = (
    ("SETTLEMENTDATE", "settlementdate", "timestamp"),
    ("RUNNO", "source_run_no", "long"),
    ("REGIONID", "region_id", "string"),
    ("PERIODID", "period_id", "int"),
    ("RRP", "settlement_price_aud_per_mwh", "double"),
    ("EEP", "energy_excess_price_aud_per_mwh", "double"),
    ("INVALIDFLAG", "invalid_flag", "string"),
    ("ROP", "regional_override_price_aud_per_mwh", "double"),
    ("PRICE_STATUS", "price_status", "string"),
    ("LASTCHANGED", "source_last_changed", "timestamp"),
)
_VALID = f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND region_id IS NOT NULL AND source_run_no IS NOT NULL AND settlement_price_aud_per_mwh IS NOT NULL"


@dp.temporary_view(name="_raw_nem_trading_price")
def raw_nem_trading_price():
    return section_stream(spark, report_family="trading", section_group="TRADING", section_name="PRICE", columns=_COLUMNS)


@dp.table(
    name="bronze_nem_trading_price",
    comment="Append-only TradingIS PRICE.v3 rows at interval-ending AEST grain. This is settlement context, not DISPATCHIS dispatch price; all RUNNO corrections are retained.",
    table_properties={"quality": "bronze", "source.cadence": "five_minutes", "freshness.expectation": "processed by daily context run and opportunistically by critical pipeline updates", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_trading_price_contract", _VALID)
def bronze_nem_trading_price():
    return spark.readStream.table("_raw_nem_trading_price")


@dp.table(name="quarantine_nem_trading_price", comment="Rejected TradingIS PRICE rows with complete source lineage.")
def quarantine_nem_trading_price():
    return quarantine(spark.readStream.table("_raw_nem_trading_price"), _VALID, "INVALID_TRADING_PRICE_CONTRACT")
