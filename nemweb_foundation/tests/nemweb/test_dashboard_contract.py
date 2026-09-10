from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
DASHBOARD = json.loads((ROOT / "dashboards/nemweb_overview.lvdash.json").read_text())
RESOURCE = yaml.safe_load((ROOT / "resources/nemweb_overview.dashboard.yml").read_text())
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("extract_dashboard_sql", SCRIPTS / "extract_dashboard_sql.py")
assert spec and spec.loader
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


def test_dashboard_resource_is_portable_stable_and_parameterised() -> None:
    dashboard = RESOURCE["resources"]["dashboards"]["nemweb_overview"]
    assert dashboard["file_path"] == "../dashboards/nemweb_overview.lvdash.json"
    assert dashboard["warehouse_id"] == "${var.warehouse_id}"
    assert dashboard["dataset_catalog"] == "${var.catalog}"
    assert dashboard["dataset_schema"] == "${var.schema}"
    assert dashboard["embed_credentials"] is False
    assert {item["level"] for item in dashboard["permissions"]} == {"CAN_READ", "CAN_MANAGE"}


def test_dashboard_datasets_are_single_portable_effective_queries() -> None:
    extracted = extractor.extract_dashboard_sql(ROOT / "dashboards/nemweb_overview.lvdash.json")
    assert {item["dataset"] for item in extracted} == {
        "ds_region",
        "ds_spikes",
        "ds_generation",
        "ds_constraints",
        "ds_interconnectors",
        "ds_t1_availability",
        "ds_freshness",
    }
    for item in extracted:
        assert len(item["sha256"]) == 64
        # Default catalog/schema are supplied by the dashboard resource.
        assert not re.search(r"\bFROM\s+[A-Za-z_][\w-]*\.[A-Za-z_]", item["sql"], re.I)
    by_name = {item["dataset"]: item["sql"].lower() for item in extracted}
    for name in (
        "ds_region",
        "ds_spikes",
        "ds_constraints",
        "ds_interconnectors",
        "ds_t1_availability",
    ):
        assert "is_effective_run = true" in by_name[name]
    assert "unit/facility actual output" in by_name["ds_freshness"]
    assert by_name["ds_freshness"].count("union all") == 4
    # Row-level datasets must be time-bounded. Unbounded row scans grow without
    # limit as history accumulates: ds_t1_availability exceeded the 25 MiB inline
    # statement result limit against real data on 2026-09-02. ds_freshness is
    # aggregate-only and needs no bound.
    for name in (
        "ds_region",
        "ds_spikes",
        "ds_generation",
        "ds_constraints",
        "ds_interconnectors",
        "ds_t1_availability",
    ):
        assert "interval_end >= timestampadd(day," in by_name[name], (
            f"dashboard dataset {name} must bound interval_end"
        )
    spikes = by_name["ds_spikes"]
    # The panel must show non-spiking intervals too, so a quiet window is
    # distinguishable from a broken pipeline. Filtering to is_price_spike would
    # make an empty table ambiguous.
    assert "where is_price_spike" not in spikes
    assert "is_price_spike = true" not in spikes
    # The threshold that fired and the freshness label must reach the panel, or an
    # operator cannot tell what was applied or whether it is current.
    for column in (
        "spike_threshold_aud_per_mwh",
        "spike_freshness_status",
        "price_status",
    ):
        assert column in spikes, column
    t1 = by_name["ds_t1_availability"]
    aest_day = "date(from_utc_timestamp(interval_end, 'australia/brisbane'))"
    assert t1.count(aest_day) == 2, (
        "T+1 market_day must use fixed AEST in both SELECT and GROUP BY; "
        "DATE(interval_end) depends on the warehouse session timezone"
    )


def test_dashboard_has_valid_pages_filters_layout_and_genie_link() -> None:
    pages = DASHBOARD["pages"]
    assert all(page["layoutVersion"] == "GRID_V1" for page in pages)
    assert {page["pageType"] for page in pages} == {
        "PAGE_TYPE_CANVAS",
        "PAGE_TYPE_GLOBAL_FILTERS",
    }
    filter_types = {
        layout["widget"]["spec"]["widgetType"]
        for page in pages
        if page["pageType"] == "PAGE_TYPE_GLOBAL_FILTERS"
        for layout in page["layout"]
    }
    assert filter_types == {"filter-date-range-picker", "filter-multi-select"}
    assert DASHBOARD["uiSettings"]["genieSpace"] == {
        "isEnabled": True,
        "overrideId": "${resources.genie_spaces.nemweb_analyst.id}",
        "enablementMode": "ENABLED",
    }
    assert "visualizationColors" in DASHBOARD["uiSettings"]["theme"]


def test_widget_versions_names_and_field_bindings_are_valid() -> None:
    expected_versions = {
        "counter": 2,
        "table": 2,
        "line": 3,
        "bar": 3,
        "filter-date-range-picker": 2,
        "filter-multi-select": 2,
    }
    for page in DASHBOARD["pages"]:
        for layout in page["layout"]:
            widget = layout["widget"]
            assert re.fullmatch(r"[A-Za-z0-9_-]+", widget["name"])
            assert 0 <= layout["position"]["x"] < 12
            assert layout["position"]["x"] + layout["position"]["width"] <= 12
            if "spec" not in widget:
                assert "multilineTextboxSpec" in widget
                continue
            kind = widget["spec"]["widgetType"]
            assert widget["spec"]["version"] == expected_versions[kind]
            assert widget["spec"]["frame"]["showTitle"] is True
            queries = {query["name"]: query["query"] for query in widget["queries"]}
            if kind.startswith("filter-"):
                for field in widget["spec"]["encodings"]["fields"]:
                    query = queries[field["queryName"]]
                    assert field["fieldName"] in {value["name"] for value in query["fields"]}
                continue
            query = queries["main_query"]
            available = {field["name"] for field in query["fields"]}
            encoded: list[str] = []
            for value in widget["spec"]["encodings"].values():
                if isinstance(value, dict) and "fieldName" in value:
                    encoded.append(value["fieldName"])
                elif isinstance(value, dict):
                    encoded.extend(field["fieldName"] for field in value.get("fields", []))
                elif isinstance(value, list):
                    encoded.extend(field["fieldName"] for field in value)
            assert set(encoded) <= available


def test_dashboard_discloses_freshness_and_t1_source_limitations() -> None:
    text = json.dumps(DASHBOARD).lower()
    for phrase in (
        "source-to-gold lag",
        "source publication",
        "gold publication",
        "daily t+1",
        "not dispatch target or availability",
        "aemo source sign",
        "marginalvalue <> 0",
        "interval-ending aest",
        # The spike rule is a reviewed decision and a configured level, so the
        # dashboard must state it rather than presenting a bare count.
        "strictly above the governed threshold",
        "not an aemo-published spike definition",
        "negative dispatch prices are valid and are never spikes",
    ):
        assert phrase in text, phrase
