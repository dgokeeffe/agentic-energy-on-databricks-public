"""Flexible, OOP-based ETL extraction framework for multi-source data ingestion.

This module provides:
- Base classes for data extraction, transformation, and validation
- Common utilities for HTTP/archive handling
- Column mapping and type coercion
- Error handling and recovery
- Extensible parser registry for future sources

Design principles:
- Metadata-driven: All source configuration in sources.json
- Flexible: Support multiple data objects and column structures
- Observable: Detailed error tracking and lineage
- Testable: Deterministic fixtures and unit tests
"""

from .base import (
    DataExtractor,
    DataTransformer,
    DataValidator,
    ExtractionError,
    TransformationError,
    ValidationError,
)
from .common import (
    ColumnMapping,
    ColumnTransformer,
    TypeCoercer,
    RemoteArchiveFetcher,
)

__all__ = [
    "DataExtractor",
    "DataTransformer",
    "DataValidator",
    "ExtractionError",
    "TransformationError",
    "ValidationError",
    "ColumnMapping",
    "ColumnTransformer",
    "TypeCoercer",
    "RemoteArchiveFetcher",
]
