"""Common utilities for data extraction, transformation, and validation.

This module provides reusable components:
- ColumnMapping: Flexible field mapping and renaming
- ColumnTransformer: Apply transformations to columns
- TypeCoercer: Type conversion with error handling
- RemoteArchiveFetcher: HTTP/ZIP handling with validation
- RateLimiter: Request rate limiting
"""

from __future__ import annotations

import csv
import math
import re
import time
from collections import deque
from io import BytesIO, StringIO
from typing import Any, Callable, Optional
from urllib.parse import urljoin, urlparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import ZipFile

from .base import ExtractionError, TransformationError


# HTTP/Archive constants
MAX_RESPONSE_BYTES = 50_000_000
MAX_ARCHIVE_MEMBER_BYTES = 50_000_000


class ColumnMapping:
    """Flexible column mapping from source to canonical names.

    Supports:
    - Simple rename: {"SOURCE_FIELD": "canonical_field"}
    - Computed columns: {"computed": lambda row: row["a"] + row["b"]}
    - Conditional mapping: {"field": ("SOURCE_FIELD", lambda v: v if v else None)}
    """

    def __init__(self, mapping: dict[str, Any]):
        """Initialize column mapping.

        Args:
            mapping: Dict of canonical_field -> source_field or callable
        """
        self.mapping = mapping

    def apply(self, row: dict) -> dict:
        """Apply mapping to a row.

        Args:
            row: Source row dict

        Returns:
            Mapped row dict with canonical field names

        Raises:
            TransformationError: If mapping fails
        """
        result = {}
        for canonical_field, source_spec in self.mapping.items():
            try:
                if isinstance(source_spec, str):
                    # Simple rename
                    result[canonical_field] = row.get(source_spec)
                elif callable(source_spec):
                    # Computed column
                    result[canonical_field] = source_spec(row)
                elif isinstance(source_spec, tuple) and len(source_spec) == 2:
                    # Conditional mapping: (source_field, transformer)
                    source_field, transformer = source_spec
                    value = row.get(source_field)
                    result[canonical_field] = transformer(value) if value is not None else None
                else:
                    raise TransformationError(
                        f"Invalid mapping spec for {canonical_field}: {source_spec}",
                        details={"canonical_field": canonical_field, "spec": str(source_spec)},
                    )
            except TransformationError:
                raise
            except Exception as exc:
                raise TransformationError(
                    f"Failed to map {canonical_field}: {exc}",
                    details={"canonical_field": canonical_field, "exception": str(exc)},
                ) from exc
        return result


class TypeCoercer:
    """Type conversion with error handling and validation.

    Supports: string, int, float, bool, datetime
    """

    COERCERS = {
        "string": lambda v: str(v) if v is not None else None,
        "int": lambda v: int(v) if v is not None else None,
        "float": lambda v: float(v) if v is not None else None,
        "bool": lambda v: v.lower() in ("true", "1", "yes") if isinstance(v, str) else bool(v),
    }

    @classmethod
    def coerce(cls, value: Any, target_type: str) -> Any:
        """Coerce value to target type.

        Args:
            value: Value to coerce
            target_type: Target type name (string, int, float, bool)

        Returns:
            Coerced value or None if value is None

        Raises:
            TransformationError: If coercion fails
        """
        if value is None or value == "":
            return None

        if target_type not in cls.COERCERS:
            raise TransformationError(
                f"Unknown type: {target_type}",
                details={"target_type": target_type},
            )

        try:
            coercer = cls.COERCERS[target_type]
            return coercer(value)
        except (ValueError, TypeError, AttributeError) as exc:
            raise TransformationError(
                f"Failed to coerce {value!r} to {target_type}: {exc}",
                details={"value": str(value), "target_type": target_type},
            ) from exc


class ColumnTransformer:
    """Apply transformations to columns.

    Supports:
    - Type coercion
    - Custom transformation functions
    - Conditional transformations
    - Null handling
    """

    def __init__(self, transformations: dict[str, Any]):
        """Initialize column transformer.

        Args:
            transformations: Dict of field_name -> transformation_spec
                - str: Type name for coercion (e.g., "float", "int")
                - callable: Custom transformation function
                - dict: Advanced spec with type, transformer, null_handling
        """
        self.transformations = transformations

    def apply(self, row: dict) -> dict:
        """Apply transformations to a row.

        Args:
            row: Row dict to transform

        Returns:
            Transformed row dict

        Raises:
            TransformationError: If transformation fails
        """
        result = row.copy()
        for field, spec in self.transformations.items():
            if field not in result:
                continue

            try:
                value = result[field]

                if isinstance(spec, str):
                    # Type coercion
                    result[field] = TypeCoercer.coerce(value, spec)
                elif callable(spec):
                    # Custom transformation
                    result[field] = spec(value)
                elif isinstance(spec, dict):
                    # Advanced spec
                    if value is None and spec.get("null_handling") == "keep":
                        continue
                    if "type" in spec:
                        result[field] = TypeCoercer.coerce(value, spec["type"])
                    if "transformer" in spec:
                        result[field] = spec["transformer"](result[field])
                else:
                    raise TransformationError(
                        f"Invalid transformation spec for {field}: {spec}",
                        details={"field": field, "spec": str(spec)},
                    )
            except TransformationError:
                raise
            except Exception as exc:
                raise TransformationError(
                    f"Transformation failed for field {field}: {exc}",
                    details={"field": field, "value": str(value)},
                ) from exc

        return result


class RateLimiter:
    """Rate limiter for remote requests.

    Tracks request timestamps and enforces max requests per minute.
    """

    def __init__(self, max_requests_per_minute: int = 10):
        """Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests allowed per minute
        """
        self.max_requests = max_requests_per_minute
        self.requests = deque()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Remove requests older than 1 minute
        while self.requests and self.requests[0] < now - 60:
            self.requests.popleft()

        # Check if limit exceeded
        if len(self.requests) >= self.max_requests:
            wait_time = 60 - (now - self.requests[0])
            if wait_time > 0:
                time.sleep(wait_time)

        self.requests.append(time.time())


class _NoRedirect(HTTPRedirectHandler):
    """HTTP handler that rejects redirects."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class RemoteArchiveFetcher:
    """Fetch and validate remote archives (ZIP files).

    Features:
    - Host validation against allowlist
    - No-redirect enforcement
    - Size validation
    - Archive member extraction
    - Rate limiting
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """Initialize fetcher.

        Args:
            rate_limiter: Optional RateLimiter instance
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self._opener = build_opener(_NoRedirect)

    def _request(self, url: str, allowed_host: str, max_bytes: int = MAX_RESPONSE_BYTES) -> bytes:
        """Make HTTP request with validation.

        Args:
            url: URL to fetch
            allowed_host: Expected hostname (must match)
            max_bytes: Maximum response size

        Returns:
            Response bytes

        Raises:
            ExtractionError: If request fails or validation fails
        """
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != allowed_host:
            raise ExtractionError(
                "HOST_NOT_ALLOWED",
                details={"url": url, "expected_host": allowed_host, "actual_host": parsed.hostname},
            )

        self.rate_limiter.wait_if_needed()

        try:
            response = self._opener.open(
                Request(url, headers={"User-Agent": "agentic-energy-etl/0.1"}),
                timeout=60,
            )
        except HTTPError as exc:
            if 300 <= exc.code < 400:
                raise ExtractionError("REDIRECT_NOT_ALLOWED", details={"code": exc.code}) from exc
            raise ExtractionError(f"HTTP_ERROR_{exc.code}", details={"url": url}) from exc

        with response:
            payload = response.read(max_bytes + 1)

        if len(payload) > max_bytes:
            raise ExtractionError(
                "RESPONSE_TOO_LARGE",
                details={"size_bytes": len(payload), "max_bytes": max_bytes},
            )

        return payload

    def fetch_latest_archive(self, source: dict) -> tuple[str, bytes]:
        """Fetch latest archive matching source configuration.

        Args:
            source: Source metadata dict with url_or_fixture_path, allowed_hosts, file_name_regex

        Returns:
            Tuple of (archive_url, archive_bytes)

        Raises:
            ExtractionError: If fetch fails
        """
        listing_url = source.get("url_or_fixture_path")
        allowed_hosts = source.get("allowed_hosts", [])
        file_regex = source.get("file_name_regex", r".*\.zip$")

        if not listing_url or not allowed_hosts:
            raise ExtractionError("INVALID_SOURCE_CONFIG", details={"source_id": source.get("source_id")})

        parsed_url = urlparse(listing_url)
        allowed_host = parsed_url.hostname

        if not allowed_host or allowed_host not in allowed_hosts:
            raise ExtractionError(
                "LISTING_HOST_NOT_ALLOWED",
                details={"host": allowed_host, "allowed": allowed_hosts},
            )

        # Fetch HTML listing
        html = self._request(listing_url, allowed_host=allowed_host).decode("latin-1")

        # Extract archive links
        pattern = re.compile(file_regex, re.IGNORECASE)
        hrefs = re.findall(r'href=["\']([^"\']+\.zip)', html, re.IGNORECASE)
        candidates = sorted({href for href in hrefs if pattern.search(href)})

        if not candidates:
            raise ExtractionError("NO_MATCHING_ARCHIVE", details={"pattern": file_regex})

        # Use latest archive
        relative = candidates[-1]
        url = urljoin(listing_url, relative)

        # Validate archive URL
        parsed_archive = urlparse(url)
        if parsed_archive.hostname != allowed_host:
            raise ExtractionError(
                "ARCHIVE_HOST_NOT_ALLOWED",
                details={"host": parsed_archive.hostname, "expected": allowed_host},
            )

        # Download archive
        archive_bytes = self._request(url, allowed_host=allowed_host)
        return url, archive_bytes

    def extract_csv_from_zip(self, archive_bytes: bytes, csv_pattern: Optional[str] = None) -> str:
        """Extract CSV content from ZIP archive.

        Args:
            archive_bytes: ZIP archive bytes
            csv_pattern: Optional regex pattern to match CSV filename

        Returns:
            CSV content as string

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            with ZipFile(BytesIO(archive_bytes)) as zf:
                # Find CSV file
                csv_files = [n for n in zf.namelist() if n.upper().endswith((".CSV", ".CSV.TXT"))]

                if csv_pattern:
                    pattern = re.compile(csv_pattern, re.IGNORECASE)
                    csv_files = [n for n in csv_files if pattern.search(n)]

                if not csv_files:
                    raise ExtractionError("NO_CSV_IN_ARCHIVE", details={"archive_files": zf.namelist()})

                if len(csv_files) > 1:
                    raise ExtractionError(
                        "MULTIPLE_CSV_IN_ARCHIVE",
                        details={"csv_files": csv_files},
                    )

                csv_name = csv_files[0]
                member = zf.getinfo(csv_name)

                if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    raise ExtractionError(
                        "CSV_TOO_LARGE",
                        details={"size_bytes": member.file_size, "max_bytes": MAX_ARCHIVE_MEMBER_BYTES},
                    )

                return zf.read(member).decode("utf-8")
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(f"Failed to extract CSV from ZIP: {exc}") from exc


class CSVParser:
    """Parse CSV content into rows.

    Features:
    - Flexible delimiter and encoding
    - Header validation
    - Row filtering
    - Error tracking
    """

    def __init__(
        self,
        delimiter: str = ",",
        encoding: str = "utf-8",
        skip_rows: int = 0,
        skip_footer: int = 0,
    ):
        """Initialize CSV parser.

        Args:
            delimiter: CSV delimiter character
            encoding: File encoding
            skip_rows: Number of rows to skip from start
            skip_footer: Number of rows to skip from end
        """
        self.delimiter = delimiter
        self.encoding = encoding
        self.skip_rows = skip_rows
        self.skip_footer = skip_footer

    def parse(self, csv_content: str) -> list[dict]:
        """Parse CSV content into rows.

        Args:
            csv_content: CSV content as string

        Returns:
            List of row dicts

        Raises:
            ExtractionError: If parsing fails
        """
        try:
            # Skip rows from beginning
            lines = csv_content.split('\n')
            if self.skip_rows > 0:
                lines = lines[self.skip_rows:]
            
            # Skip rows from end
            if self.skip_footer > 0:
                lines = lines[:-self.skip_footer]
            
            csv_content = '\n'.join(lines)
            reader = csv.DictReader(StringIO(csv_content), delimiter=self.delimiter)
            rows = list(reader)
            return rows
        except Exception as exc:
            raise ExtractionError(f"CSV parsing failed: {exc}") from exc
