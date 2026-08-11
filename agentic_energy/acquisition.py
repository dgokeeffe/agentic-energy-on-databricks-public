"""Metadata-selected live acquisition adapters.

The live NEMWEB adapter deliberately stops at a small, governed canonical
record shape. It does not expose arbitrary remote columns to Silver; the raw
retrieval identity and selected source records remain in Bronze lineage.
"""
from __future__ import annotations

import csv
from io import BytesIO, StringIO
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import ZipFile


MAX_RESPONSE_BYTES = 50_000_000
MAX_ARCHIVE_MEMBER_BYTES = 50_000_000


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirect)


def _request(url: str, *, allowed_host: str, max_bytes: int = MAX_RESPONSE_BYTES) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != allowed_host:
        raise ValueError("LIVE_SOURCE_HOST_NOT_ALLOWED")
    try:
        response = _NO_REDIRECT_OPENER.open(  # noqa: S310 - URL is checked against metadata allowlist
            Request(url, headers={"User-Agent": "agentic-energy-workshop/0.1"}),
            timeout=60,
        )
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            raise RuntimeError("LIVE_SOURCE_REDIRECT_NOT_ALLOWED") from exc
        raise
    with response:
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise RuntimeError("NEMWEB_RESPONSE_TOO_LARGE")
    return payload


def _validate_remote_url(source: dict) -> str:
    url = source["url_or_fixture_path"]
    parsed = urlparse(url)
    allowed_hosts = set(source.get("allowed_hosts", []))
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname not in allowed_hosts:
        raise ValueError("LIVE_SOURCE_HOST_NOT_ALLOWED")
    return url


def _latest_archive(source: dict) -> tuple[str, bytes]:
    listing_url = _validate_remote_url(source)
    allowed_host = urlparse(listing_url).hostname
    assert allowed_host is not None
    html = _request(listing_url, allowed_host=allowed_host).decode("latin-1")
    pattern = re.compile(source.get("file_name_regex", r"PUBLIC_DISPATCHIS_.*\.zip$"), re.IGNORECASE)
    hrefs = re.findall(r"href=[\"']([^\"']+\.zip)[\"']", html, flags=re.IGNORECASE)
    candidates = sorted({href for href in hrefs if pattern.search(href)})
    if not candidates:
        raise RuntimeError("NEMWEB_NO_MATCHING_ARCHIVE")
    relative = candidates[-1]
    url = urljoin(listing_url, relative)
    if urlparse(url).hostname != urlparse(listing_url).hostname:
        raise ValueError("NEMWEB_ARCHIVE_HOST_NOT_ALLOWED")
    parsed_archive = urlparse(url)
    if parsed_archive.scheme != "https" or parsed_archive.hostname != allowed_host:
        raise ValueError("NEMWEB_ARCHIVE_HOST_NOT_ALLOWED")
    return url, _request(url, allowed_host=allowed_host)


def _parse_number(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _timestamp(value: str) -> str:
    # NEMWEB uses YYYY/MM/DD HH:MM:SS; the rest of the pipeline accepts ISO
    # local wall-clock values and applies the declared source timezone.
    return value.replace("/", "-").replace(" ", "T", 1)


def parse_dispatchis_zip(payload: bytes, source_file: str) -> list[dict]:
    """Parse a NEMWEB DISPATCHIS archive into region demand/price rows.

    DISPATCHIS is a multi-record CSV. Header rows (I) define columns for each
    report/version and data rows (D) carry either PRICE or REGIONSUM records.
    We join those two records on settlement timestamp, region, and intervention
    so the canonical Silver input has one row per region/interval.
    """
    headers: dict[tuple[str, str], list[str]] = {}
    prices: dict[tuple[str, str, str], dict] = {}
    demands: dict[tuple[str, str, str], dict] = {}
    with ZipFile(BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.upper().endswith((".CSV", ".CSV.TXT"))]
        if not members:
            raise RuntimeError("NEMWEB_ARCHIVE_HAS_NO_CSV")
        member = archive.getinfo(members[0])
        if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
            raise RuntimeError("NEMWEB_ARCHIVE_MEMBER_TOO_LARGE")
        text = archive.read(member).decode("latin-1")
    for line_number, row in enumerate(csv.reader(StringIO(text)), 1):
        if len(row) < 5 or row[0] == "C":
            continue
        record_type, report, version = row[0], row[2], row[3]
        key = (report, version)
        if record_type == "I":
            headers[key] = row[4:]
            continue
        if record_type != "D" or key not in headers:
            continue
        values = dict(zip(headers[key], row[4:]))
        if report not in {"PRICE", "REGIONSUM"}:
            continue
        settlement = values.get("SETTLEMENTDATE")
        region = values.get("REGIONID")
        intervention = values.get("INTERVENTION", "0")
        if not settlement or not region:
            continue
        record_key = (settlement, region, intervention)
        values["_line_number"] = line_number
        if report == "PRICE" and values.get("RRP") not in (None, ""):
            prices[record_key] = values
        elif report == "REGIONSUM" and values.get("TOTALDEMAND") not in (None, ""):
            demands[record_key] = values

    rows = []
    for key in sorted(prices.keys() & demands.keys()):
        settlement, region, intervention = key
        price = prices[key]
        demand = demands[key]
        rows.append(
            {
                "region": region,
                "interval_datetime": _timestamp(settlement),
                "demand_mw": _parse_number(demand.get("TOTALDEMAND")),
                "price_per_mwh": _parse_number(price.get("RRP")),
                "ingestion_sequence": max(int(price.get("DISPATCHINTERVAL") or 0), int(demand.get("DISPATCHINTERVAL") or 0)),
                "source_record_types": ["PRICE", "REGIONSUM"],
                "source_line_numbers": [price["_line_number"], demand["_line_number"]],
                "source_file": source_file,
            }
        )
    if not rows:
        raise RuntimeError("NEMWEB_DISPATCHIS_NO_REGION_MARKET_ROWS")
    return rows


def acquire_live_dispatchis(source: dict) -> tuple[list[dict], str]:
    source_file, payload = _latest_archive(source)
    return parse_dispatchis_zip(payload, source_file), source_file
