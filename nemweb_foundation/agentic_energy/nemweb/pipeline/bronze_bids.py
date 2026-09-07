"""Append-only daily NEMWEB BIDMOVE_COMPLETE offer contracts.

The public Current file contains BIDDAYOFFER_D.v3 and BIDPEROFFER_D.v4 in one
ZIP.  It is published daily after the trading day; offer VERSIONNO values are
retained for correction-aware Silver selection.
"""

from pyspark import pipelines as dp

from agentic_energy.nemweb.pipeline.io import COMMON_VALIDITY_SQL, quarantine, section_stream

_PRICE_COLUMNS = tuple((f"PRICEBAND{i}", f"price_band_{i}_aud_per_mwh", "double") for i in range(1, 11))
_AVAIL_COLUMNS = tuple((f"BANDAVAIL{i}", f"band_availability_{i}_mw", "double") for i in range(1, 11))
_DAY_COLUMNS = (
    ("SETTLEMENTDATE", "settlement_date", "timestamp"),
    ("DUID", "duid", "string"),
    ("BIDTYPE", "bid_type", "string"),
    ("BIDSETTLEMENTDATE", "bid_settlement_at", "timestamp"),
    ("OFFERDATE", "offer_at", "timestamp"),
    ("VERSIONNO", "source_version_no", "long"),
    ("PARTICIPANTID", "participant_id", "string"),
    ("DAILYENERGYCONSTRAINT", "daily_energy_constraint_mwh", "double"),
    ("REBIDEXPLANATION", "rebid_explanation", "string"),
    *_PRICE_COLUMNS,
    ("MINIMUMLOAD", "minimum_load_mw", "double"),
    ("LASTCHANGED", "source_last_changed", "timestamp"),
    ("ENTRYTYPE", "entry_type", "string"),
    ("DIRECTION", "direction", "string"),
)
_PERIOD_COLUMNS = (
    ("SETTLEMENTDATE", "settlement_date", "timestamp"),
    ("DUID", "duid", "string"),
    ("BIDTYPE", "bid_type", "string"),
    ("BIDSETTLEMENTDATE", "bid_settlement_at", "timestamp"),
    ("OFFERDATE", "offer_at", "timestamp"),
    ("PERIODID", "period_id", "int"),
    ("VERSIONNO", "source_version_no", "long"),
    ("MAXAVAIL", "maximum_availability_mw", "double"),
    ("FIXEDLOAD", "fixed_load_mw", "double"),
    ("ROCUP", "ramp_up_rate_mw_per_min", "double"),
    ("ROCDOWN", "ramp_down_rate_mw_per_min", "double"),
    ("ENABLEMENTMIN", "enablement_min_mw", "double"),
    ("ENABLEMENTMAX", "enablement_max_mw", "double"),
    ("LOWBREAKPOINT", "low_breakpoint_mw", "double"),
    ("HIGHBREAKPOINT", "high_breakpoint_mw", "double"),
    *_AVAIL_COLUMNS,
    ("PASAAVAILABILITY", "pasa_availability_mw", "double"),
    ("LASTCHANGED", "source_last_changed", "timestamp"),
    ("INTERVAL_DATETIME", "offer_interval_end", "timestamp"),
    ("DIRECTION", "direction", "string"),
    ("ENERGYLIMIT", "energy_limit_mwh", "double"),
    ("RECALL_PERIOD", "recall_period_minutes", "int"),
)
_DAY_VALID = f"{COMMON_VALIDITY_SQL} AND settlement_date IS NOT NULL AND duid IS NOT NULL AND bid_type IS NOT NULL AND source_version_no IS NOT NULL AND direction IS NOT NULL"
_PERIOD_VALID = f"{_DAY_VALID} AND period_id IS NOT NULL"


@dp.temporary_view(name="_raw_nem_bid_day_offer")
def raw_nem_bid_day_offer():
    return section_stream(spark, report_family="bids", section_group="BID", section_name="BIDDAYOFFER_D", columns=_DAY_COLUMNS)


@dp.table(
    name="bronze_nem_bid_day_offer",
    comment="Append-only daily BIDMOVE_COMPLETE BIDDAYOFFER_D price-band versions. Natural business key is settlement date, DUID, bid type and direction; VERSIONNO is correction order.",
    table_properties={"quality": "bronze", "source.cadence": "daily", "freshness.expectation": "available after source daily publication", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_bid_day_offer_contract", _DAY_VALID)
def bronze_nem_bid_day_offer():
    return spark.readStream.table("_raw_nem_bid_day_offer")


@dp.table(name="quarantine_nem_bid_day_offer", comment="Rejected BIDDAYOFFER_D rows with immutable archive lineage.")
def quarantine_nem_bid_day_offer():
    return quarantine(spark.readStream.table("_raw_nem_bid_day_offer"), _DAY_VALID, "INVALID_BID_DAY_OFFER_CONTRACT")


@dp.temporary_view(name="_raw_nem_bid_period_offer")
def raw_nem_bid_period_offer():
    return section_stream(spark, report_family="bids", section_group="BID", section_name="BIDPEROFFER_D", columns=_PERIOD_COLUMNS)


@dp.table(
    name="bronze_nem_bid_period_offer",
    comment="Append-only daily BIDMOVE_COMPLETE BIDPEROFFER_D period availability versions. Natural business key adds PERIODID to settlement date, DUID, bid type and direction.",
    table_properties={"quality": "bronze", "source.cadence": "daily", "freshness.expectation": "available after source daily publication", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_bid_period_offer_contract", _PERIOD_VALID)
def bronze_nem_bid_period_offer():
    return spark.readStream.table("_raw_nem_bid_period_offer")


@dp.table(name="quarantine_nem_bid_period_offer", comment="Rejected BIDPEROFFER_D rows with immutable archive lineage.")
def quarantine_nem_bid_period_offer():
    return quarantine(spark.readStream.table("_raw_nem_bid_period_offer"), _PERIOD_VALID, "INVALID_BID_PERIOD_OFFER_CONTRACT")
