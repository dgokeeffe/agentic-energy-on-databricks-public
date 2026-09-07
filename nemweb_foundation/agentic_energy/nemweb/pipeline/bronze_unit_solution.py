"""Append-only daily T+1 DISPATCH UNIT_SOLUTION Bronze contract.

AEMO Current reports do not publish this authoritative target/availability
section every five minutes.  It is therefore labelled and refreshed only as a
Next_Day_Dispatch T+1 source; no five-minute availability is manufactured.
"""

from pyspark import pipelines as dp

from agentic_energy.nemweb.pipeline.io import (
    COMMON_VALIDITY_SQL,
    quarantine,
    section_stream,
)

_UNIT_SOLUTION_COLUMNS = (
    ("SETTLEMENTDATE", "settlementdate", "timestamp"),
    ("RUNNO", "source_run_no", "long"),
    ("DUID", "duid", "string"),
    ("TRADETYPE", "trade_type", "string"),
    ("DISPATCHINTERVAL", "dispatch_interval", "int"),
    ("INTERVENTION", "intervention", "int"),
    ("CONNECTIONPOINTID", "connection_point_id", "string"),
    ("DISPATCHMODE", "dispatch_mode", "int"),
    ("AGCSTATUS", "agc_status", "int"),
    ("INITIALMW", "initial_mw", "double"),
    ("TOTALCLEARED", "total_cleared_mw", "double"),
    ("RAMPDOWNRATE", "ramp_down_rate_mw_per_min", "double"),
    ("RAMPUPRATE", "ramp_up_rate_mw_per_min", "double"),
    ("AVAILABILITY", "availability_mw", "double"),
    ("UIGF", "uigf_mw", "double"),
    ("MIN_AVAILABILITY", "minimum_availability_mw", "double"),
    ("LASTCHANGED", "source_last_changed", "timestamp"),
)
_UNIT_SOLUTION_VALID = (
    f"{COMMON_VALIDITY_SQL} AND interval_end IS NOT NULL AND duid IS NOT NULL "
    "AND intervention IS NOT NULL AND total_cleared_mw IS NOT NULL "
    "AND availability_mw IS NOT NULL"
)


@dp.temporary_view(name="_raw_nem_dispatch_unit_solution_t1")
def raw_nem_dispatch_unit_solution_t1():
    return section_stream(
        spark,
        report_family="next_day_dispatch",
        section_group="DISPATCH",
        section_name="UNIT_SOLUTION",
        columns=_UNIT_SOLUTION_COLUMNS,
    )


@dp.table(
    name="bronze_nem_dispatch_unit_solution_t1",
    comment="Append-only Next_Day_Dispatch UNIT_SOLUTION target and availability at T+1 daily source cadence. Both intervention runs and every source RUNNO are retained.",
    table_properties={"quality": "bronze", "source.cadence": "daily_t_plus_1", "delta.enableRowTracking": "true", "delta.enableChangeDataFeed": "true"},
)
@dp.expect_or_drop("valid_dispatch_unit_solution_t1_contract", _UNIT_SOLUTION_VALID)
def bronze_nem_dispatch_unit_solution_t1():
    return spark.readStream.table("_raw_nem_dispatch_unit_solution_t1")


@dp.table(
    name="quarantine_nem_dispatch_unit_solution_t1",
    comment="Rejected T+1 UNIT_SOLUTION parsed rows with complete source lineage.",
)
def quarantine_nem_dispatch_unit_solution_t1():
    return quarantine(
        spark.readStream.table("_raw_nem_dispatch_unit_solution_t1"),
        _UNIT_SOLUTION_VALID,
        "INVALID_DISPATCH_UNIT_SOLUTION_T1_CONTRACT",
    )
