from __future__ import annotations

import ast
import io
import stat
import zipfile
from pathlib import Path

from agentic_energy.nemweb.parser import parse_zip_bytes
from agentic_energy.nemweb.schema_drift import assess_schema_drift
from agentic_energy.nemweb.schemas import required_sections

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = ROOT.parent
PIPELINE = ROOT / "agentic_energy" / "nemweb" / "pipeline"

_HEADERS = {
    "bids": [
        "I,BID,BIDDAYOFFER_D,3,SETTLEMENTDATE,DUID,BIDTYPE,BIDSETTLEMENTDATE,OFFERDATE,VERSIONNO,PARTICIPANTID,DAILYENERGYCONSTRAINT,REBIDEXPLANATION,PRICEBAND1,PRICEBAND2,PRICEBAND3,PRICEBAND4,PRICEBAND5,PRICEBAND6,PRICEBAND7,PRICEBAND8,PRICEBAND9,PRICEBAND10,MINIMUMLOAD,T1,T2,T3,T4,NORMALSTATUS,LASTCHANGED,ENTRYTYPE,DIRECTION",
        "I,BID,BIDPEROFFER_D,4,SETTLEMENTDATE,DUID,BIDTYPE,BIDSETTLEMENTDATE,OFFERDATE,PERIODID,VERSIONNO,MAXAVAIL,FIXEDLOAD,ROCUP,ROCDOWN,ENABLEMENTMIN,ENABLEMENTMAX,LOWBREAKPOINT,HIGHBREAKPOINT,BANDAVAIL1,BANDAVAIL2,BANDAVAIL3,BANDAVAIL4,BANDAVAIL5,BANDAVAIL6,BANDAVAIL7,BANDAVAIL8,BANDAVAIL9,BANDAVAIL10,LASTCHANGED,PASAAVAILABILITY,INTERVAL_DATETIME,DIRECTION,ENERGYLIMIT,RECALL_PERIOD",
    ],
    "trading": [
        "I,TRADING,PRICE,3,SETTLEMENTDATE,RUNNO,REGIONID,PERIODID,RRP,EEP,INVALIDFLAG,LASTCHANGED,ROP,RAISE6SECRRP,RAISE6SECROP,RAISE60SECRRP,RAISE60SECROP,RAISE5MINRRP,RAISE5MINROP,RAISEREGRRP,RAISEREGROP,LOWER6SECRRP,LOWER6SECROP,LOWER60SECRRP,LOWER60SECROP,LOWER5MINRRP,LOWER5MINROP,LOWERREGRRP,LOWERREGROP,RAISE1SECRRP,RAISE1SECROP,LOWER1SECRRP,LOWER1SECROP,PRICE_STATUS",
    ],
    "settlement": [
        "I,SETTLEMENTS,FCASREGIONRECOVERY,6,SETTLEMENTDATE,VERSIONNO,BIDTYPE,REGIONID,PERIODID,GENERATORREGIONENERGY,CUSTOMERREGIONENERGY,REGIONRECOVERY,REGION_ACE_MWH,REGION_ASOE_MWH,REGIONRECOVERYAMOUNT_ACE,REGIONRECOVERYAMOUNT_ASOE,REGIONRECOVERYAMOUNT,LASTCHANGED",
        "I,SETTLEMENTS,IRSURPLUS,6,SETTLEMENTDATE,SETTLEMENTRUNNO,PERIODID,INTERCONNECTORID,REGIONID,MWFLOW,LOSSFACTOR,SURPLUSVALUE,LASTCHANGED,UNADJUSTED_IRSR,CSP_DEROGATION_AMOUNT",
    ],
}


def _header_zip(family: str, headers: list[str]) -> bytes:
    payload = "\n".join([f"C,NEMP.WORLD,{family.upper()},AEMO", *headers, "F,END OF MEMBER,0", ""])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo(f"PUBLIC_{family.upper()}_CONTRACT.CSV")
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, payload)
    return buffer.getvalue()


def _declared_datasets(path: Path, decorator_name: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == decorator_name):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    names.add(str(keyword.value.value))
    return names


def test_real_current_headers_are_registered_without_false_schema_drift() -> None:
    for family, headers in _HEADERS.items():
        parsed = parse_zip_bytes(_header_zip(family, headers), family)
        drift = assess_schema_drift(parsed)
        assert not drift.failed
        assert drift.warning_count == 0
        assert {finding.status for finding in drift.findings} == {"compatible"}


def test_context_natural_keys_and_revision_fields_are_explicit() -> None:
    assert required_sections("bids") == {
        ("BID", "BIDDAYOFFER_D", "3"),
        ("BID", "BIDPEROFFER_D", "4"),
    }
    assert required_sections("trading") == {("TRADING", "PRICE", "3")}
    assert required_sections("settlement") == {
        ("SETTLEMENTS", "FCASREGIONRECOVERY", "6"),
        ("SETTLEMENTS", "IRSURPLUS", "6"),
    }
    bids = (PIPELINE / "silver_bids.py").read_text()
    settlement = (PIPELINE / "silver_settlement.py").read_text()
    assert '_DAY_KEY = ("settlement_date", "duid", "bid_type", "direction")' in bids
    assert 'source_revision="source_version_no"' in bids
    assert 'source_revision="source_version_no"' in settlement
    assert 'source_revision="settlement_run_no"' in settlement


def test_context_medallion_datasets_use_modern_pipeline_apis() -> None:
    expected = {
        "bids": ({"bronze_nem_bid_day_offer", "bronze_nem_bid_period_offer"}, {"silver_nem_bid_day_offer", "silver_nem_bid_period_offer"}, {"gold_nem_bid_stack"}),
        "trading": ({"bronze_nem_trading_price"}, {"silver_nem_trading_price"}, {"gold_nem_trading_price"}),
        "settlement": ({"bronze_nem_settlement_fcas_recovery", "bronze_nem_settlement_irsurplus"}, {"silver_nem_settlement_fcas_recovery", "silver_nem_settlement_irsurplus"}, {"gold_nem_settlement_fcas_recovery", "gold_nem_interregional_settlement_surplus"}),
    }
    for domain, (bronze, silver, gold) in expected.items():
        assert bronze <= _declared_datasets(PIPELINE / f"bronze_{domain}.py", "table")
        assert silver == _declared_datasets(PIPELINE / f"silver_{domain}.py", "materialized_view")
        assert gold == _declared_datasets(PIPELINE / f"gold_{domain}.py", "materialized_view")
        combined = "".join((PIPELINE / f"{layer}_{domain}.py").read_text() for layer in ("bronze", "silver", "gold"))
        assert "dp.read(" not in combined
        assert "dlt.read" not in combined
        assert "LIVE." not in combined


def test_units_cadence_and_semantic_boundaries_are_in_table_comments() -> None:
    bids = (PIPELINE / "gold_bids.py").read_text()
    trading = (PIPELINE / "gold_trading.py").read_text()
    settlement = (PIPELINE / "gold_settlement.py").read_text()
    assert "AUD/MWh" in bids and "MW" in bids and '"source.cadence": "daily"' in bids
    assert "settlement price" in trading.lower() and "dispatch price" in trading.lower()
    assert "AUD" in settlement and "MWh" in settlement and '"flow.sign": "aemo_source"' in settlement


def test_market_notices_are_deliberately_omitted_not_half_wired() -> None:
    assert not any(PIPELINE.glob("*notices.py"))
    manifest = (ROOT / "DATA-CONTRACT.md").read_text()
    assert "Market notices are deliberately omitted in this slice" in manifest
    assert "unstructured plain-text notice" in manifest
    resource = (ROOT / "resources" / "nemweb.pipeline.yml").read_text()
    assert "plain-text source has a bounded, tested parser" in resource
