"""Versioned schema registry for the NEMWEB reports in the governed path.

The registry contains only columns whose semantics are required by this
project.  Parsers retain and flag every additional observed column so schema
changes cannot be silently discarded.  Header versions are part of the lookup
key because NEMWEB may publish several section versions concurrently.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    name: str
    kind: str = "string"
    required: bool = False


@dataclass(frozen=True)
class SectionSchema:
    report_family: str
    group: str
    section: str
    version: str
    fields: tuple[Field, ...]

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.group, self.section, self.version)

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)

    @property
    def required_names(self) -> frozenset[str]:
        return frozenset(field.name for field in self.fields if field.required)

    @property
    def kinds(self) -> dict[str, str]:
        return {field.name: field.kind for field in self.fields}


def _f(name: str, kind: str = "string", required: bool = False) -> Field:
    return Field(name, kind, required)


SCHEMAS: tuple[SectionSchema, ...] = (
    SectionSchema("dispatchis", "DISPATCH", "PRICE", "5", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("RUNNO", "int", True),
        _f("REGIONID", required=True), _f("DISPATCHINTERVAL", "int"),
        _f("INTERVENTION", "int", True), _f("RRP", "float", True),
        _f("EEP", "float"), _f("ROP", "float"), _f("APCFLAG", "int"),
        _f("MARKETSUSPENDEDFLAG", "int"), _f("LASTCHANGED", "market_timestamp"),
    )),
    SectionSchema("dispatchis", "DISPATCH", "REGIONSUM", "9", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("RUNNO", "int", True),
        _f("REGIONID", required=True), _f("DISPATCHINTERVAL", "int"),
        _f("INTERVENTION", "int", True), _f("TOTALDEMAND", "float", True),
        _f("AVAILABLEGENERATION", "float"), _f("AVAILABLELOAD", "float"),
        _f("DEMANDFORECAST", "float"), _f("DISPATCHABLEGENERATION", "float"),
        _f("DISPATCHABLELOAD", "float"), _f("NETINTERCHANGE", "float"),
        _f("LASTCHANGED", "market_timestamp"),
    )),
    SectionSchema("dispatchis", "DISPATCH", "CONSTRAINT", "5", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("RUNNO", "int", True),
        _f("CONSTRAINTID", required=True), _f("DISPATCHINTERVAL", "int"),
        _f("INTERVENTION", "int", True), _f("RHS", "float"),
        _f("MARGINALVALUE", "float"), _f("VIOLATIONDEGREE", "float"),
        _f("LASTCHANGED", "market_timestamp"), _f("LHS", "float"),
    )),
    SectionSchema("dispatchis", "DISPATCH", "INTERCONNECTORRES", "3", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("RUNNO", "int", True),
        _f("INTERCONNECTORID", required=True), _f("DISPATCHINTERVAL", "int"),
        _f("INTERVENTION", "int", True), _f("METEREDMWFLOW", "float"),
        _f("MWFLOW", "float", True), _f("MWLOSSES", "float"),
        _f("MARGINALVALUE", "float"), _f("VIOLATIONDEGREE", "float"),
        _f("LASTCHANGED", "market_timestamp"), _f("EXPORTLIMIT", "float"),
        _f("IMPORTLIMIT", "float"), _f("MARGINALLOSS", "float"),
    )),
    SectionSchema("dispatch_scada", "DISPATCH", "UNIT_SCADA", "1", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("DUID", required=True),
        _f("SCADAVALUE", "float", True), _f("LASTCHANGED", "market_timestamp"),
    )),
    SectionSchema("next_day_dispatch", "DISPATCH", "UNIT_SOLUTION", "6", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("RUNNO", "int", True),
        _f("DUID", required=True), _f("TRADETYPE"), _f("DISPATCHINTERVAL", "int"),
        _f("INTERVENTION", "int", True), _f("CONNECTIONPOINTID"),
        _f("DISPATCHMODE", "int"), _f("AGCSTATUS", "int"),
        _f("INITIALMW", "float"), _f("TOTALCLEARED", "float", True),
        _f("RAMPDOWNRATE", "float"), _f("RAMPUPRATE", "float"),
        _f("LASTCHANGED", "market_timestamp"), _f("AVAILABILITY", "float", True),
        _f("UIGF", "float"), _f("MIN_AVAILABILITY", "float"),
    )),
    # Real AEMO MMSDM monthly registration contracts, verified against the
    # July 2026 SQLLoader archive. DUID-to-fuel requires all three tables:
    # DUDETAILSUMMARY -> DUALLOC -> GENUNITS.CO2E_ENERGY_SOURCE.
    SectionSchema("registration", "PARTICIPANT_REGISTRATION", "DUDETAILSUMMARY", "7", (
        _f("DUID", required=True), _f("START_DATE", "market_timestamp", True),
        _f("END_DATE", "market_timestamp"), _f("DISPATCHTYPE"),
        _f("CONNECTIONPOINTID"), _f("REGIONID", required=True), _f("STATIONID"),
        _f("PARTICIPANTID"), _f("LASTCHANGED", "market_timestamp"),
        _f("TRANSMISSIONLOSSFACTOR", "float"), _f("STARTTYPE"),
        _f("DISTRIBUTIONLOSSFACTOR", "float"), _f("MINIMUM_ENERGY_PRICE", "float"),
        _f("MAXIMUM_ENERGY_PRICE", "float"), _f("SCHEDULE_TYPE"),
        _f("MIN_RAMP_RATE_UP", "float"), _f("MIN_RAMP_RATE_DOWN", "float"),
        _f("MAX_RAMP_RATE_UP", "float"), _f("MAX_RAMP_RATE_DOWN", "float"),
        _f("IS_AGGREGATED"), _f("DISPATCHSUBTYPE"), _f("ADG_ID"),
        _f("LOAD_MINIMUM_ENERGY_PRICE", "float"), _f("LOAD_MAXIMUM_ENERGY_PRICE", "float"),
        _f("LOAD_MIN_RAMP_RATE_UP", "float"), _f("LOAD_MIN_RAMP_RATE_DOWN", "float"),
        _f("LOAD_MAX_RAMP_RATE_UP", "float"), _f("LOAD_MAX_RAMP_RATE_DOWN", "float"),
        _f("SECONDARY_TLF", "float"),
    )),
    SectionSchema("registration", "PARTICIPANT_REGISTRATION", "DUALLOC", "1", (
        _f("EFFECTIVEDATE", "market_timestamp", True), _f("VERSIONNO", "int", True),
        _f("DUID", required=True), _f("GENSETID", required=True),
        _f("LASTCHANGED", "market_timestamp"),
    )),
    SectionSchema("registration", "PARTICIPANT_REGISTRATION", "GENUNITS", "3", (
        _f("GENSETID", required=True), _f("STATIONID"), _f("SETLOSSFACTOR", "float"),
        _f("CDINDICATOR"), _f("AGCFLAG"), _f("SPINNINGFLAG"), _f("VOLTLEVEL"),
        _f("REGISTEREDCAPACITY", "float"), _f("DISPATCHTYPE"), _f("STARTTYPE"),
        _f("MKTGENERATORIND"), _f("NORMALSTATUS"), _f("MAXCAPACITY", "float"),
        _f("GENSETTYPE"), _f("GENSETNAME"), _f("LASTCHANGED", "market_timestamp"),
        _f("CO2E_EMISSIONS_FACTOR", "float"), _f("CO2E_ENERGY_SOURCE"),
        _f("CO2E_DATA_SOURCE"), _f("MINCAPACITY", "float"),
        _f("REGISTEREDMINCAPACITY", "float"), _f("MAXSTORAGECAPACITY", "float"),
    )),
    # Slower context contracts verified against public Current files on
    # 2026-09-02. VERSIONNO/SETTLEMENTRUNNO are report-specific correction
    # sequences and are intentionally retained separately from RUNNO.
    SectionSchema("bids", "BID", "BIDDAYOFFER_D", "3", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("DUID", required=True),
        _f("BIDTYPE", required=True), _f("BIDSETTLEMENTDATE", "market_timestamp"),
        _f("OFFERDATE", "market_timestamp"), _f("VERSIONNO", "int", True),
        _f("PARTICIPANTID"), _f("DAILYENERGYCONSTRAINT", "float"),
        _f("REBIDEXPLANATION"),
        *tuple(_f(f"PRICEBAND{i}", "float") for i in range(1, 11)),
        _f("MINIMUMLOAD", "float"), _f("LASTCHANGED", "market_timestamp"),
        _f("ENTRYTYPE"), _f("DIRECTION", required=True),
    )),
    SectionSchema("bids", "BID", "BIDPEROFFER_D", "4", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("DUID", required=True),
        _f("BIDTYPE", required=True), _f("BIDSETTLEMENTDATE", "market_timestamp"),
        _f("OFFERDATE", "market_timestamp"), _f("PERIODID", "int", True),
        _f("VERSIONNO", "int", True), _f("MAXAVAIL", "float"),
        _f("FIXEDLOAD", "float"), _f("ROCUP", "float"), _f("ROCDOWN", "float"),
        _f("ENABLEMENTMIN", "float"), _f("ENABLEMENTMAX", "float"),
        _f("LOWBREAKPOINT", "float"), _f("HIGHBREAKPOINT", "float"),
        *tuple(_f(f"BANDAVAIL{i}", "float") for i in range(1, 11)),
        _f("LASTCHANGED", "market_timestamp"), _f("PASAAVAILABILITY", "float"),
        _f("INTERVAL_DATETIME", "market_timestamp"), _f("DIRECTION", required=True),
        _f("ENERGYLIMIT", "float"), _f("RECALL_PERIOD", "int"),
    )),
    SectionSchema("trading", "TRADING", "PRICE", "3", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("RUNNO", "int", True),
        _f("REGIONID", required=True), _f("PERIODID", "int"),
        _f("RRP", "float", True), _f("EEP", "float"), _f("INVALIDFLAG"),
        _f("LASTCHANGED", "market_timestamp"), _f("ROP", "float"),
        _f("PRICE_STATUS"),
    )),
    SectionSchema("settlement", "SETTLEMENTS", "FCASREGIONRECOVERY", "6", (
        _f("SETTLEMENTDATE", "market_timestamp", True), _f("VERSIONNO", "int", True),
        _f("BIDTYPE", required=True), _f("REGIONID", required=True),
        _f("PERIODID", "int", True), _f("GENERATORREGIONENERGY", "float"),
        _f("CUSTOMERREGIONENERGY", "float"), _f("REGIONRECOVERY", "float"),
        _f("REGION_ACE_MWH", "float"), _f("REGION_ASOE_MWH", "float"),
        _f("REGIONRECOVERYAMOUNT_ACE", "float"),
        _f("REGIONRECOVERYAMOUNT_ASOE", "float"),
        _f("REGIONRECOVERYAMOUNT", "float"), _f("LASTCHANGED", "market_timestamp"),
    )),
    SectionSchema("settlement", "SETTLEMENTS", "IRSURPLUS", "6", (
        _f("SETTLEMENTDATE", "market_timestamp", True),
        _f("SETTLEMENTRUNNO", "int", True), _f("PERIODID", "int", True),
        _f("INTERCONNECTORID", required=True), _f("REGIONID", required=True),
        _f("MWFLOW", "float"), _f("LOSSFACTOR", "float"),
        _f("SURPLUSVALUE", "float"), _f("LASTCHANGED", "market_timestamp"),
        _f("UNADJUSTED_IRSR", "float"), _f("CSP_DEROGATION_AMOUNT", "float"),
    )),
)

_REGISTRY = {(schema.report_family, *schema.key): schema for schema in SCHEMAS}

# Header fingerprints are from the public Current samples inspected on
# 2026-09-02 and allow the parser to recognise the complete standard headers
# without treating their non-selected columns as novel drift.  Selected fields
# above remain the typed contract.  Any changed full header is compared by name
# and surfaced for review; the fingerprint is never used to accept missing keys.
_KNOWN_HEADER_SHA256 = {
    ("dispatchis", "DISPATCH", "PRICE", "5"): "935043b54c3c6dc59b951b4e6190c00e92f2a46aaf53fcf8274fb74596c3a7b4",
    ("dispatchis", "DISPATCH", "REGIONSUM", "9"): "1b643f4032ee55a749232b5d2d56f1072c317f94cf9d94c967ae8478b8b1ebbf",
    ("dispatchis", "DISPATCH", "CONSTRAINT", "5"): "b6256e8ef911dfc3cfc55b0f53d84cfd90b8a33f12de978b7cdd2147ffab11b4",
    ("dispatchis", "DISPATCH", "INTERCONNECTORRES", "3"): "63714be55c207b9ca1f014510c595e0c0b39bceef49bfcc5175d548698a43c4f",
    ("dispatch_scada", "DISPATCH", "UNIT_SCADA", "1"): "00eca748bb51e90a36e304e58585278abc43af19e0d55d1d01e8fc0dcf37fa98",
    ("next_day_dispatch", "DISPATCH", "UNIT_SOLUTION", "6"): "08a279e4a6fdea957ed877e4d0f994a1d58aad43f3b14a69f772c292ae1e0e1f",
    ("bids", "BID", "BIDDAYOFFER_D", "3"): "881afe92832f6180a1a3f3c2d8876830d9210a283efd9d75221608770d337e65",
    ("bids", "BID", "BIDPEROFFER_D", "4"): "b4ea5d2f0c4e5e7ede9fd2e56a1056844d8c9079e544a95aa7092986455f1512",
    ("trading", "TRADING", "PRICE", "3"): "ef8beb03a4590581cc65472eaad692f4726a7bb78adee2e1de7fde586284559d",
    ("settlement", "SETTLEMENTS", "FCASREGIONRECOVERY", "6"): "4584848464fa9e3e9d5a3c601a7752823639458d2d59170524b5dfc514054c07",
    ("settlement", "SETTLEMENTS", "IRSURPLUS", "6"): "815638f120ad14dc88260703f8ab7ffdc5202d6b18a8be7d1cde531192f4db45",
}


def is_known_complete_header(
    report_family: str,
    group: str,
    section: str,
    version: str,
    columns: tuple[str, ...],
) -> bool:
    expected = _KNOWN_HEADER_SHA256.get((report_family, group, section, version))
    if expected is None:
        return False
    actual = hashlib.sha256("\x1f".join(columns).encode("utf-8")).hexdigest()
    return actual == expected


def get_schema(
    report_family: str, group: str, section: str, version: str
) -> SectionSchema | None:
    """Return the exact versioned schema or ``None`` for an unknown section."""

    return _REGISTRY.get((report_family, group, section, version))


def schemas_for_family(report_family: str) -> tuple[SectionSchema, ...]:
    return tuple(schema for schema in SCHEMAS if schema.report_family == report_family)


def required_sections(report_family: str) -> frozenset[tuple[str, str, str]]:
    return frozenset(schema.key for schema in schemas_for_family(report_family))


def registered_families() -> frozenset[str]:
    return frozenset(schema.report_family for schema in SCHEMAS)
