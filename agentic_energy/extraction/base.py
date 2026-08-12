"""Base classes and interfaces for data extraction, transformation, and validation.

This module defines the core abstractions for the ETL framework:
- DataExtractor: Fetch raw data from sources
- DataTransformer: Transform raw data to canonical form
- DataValidator: Validate data against rules and schemas
- Error types: ExtractionError, TransformationError, ValidationError
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from dataclasses import dataclass
from datetime import datetime, timezone

T = TypeVar("T")
U = TypeVar("U")

UTC = timezone.utc


class ExtractionError(Exception):
    """Base exception for data extraction errors."""

    def __init__(self, message: str, source_id: str | None = None, details: dict | None = None):
        self.message = message
        self.source_id = source_id
        self.details = details or {}
        super().__init__(self.message)


class TransformationError(Exception):
    """Base exception for data transformation errors."""

    def __init__(self, message: str, row_number: int | None = None, details: dict | None = None):
        self.message = message
        self.row_number = row_number
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(Exception):
    """Base exception for data validation errors."""

    def __init__(self, message: str, row_number: int | None = None, reasons: list[str] | None = None):
        self.message = message
        self.row_number = row_number
        self.reasons = reasons or []
        super().__init__(self.message)


@dataclass
class ExtractionResult:
    """Result of a data extraction operation."""

    source_id: str
    source_file: str
    row_count: int
    rows: list[dict]
    extracted_at: str
    metadata: dict[str, Any]

    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class TransformationResult:
    """Result of a data transformation operation."""

    source_id: str
    row_count: int
    rows: list[dict]
    transformed_at: str
    transformation_metadata: dict[str, Any]

    def __post_init__(self):
        if not self.transformed_at:
            self.transformed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class ValidationResult:
    """Result of a data validation operation."""

    source_id: str
    valid_rows: list[dict]
    invalid_rows: list[dict]
    validation_summary: dict[str, Any]

    @property
    def valid_count(self) -> int:
        return len(self.valid_rows)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_rows)

    @property
    def total_count(self) -> int:
        return self.valid_count + self.invalid_count

    @property
    def pass_rate(self) -> float:
        if self.total_count == 0:
            return 1.0
        return self.valid_count / self.total_count


class DataExtractor(ABC, Generic[T]):
    """Abstract base class for data extraction.

    Subclasses must implement:
    - extract(): Fetch raw data from source
    - parse(): Parse raw data into structured rows
    """

    def __init__(self, source: dict):
        """Initialize extractor with source metadata.

        Args:
            source: Source configuration dict from metadata
        """
        self.source = source
        self.source_id = source.get("source_id", "unknown")

    @abstractmethod
    def extract(self) -> bytes:
        """Fetch raw data from source.

        Returns:
            Raw data bytes (e.g., ZIP archive, CSV file)

        Raises:
            ExtractionError: If extraction fails
        """
        pass

    @abstractmethod
    def parse(self, raw_data: bytes, source_file: str) -> list[dict]:
        """Parse raw data into structured rows.

        Args:
            raw_data: Raw data bytes from extract()
            source_file: Source file identifier for lineage

        Returns:
            List of row dicts with extracted fields

        Raises:
            ExtractionError: If parsing fails
        """
        pass

    def extract_and_parse(self, source_file: str) -> ExtractionResult:
        """Extract and parse data in one operation.

        Args:
            source_file: Source file identifier for lineage

        Returns:
            ExtractionResult with parsed rows and metadata

        Raises:
            ExtractionError: If extraction or parsing fails
        """
        try:
            raw_data = self.extract()
            rows = self.parse(raw_data, source_file)
            return ExtractionResult(
                source_id=self.source_id,
                source_file=source_file,
                row_count=len(rows),
                rows=rows,
                extracted_at="",
                metadata={"raw_size_bytes": len(raw_data)},
            )
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(
                f"Extraction failed for {self.source_id}: {exc}",
                source_id=self.source_id,
                details={"exception": str(exc)},
            ) from exc


class DataTransformer(ABC, Generic[T, U]):
    """Abstract base class for data transformation.

    Subclasses must implement:
    - transform(): Transform extracted data to canonical form
    """

    def __init__(self, source: dict):
        """Initialize transformer with source metadata.

        Args:
            source: Source configuration dict from metadata
        """
        self.source = source
        self.source_id = source.get("source_id", "unknown")

    @abstractmethod
    def transform(self, rows: list[dict]) -> list[dict]:
        """Transform extracted rows to canonical form.

        Args:
            rows: List of extracted row dicts

        Returns:
            List of transformed row dicts

        Raises:
            TransformationError: If transformation fails
        """
        pass

    def transform_with_result(self, rows: list[dict]) -> TransformationResult:
        """Transform rows and return detailed result.

        Args:
            rows: List of extracted row dicts

        Returns:
            TransformationResult with transformed rows and metadata

        Raises:
            TransformationError: If transformation fails
        """
        try:
            transformed = self.transform(rows)
            return TransformationResult(
                source_id=self.source_id,
                row_count=len(transformed),
                rows=transformed,
                transformed_at="",
                transformation_metadata={"input_rows": len(rows), "output_rows": len(transformed)},
            )
        except TransformationError:
            raise
        except Exception as exc:
            raise TransformationError(
                f"Transformation failed for {self.source_id}: {exc}",
                details={"exception": str(exc)},
            ) from exc


class DataValidator(ABC):
    """Abstract base class for data validation.

    Subclasses must implement:
    - validate(): Validate rows against rules
    """

    def __init__(self, source: dict):
        """Initialize validator with source metadata.

        Args:
            source: Source configuration dict from metadata
        """
        self.source = source
        self.source_id = source.get("source_id", "unknown")

    @abstractmethod
    def validate(self, rows: list[dict]) -> ValidationResult:
        """Validate rows against rules.

        Args:
            rows: List of row dicts to validate

        Returns:
            ValidationResult with valid/invalid rows and summary

        Raises:
            ValidationError: If validation logic fails
        """
        pass

    def validate_row(self, row: dict, row_number: int) -> tuple[bool, list[str]]:
        """Validate a single row.

        Args:
            row: Row dict to validate
            row_number: Row number for error reporting

        Returns:
            Tuple of (is_valid, reasons) where reasons is list of failure codes

        Raises:
            ValidationError: If validation logic fails
        """
        try:
            # Subclasses should override this method
            return True, []
        except Exception as exc:
            raise ValidationError(
                f"Row validation failed: {exc}",
                row_number=row_number,
                reasons=[str(exc)],
            ) from exc
