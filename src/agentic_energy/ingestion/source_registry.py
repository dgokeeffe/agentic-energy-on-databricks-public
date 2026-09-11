"""Single registry for the NEMWEB subjects used by application pipelines.

The first app slice publishes per-unit SCADA and generation by fuel. Its
five-minute path therefore requires only UNIT_SCADA; monthly DUDETAILSUMMARY,
DUALLOC, and GENUNITS provide governed region, fuel, and capacity enrichment.
The existing regional subjects remain registered for compatibility, but they
are not dependencies of this generation-only critical cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SourceField:
    source_name: str
    target_name: str
    parser_kind: str
    spark_type: str
    required: bool = False


@dataclass(frozen=True)
class SourceSubject:
    key: str
    report_family: str
    discovery_kind: str
    current_folder: str | None
    archive_folder_template: str | None
    filename_prefix: str
    filename_suffix: str
    section_group: str
    section_name: str
    section_version: str
    landing_table: str
    fields: tuple[SourceField, ...]
    natural_key: tuple[str, ...]
    correction_order: tuple[str, ...]
    expected_cadence: str
    required_scope: str
    archive_layouts: frozenset[str]
    app_dependencies: tuple[str, ...]
    encodings: tuple[str, ...] = ("utf-8-sig", "cp1252")

    @property
    def section_identity(self) -> tuple[str, str, str]:
        return self.section_group, self.section_name, self.section_version


def _f(source: str, target: str | None = None, kind: str = "string", spark: str = "string", required: bool = False) -> SourceField:
    return SourceField(source, target or source.lower(), kind, spark, required)


def _dispatch(
    key: str,
    section: str,
    version: str,
    table: str,
    fields: tuple[SourceField, ...],
    natural: tuple[str, ...],
    deps: tuple[str, ...],
    *,
    required_scope: str = "regional",
) -> SourceSubject:
    return SourceSubject(key, "dispatchis", "current", "DispatchIS_Reports", None,
        "PUBLIC_DISPATCHIS_", ".zip", "DISPATCH", section, version, table,
        fields, natural, ("report_version", "source_run_no", "source_last_changed", "source_publication_at", "landed_at", "source_record_id"),
        "five_minutes", required_scope, frozenset({"direct", "nested"}), deps)


APP_CRITICAL_SUBJECTS: tuple[SourceSubject, ...] = (
    _dispatch("dispatch_price", "PRICE", "5", "landing_nem_dispatch_price", (
        _f("SETTLEMENTDATE", "settlementdate", "market_timestamp", "timestamp", True), _f("RUNNO", "source_run_no", "int", "long", True),
        _f("REGIONID", "region_id", required=True), _f("DISPATCHINTERVAL", "dispatch_interval", "int", "int"), _f("INTERVENTION", "intervention", "int", "int", True),
        _f("RRP", "rrp_aud_per_mwh", "float", "double", True), _f("EEP", "energy_excess_price_aud_per_mwh", "float", "double"),
        _f("ROP", "regional_override_price_aud_per_mwh", "float", "double"), _f("APCFLAG", "administered_price_cap_flag", "int", "int"),
        _f("MARKETSUSPENDEDFLAG", "market_suspended_flag", "int", "int"), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp")),
        ("interval_end", "region_id", "intervention"),
        ("gold_nem_region_dispatch_5min",), required_scope="critical"),
    _dispatch("dispatch_region_sum", "REGIONSUM", "9", "landing_nem_dispatch_region_sum", (
        _f("SETTLEMENTDATE", "settlementdate", "market_timestamp", "timestamp", True), _f("RUNNO", "source_run_no", "int", "long", True), _f("REGIONID", "region_id", required=True),
        _f("DISPATCHINTERVAL", "dispatch_interval", "int", "int"), _f("INTERVENTION", "intervention", "int", "int", True), _f("TOTALDEMAND", "total_demand_mw", "float", "double", True),
        _f("AVAILABLEGENERATION", "available_generation_mw", "float", "double"), _f("AVAILABLELOAD", "available_load_mw", "float", "double"),
        _f("DEMANDFORECAST", "demand_forecast_mw", "float", "double"), _f("DISPATCHABLEGENERATION", "dispatchable_generation_mw", "float", "double"),
        _f("DISPATCHABLELOAD", "dispatchable_load_mw", "float", "double"), _f("NETINTERCHANGE", "net_interchange_mw", "float", "double"), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp")),
        ("interval_end", "region_id", "intervention"),
        ("gold_nem_region_dispatch_5min",), required_scope="critical"),
    _dispatch("dispatch_constraint", "CONSTRAINT", "5", "landing_nem_dispatch_constraint", (
        _f("SETTLEMENTDATE", "settlementdate", "market_timestamp", "timestamp", True), _f("RUNNO", "source_run_no", "int", "long", True), _f("CONSTRAINTID", "constraint_id", required=True),
        _f("DISPATCHINTERVAL", "dispatch_interval", "int", "int"), _f("INTERVENTION", "intervention", "int", "int", True), _f("RHS", "rhs", "float", "double"),
        _f("MARGINALVALUE", "marginal_value", "float", "double"), _f("VIOLATIONDEGREE", "violation_degree", "float", "double"), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp"), _f("LHS", "lhs", "float", "double")),
        ("interval_end", "constraint_id", "intervention"), ("gold_nem_app_region_status",)),
    _dispatch("dispatch_interconnector_res", "INTERCONNECTORRES", "3", "landing_nem_dispatch_interconnector_res", (
        _f("SETTLEMENTDATE", "settlementdate", "market_timestamp", "timestamp", True), _f("RUNNO", "source_run_no", "int", "long", True), _f("INTERCONNECTORID", "interconnector_id", required=True),
        _f("DISPATCHINTERVAL", "dispatch_interval", "int", "int"), _f("INTERVENTION", "intervention", "int", "int", True), _f("METEREDMWFLOW", "metered_mw_flow", "float", "double"),
        _f("MWFLOW", "mw_flow", "float", "double", True), _f("MWLOSSES", "mw_losses", "float", "double"), _f("MARGINALVALUE", "marginal_value", "float", "double"),
        _f("VIOLATIONDEGREE", "violation_degree", "float", "double"), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp"),
        _f("EXPORTLIMIT", "export_limit_mw", "float", "double"), _f("IMPORTLIMIT", "import_limit_mw", "float", "double"), _f("MARGINALLOSS", "marginal_loss", "float", "double")),
        ("interval_end", "interconnector_id", "intervention"), ("gold_nem_app_region_status",)),
    SourceSubject("dispatch_unit_scada", "dispatch_scada", "current", "Dispatch_SCADA", None, "PUBLIC_DISPATCHSCADA_", ".zip", "DISPATCH", "UNIT_SCADA", "1", "landing_nem_dispatch_unit_scada", (
        _f("SETTLEMENTDATE", "settlementdate", "market_timestamp", "timestamp", True), _f("DUID", "duid", required=True), _f("SCADAVALUE", "actual_generation_mw", "float", "double", True), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp")),
        ("interval_end", "duid"), ("report_version", "source_last_changed", "source_publication_at", "landed_at", "source_record_id"), "five_minutes", "critical", frozenset({"direct", "nested"}), ("gold_nem_unit_dispatch_5min", "gold_nem_scada_generation_5min")),
    SourceSubject("dudetail", "registration", "monthly", None, "Data_Archive/Wholesale_Electricity/MMSDM/{year}/MMSDM_{year}_{month}", "PUBLIC_ARCHIVE#DUDETAILSUMMARY#", ".zip", "PARTICIPANT_REGISTRATION", "DUDETAILSUMMARY", "7", "landing_nem_dudetail", (
        _f("DUID", "duid", required=True), _f("START_DATE", "start_date", "market_timestamp", "timestamp", True), _f("END_DATE", "end_date", "market_timestamp", "timestamp"), _f("REGIONID", "region_id", required=True),
        _f("STATIONID", "station_id"), _f("DISPATCHTYPE", "dispatch_type"), _f("SCHEDULE_TYPE", "schedule_type"), _f("PARTICIPANTID", "participant_id"), _f("CONNECTIONPOINTID", "connection_point_id"),
        _f("TRANSMISSIONLOSSFACTOR", "transmission_loss_factor", "float", "double"), _f("DISTRIBUTIONLOSSFACTOR", "distribution_loss_factor", "float", "double"), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp"),
        _f("STARTTYPE"), _f("MINIMUM_ENERGY_PRICE", kind="float", spark="double"), _f("MAXIMUM_ENERGY_PRICE", kind="float", spark="double"),
        _f("MIN_RAMP_RATE_UP", kind="float", spark="double"), _f("MIN_RAMP_RATE_DOWN", kind="float", spark="double"), _f("MAX_RAMP_RATE_UP", kind="float", spark="double"), _f("MAX_RAMP_RATE_DOWN", kind="float", spark="double"),
        _f("IS_AGGREGATED"), _f("DISPATCHSUBTYPE"), _f("ADG_ID"), _f("LOAD_MINIMUM_ENERGY_PRICE", kind="float", spark="double"), _f("LOAD_MAXIMUM_ENERGY_PRICE", kind="float", spark="double"),
        _f("LOAD_MIN_RAMP_RATE_UP", kind="float", spark="double"), _f("LOAD_MIN_RAMP_RATE_DOWN", kind="float", spark="double"), _f("LOAD_MAX_RAMP_RATE_UP", kind="float", spark="double"), _f("LOAD_MAX_RAMP_RATE_DOWN", kind="float", spark="double"), _f("SECONDARY_TLF", kind="float", spark="double")),
        ("duid", "start_date"), ("report_version", "source_last_changed", "source_publication_at", "landed_at", "source_record_id"), "monthly", "context", frozenset({"direct", "nested"}), ("gold_nem_unit_dispatch_5min", "gold_nem_scada_generation_5min")),
    SourceSubject("dualloc", "registration", "monthly", None, "Data_Archive/Wholesale_Electricity/MMSDM/{year}/MMSDM_{year}_{month}", "PUBLIC_ARCHIVE#DUALLOC#", ".zip", "PARTICIPANT_REGISTRATION", "DUALLOC", "1", "landing_nem_dualloc", (
        _f("EFFECTIVEDATE", "effective_at", "market_timestamp", "timestamp", True), _f("VERSIONNO", "source_version_no", "int", "long", True), _f("DUID", "duid", required=True), _f("GENSETID", "genset_id", required=True), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp")),
        ("duid", "effective_at", "source_version_no"), ("report_version", "source_version_no", "source_last_changed", "source_publication_at", "landed_at", "source_record_id"), "monthly", "context", frozenset({"direct", "nested"}), ("gold_nem_unit_dispatch_5min", "gold_nem_scada_generation_5min")),
    SourceSubject("genunits", "registration", "monthly", None, "Data_Archive/Wholesale_Electricity/MMSDM/{year}/MMSDM_{year}_{month}", "PUBLIC_ARCHIVE#GENUNITS#", ".zip", "PARTICIPANT_REGISTRATION", "GENUNITS", "3", "landing_nem_genunits", (
        _f("GENSETID", "genset_id", required=True), _f("STATIONID", "station_id"), _f("REGISTEREDCAPACITY", "registered_capacity_mw", "float", "double"), _f("MAXCAPACITY", "maximum_capacity_mw", "float", "double"),
        _f("GENSETTYPE", "genset_type"), _f("GENSETNAME", "genset_name"), _f("DISPATCHTYPE", "dispatch_type"), _f("CO2E_ENERGY_SOURCE", "fuel_type_raw"), _f("CO2E_EMISSIONS_FACTOR", "co2e_emissions_factor", "float", "double"), _f("LASTCHANGED", "source_last_changed", "market_timestamp", "timestamp"),
        _f("SETLOSSFACTOR", kind="float", spark="double"), _f("CDINDICATOR"), _f("AGCFLAG"), _f("SPINNINGFLAG"), _f("VOLTLEVEL"), _f("STARTTYPE"), _f("MKTGENERATORIND"), _f("NORMALSTATUS"), _f("CO2E_DATA_SOURCE"),
        _f("MINCAPACITY", kind="float", spark="double"), _f("REGISTEREDMINCAPACITY", kind="float", spark="double"), _f("MAXSTORAGECAPACITY", kind="float", spark="double")),
        ("genset_id",), ("report_version", "source_last_changed", "source_publication_at", "landed_at", "source_record_id"), "monthly", "context", frozenset({"direct", "nested"}), ("gold_nem_unit_dispatch_5min", "gold_nem_scada_generation_5min")),
)

GENERATION_APP_GOLD_TABLES = (
    "gold_nem_unit_dispatch_5min",
    "gold_nem_scada_generation_5min",
)
GENERATION_APP_SUBJECT_KEYS = frozenset(
    {"dispatch_unit_scada", "dudetail", "dualloc", "genunits"}
)
MARKET_CONTEXT_GOLD_TABLES = ("gold_nem_region_dispatch_5min",)
MARKET_CONTEXT_SUBJECT_KEYS = frozenset(
    {"dispatch_price", "dispatch_region_sum"}
)

_BY_KEY = {subject.key: subject for subject in APP_CRITICAL_SUBJECTS}
_BY_SECTION = {(subject.report_family, *subject.section_identity): subject for subject in APP_CRITICAL_SUBJECTS}


def get_subject_by_key(key: str) -> SourceSubject:
    return _BY_KEY[key]


def get_subject_by_section(report_family: str, group: str, name: str, version: str) -> SourceSubject | None:
    return _BY_SECTION.get((report_family, group, name, version))


def subjects_for_family(report_family: str) -> tuple[SourceSubject, ...]:
    return tuple(s for s in APP_CRITICAL_SUBJECTS if s.report_family == report_family)


def subjects_for_scope(scope: str) -> tuple[SourceSubject, ...]:
    return tuple(s for s in APP_CRITICAL_SUBJECTS if s.required_scope == scope)


def landing_tables(subjects: Iterable[SourceSubject] = APP_CRITICAL_SUBJECTS) -> tuple[str, ...]:
    return tuple(s.landing_table for s in subjects)
