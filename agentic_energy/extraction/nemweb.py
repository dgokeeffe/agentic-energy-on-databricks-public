"""NEMWEB-specific extractors for DISPATCHIS, PREDISPATCHIS, and ROOFTOP_PV.

This module implements extractors for various NEMWEB report types:
- DispatchISExtractor: 5-minute dispatch data
- PredispatchISExtractor: 30-minute predispatch data
- RooftopPVExtractor: Rooftop solar generation
- DemandSideProgramsExtractor: DSP data

Each extractor handles:
- Archive fetching and validation
- CSV parsing with multi-record types
- Field mapping to canonical form
- Type coercion and validation
"""

from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any, Optional

from .base import DataExtractor, DataTransformer, DataValidator, ValidationResult
from .common import ColumnMapping, ColumnTransformer, RemoteArchiveFetcher, CSVParser


class NEMWEBExtractor(DataExtractor):
    """Base class for NEMWEB extractors.

    Handles common NEMWEB operations:
    - Archive fetching
    - CSV extraction from ZIP
    - Multi-record type parsing
    """

    def __init__(self, source: dict):
        """Initialize NEMWEB extractor.

        Args:
            source: Source metadata dict
        """
        super().__init__(source)
        self.fetcher = RemoteArchiveFetcher()

    def extract(self) -> bytes:
        """Fetch latest NEMWEB archive.

        Returns:
            Archive bytes

        Raises:
            ExtractionError: If fetch fails
        """
        url, archive_bytes = self.fetcher.fetch_latest_archive(self.source)
        return archive_bytes

    def parse(self, raw_data: bytes, source_file: str) -> list[dict]:
        """Parse NEMWEB archive into rows.

        Args:
            raw_data: Archive bytes
            source_file: Source file identifier

        Returns:
            List of parsed rows

        Raises:
            ExtractionError: If parsing fails
        """
        # Extract CSV from ZIP
        csv_content = self.fetcher.extract_csv_from_zip(raw_data)
        return self._parse_csv(csv_content, source_file)

    def _parse_csv(self, csv_content: str, source_file: str) -> list[dict]:
        """Parse CSV content. Override in subclasses for specific formats.

        Args:
            csv_content: CSV content as string
            source_file: Source file identifier

        Returns:
            List of parsed rows
        """
        parser = CSVParser()
        rows = parser.parse(csv_content)
        for row in rows:
            row["source_file"] = source_file
        return rows


class DispatchISExtractor(NEMWEBExtractor):
    """Extractor for AEMO DISPATCHIS reports.

    DISPATCHIS is a multi-record CSV with:
    - I (header) records: Define columns for each report/version
    - D (data) records: Contain PRICE or REGIONSUM records
    - C (comment) records: Ignored

    We join PRICE and REGIONSUM records on (settlement, region, intervention)
    to produce one row per region/interval with demand and price.
    """

    def _parse_csv(self, csv_content: str, source_file: str) -> list[dict]:
        """Parse DISPATCHIS CSV with multi-record format.

        Args:
            csv_content: CSV content as string
            source_file: Source file identifier

        Returns:
            List of joined rows (one per region/interval)
        """
        headers: dict[tuple[str, str], list[str]] = {}
        prices: dict[tuple[str, str, str], dict] = {}
        demands: dict[tuple[str, str, str], dict] = {}

        for line_number, row in enumerate(csv.reader(StringIO(csv_content)), 1):
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

        # Join PRICE and REGIONSUM records
        rows = []
        for key in sorted(prices.keys() & demands.keys()):
            settlement, region, intervention = key
            price = prices[key]
            demand = demands[key]

            rows.append(
                {
                    "region": region,
                    "interval_datetime": self._normalize_timestamp(settlement),
                    "demand_mw": self._parse_number(demand.get("TOTALDEMAND")),
                    "price_per_mwh": self._parse_number(price.get("RRP")),
                    "ingestion_sequence": max(
                        int(price.get("DISPATCHINTERVAL") or 0),
                        int(demand.get("DISPATCHINTERVAL") or 0),
                    ),
                    "source_record_types": ["PRICE", "REGIONSUM"],
                    "source_line_numbers": [price["_line_number"], demand["_line_number"]],
                    "source_file": source_file,
                }
            )

        return rows

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        """Normalize NEMWEB timestamp to ISO format.

        NEMWEB uses YYYY/MM/DD HH:MM:SS; we convert to ISO local wall-clock.

        Args:
            value: NEMWEB timestamp string

        Returns:
            ISO format timestamp
        """
        return value.replace("/", "-").replace(" ", "T", 1)

    @staticmethod
    def _parse_number(value: str | None) -> float | None:
        """Parse number, returning None for empty/null values.

        Args:
            value: String value to parse

        Returns:
            Float or None
        """
        if value is None or value == "":
            return None
        return float(value)


class PredispatchISExtractor(DispatchISExtractor):
    """Extractor for AEMO PREDISPATCHIS reports.

    Uses same multi-record format as DISPATCHIS but with 30-minute intervals.
    """

    pass


class RooftopPVExtractor(NEMWEBExtractor):
    """Extractor for AEMO Rooftop PV reports.

    Rooftop PV is a simpler single-record CSV format with:
    - SETTLEMENTDATE: Interval timestamp
    - REGIONID: NEM region
    - TOTAL_ROOFTOP_PV: Generation in MW
    """

    def _parse_csv(self, csv_content: str, source_file: str) -> list[dict]:
        """Parse Rooftop PV CSV.

        Args:
            csv_content: CSV content as string
            source_file: Source file identifier

        Returns:
            List of parsed rows
        """
        parser = CSVParser()
        raw_rows = parser.parse(csv_content)

        rows = []
        for row_num, raw_row in enumerate(raw_rows, 1):
            rows.append(
                {
                    "region": raw_row.get("REGIONID"),
                    "interval_datetime": self._normalize_timestamp(raw_row.get("SETTLEMENTDATE", "")),
                    "generation_mw": self._parse_number(raw_row.get("TOTAL_ROOFTOP_PV")),
                    "source_file": source_file,
                    "source_line_number": row_num,
                }
            )

        return rows

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        """Normalize NEMWEB timestamp to ISO format."""
        return value.replace("/", "-").replace(" ", "T", 1)

    @staticmethod
    def _parse_number(value: str | None) -> float | None:
        """Parse number, returning None for empty/null values."""
        if value is None or value == "":
            return None
        return float(value)


class DemandSideProgramsExtractor(NEMWEBExtractor):
    """Extractor for AEMO Demand Side Programs (DSP) reports.

    DSP is a single-record CSV format with:
    - SETTLEMENTDATE: Interval timestamp
    - REGIONID: NEM region
    - DSP_MW: DSP dispatch in MW
    """

    def _parse_csv(self, csv_content: str, source_file: str) -> list[dict]:
        """Parse DSP CSV.

        Args:
            csv_content: CSV content as string
            source_file: Source file identifier

        Returns:
            List of parsed rows
        """
        parser = CSVParser()
        raw_rows = parser.parse(csv_content)

        rows = []
        for row_num, raw_row in enumerate(raw_rows, 1):
            rows.append(
                {
                    "region": raw_row.get("REGIONID"),
                    "interval_datetime": self._normalize_timestamp(raw_row.get("SETTLEMENTDATE", "")),
                    "dsp_mw": self._parse_number(raw_row.get("DSP_MW")),
                    "source_file": source_file,
                    "source_line_number": row_num,
                }
            )

        return rows

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        """Normalize NEMWEB timestamp to ISO format."""
        return value.replace("/", "-").replace(" ", "T", 1)

    @staticmethod
    def _parse_number(value: str | None) -> float | None:
        """Parse number, returning None for empty/null values."""
        if value is None or value == "":
            return None
        return float(value)


class NEMWEBTransformer(DataTransformer):
    """Base transformer for NEMWEB data.

    Applies column mapping and type coercion based on metadata.
    """

    def __init__(self, source: dict):
        """Initialize transformer.

        Args:
            source: Source metadata dict with field_mapping and field_types
        """
        super().__init__(source)
        self.column_mapping = ColumnMapping(source.get("field_mapping", {}))
        self.column_transformer = ColumnTransformer(source.get("field_types", {}))

    def transform(self, rows: list[dict]) -> list[dict]:
        """Transform rows using column mapping and type coercion.

        Args:
            rows: List of extracted rows

        Returns:
            List of transformed rows
        """
        transformed = []
        for row in rows:
            # Apply column mapping
            mapped = self.column_mapping.apply(row)
            # Apply type coercion
            transformed_row = self.column_transformer.apply(mapped)
            transformed.append(transformed_row)
        return transformed


class NEMWEBValidator(DataValidator):
    """Base validator for NEMWEB data.

    Validates rows against quality_checks defined in metadata.
    """

    def validate(self, rows: list[dict]) -> ValidationResult:
        """Validate rows against quality checks.

        Args:
            rows: List of rows to validate

        Returns:
            ValidationResult with valid/invalid rows
        """
        from ..pipeline import _evaluate_quality_check

        valid_rows = []
        invalid_rows = []
        quality_checks = self.source.get("quality_checks", [])

        for row_num, row in enumerate(rows, 1):
            reasons = []

            # Apply quality checks
            for check in quality_checks:
                if not _evaluate_quality_check(check, row):
                    reasons.append(f"QUALITY_CHECK_FAILED:{check}")

            if reasons:
                invalid_rows.append(
                    {
                        "row": row,
                        "row_number": row_num,
                        "reasons": reasons,
                    }
                )
            else:
                valid_rows.append(row)

        return ValidationResult(
            source_id=self.source_id,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            validation_summary={
                "total_rows": len(rows),
                "valid_rows": len(valid_rows),
                "invalid_rows": len(invalid_rows),
                "pass_rate": len(valid_rows) / len(rows) if rows else 1.0,
            },
        )


# Extractor registry
NEMWEB_EXTRACTORS = {
    "aemo_dispatchis": DispatchISExtractor,
    "aemo_dispatchis_live": DispatchISExtractor,
    "aemo_predispatchis": PredispatchISExtractor,
    "aemo_predispatchis_live": PredispatchISExtractor,
    "aemo_rooftop_pv": RooftopPVExtractor,
    "aemo_rooftop_pv_live": RooftopPVExtractor,
    "aemo_dsp": DemandSideProgramsExtractor,
    "aemo_dsp_live": DemandSideProgramsExtractor,
}


def get_nemweb_extractor(source: dict) -> NEMWEBExtractor:
    """Get appropriate NEMWEB extractor for source.

    Args:
        source: Source metadata dict

    Returns:
        Appropriate extractor instance

    Raises:
        ValueError: If source type not supported
    """
    source_id = source.get("source_id")
    extractor_class = NEMWEB_EXTRACTORS.get(source_id)

    if not extractor_class:
        raise ValueError(f"Unknown NEMWEB source: {source_id}")

    return extractor_class(source)
