# ETL Extraction Framework

## Overview

The extraction framework provides a flexible, OOP-based architecture for multi-source data ingestion. It's designed to support NEMWEB and future data sources through a common set of abstractions.

**Key features:**
- **Metadata-driven:** All source configuration in `sources.json`
- **Flexible:** Support multiple data objects and column structures
- **Observable:** Detailed error tracking and lineage
- **Extensible:** Easy to add new sources and transformations
- **Testable:** Deterministic fixtures and comprehensive tests

## Architecture

### Directory Structure

```
agentic_energy/extraction/
├── __init__.py           # Public API
├── base.py               # Base classes and interfaces
├── common.py             # Reusable utilities
└── nemweb.py             # NEMWEB-specific extractors

tests/
└── test_extraction.py    # Comprehensive tests
```

### Core Abstractions

#### DataExtractor

Fetches and parses raw data from sources.

```python
class DataExtractor(ABC, Generic[T]):
    def extract(self) -> bytes:
        """Fetch raw data from source."""
        pass
    
    def parse(self, raw_data: bytes, source_file: str) -> list[dict]:
        """Parse raw data into structured rows."""
        pass
    
    def extract_and_parse(self, source_file: str) -> ExtractionResult:
        """Extract and parse in one operation."""
        pass
```

#### DataTransformer

Transforms extracted data to canonical form.

```python
class DataTransformer(ABC, Generic[T, U]):
    def transform(self, rows: list[dict]) -> list[dict]:
        """Transform rows to canonical form."""
        pass
    
    def transform_with_result(self, rows: list[dict]) -> TransformationResult:
        """Transform with detailed result."""
        pass
```

#### DataValidator

Validates data against rules and schemas.

```python
class DataValidator(ABC):
    def validate(self, rows: list[dict]) -> ValidationResult:
        """Validate rows against rules."""
        pass
    
    def validate_row(self, row: dict, row_number: int) -> tuple[bool, list[str]]:
        """Validate single row."""
        pass
```

### Common Utilities

#### ColumnMapping

Flexible field mapping from source to canonical names.

```python
# Simple rename
mapping = ColumnMapping({"canonical_field": "SOURCE_FIELD"})

# Computed column
mapping = ColumnMapping({
    "sum_field": lambda row: row["a"] + row["b"]
})

# Conditional mapping
mapping = ColumnMapping({
    "transformed": ("SOURCE_FIELD", lambda v: v.upper() if v else None)
})

result = mapping.apply({"SOURCE_FIELD": "value"})
```

#### ColumnTransformer

Apply transformations to columns (type coercion, custom functions).

```python
transformer = ColumnTransformer({
    "price": "float",           # Type coercion
    "region": lambda v: v.upper(),  # Custom function
    "value": {                  # Advanced spec
        "type": "float",
        "transformer": lambda v: v * 2,
        "null_handling": "keep"
    }
})

result = transformer.apply({"price": "99.99", "region": "nsw1"})
# {"price": 99.99, "region": "NSW1"}
```

#### TypeCoercer

Type conversion with error handling.

```python
TypeCoercer.coerce("123.45", "float")   # 123.45
TypeCoercer.coerce("true", "bool")      # True
TypeCoercer.coerce(None, "float")       # None
```

#### RemoteArchiveFetcher

Fetch and validate remote archives (ZIP files).

```python
fetcher = RemoteArchiveFetcher()

# Fetch latest archive
url, archive_bytes = fetcher.fetch_latest_archive(source)

# Extract CSV from ZIP
csv_content = fetcher.extract_csv_from_zip(archive_bytes)
```

#### CSVParser

Parse CSV content into rows.

```python
parser = CSVParser(delimiter=",", skip_rows=0, skip_footer=0)
rows = parser.parse(csv_content)
```

## NEMWEB Extractors

### DispatchISExtractor

Extracts AEMO DISPATCHIS reports (5-minute dispatch data).

**Features:**
- Multi-record CSV format (I/D/C records)
- Joins PRICE and REGIONSUM records
- Handles multiple report/version combinations

**Usage:**
```python
source = {
    "source_id": "aemo_dispatchis_live",
    "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/DispatchIS_Reports/",
    "allowed_hosts": ["nemweb.com.au"],
    "file_name_regex": "PUBLIC_DISPATCHIS_.*\\.zip$",
}

extractor = DispatchISExtractor(source)
result = extractor.extract_and_parse("PUBLIC_DISPATCHIS_20240407_1000.zip")

# result.rows = [
#     {
#         "region": "NSW1",
#         "interval_datetime": "2024-04-07T10:00:00",
#         "demand_mw": 5000.0,
#         "price_per_mwh": 50.0,
#         ...
#     },
#     ...
# ]
```

### PredispatchISExtractor

Extracts AEMO PREDISPATCHIS reports (30-minute predispatch data).

Uses same multi-record format as DISPATCHIS.

### RooftopPVExtractor

Extracts AEMO Rooftop PV reports (solar generation).

**Features:**
- Single-record CSV format
- Simple field mapping

**Usage:**
```python
source = {
    "source_id": "aemo_rooftop_pv_live",
    "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/Rooftop_PV_Reports/",
    "allowed_hosts": ["nemweb.com.au"],
    "file_name_regex": "PUBLIC_ROOFTOP_PV_.*\\.zip$",
}

extractor = RooftopPVExtractor(source)
result = extractor.extract_and_parse("PUBLIC_ROOFTOP_PV_20240407_1030.zip")
```

### DemandSideProgramsExtractor

Extracts AEMO Demand Side Programs (DSP) reports.

## Transformation and Validation

### NEMWEBTransformer

Applies column mapping and type coercion based on metadata.

```python
source = {
    "source_id": "aemo_dispatchis",
    "field_mapping": {
        "region": "REGION",
        "demand": "DEMAND_MW",
    },
    "field_types": {
        "demand": "float",
        "region": "string",
    }
}

transformer = NEMWEBTransformer(source)
result = transformer.transform_with_result(rows)
```

### NEMWEBValidator

Validates rows against quality_checks defined in metadata.

```python
source = {
    "source_id": "aemo_dispatchis",
    "quality_checks": [
        "demand_mw >= 0",
        "price_per_mwh is not null",
        "region is not null",
    ]
}

validator = NEMWEBValidator(source)
result = validator.validate(rows)

print(f"Valid: {result.valid_count}, Invalid: {result.invalid_count}")
print(f"Pass rate: {result.pass_rate * 100:.1f}%")
```

## Error Handling

### Exception Types

```python
# Extraction errors
try:
    extractor.extract()
except ExtractionError as e:
    print(f"Extraction failed: {e.message}")
    print(f"Details: {e.details}")

# Transformation errors
try:
    transformer.transform(rows)
except TransformationError as e:
    print(f"Transformation failed: {e.message}")
    print(f"Row: {e.row_number}")

# Validation errors
try:
    validator.validate(rows)
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Reasons: {e.reasons}")
```

## Complete Example

### Extract, Transform, and Validate

```python
from agentic_energy.extraction.nemweb import (
    get_nemweb_extractor,
    NEMWEBTransformer,
    NEMWEBValidator,
)

# Load source metadata
source = {
    "source_id": "aemo_dispatchis_live",
    "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/DispatchIS_Reports/",
    "allowed_hosts": ["nemweb.com.au"],
    "file_name_regex": "PUBLIC_DISPATCHIS_.*\\.zip$",
    "field_mapping": {
        "region": "region",
        "demand": "demand_mw",
        "price": "price_per_mwh",
    },
    "field_types": {
        "demand": "float",
        "price": "float",
    },
    "quality_checks": [
        "demand_mw >= 0",
        "price_per_mwh is not null",
    ]
}

# Extract
extractor = get_nemweb_extractor(source)
extraction_result = extractor.extract_and_parse("PUBLIC_DISPATCHIS_20240407_1000.zip")
print(f"Extracted {extraction_result.row_count} rows")

# Transform
transformer = NEMWEBTransformer(source)
transformation_result = transformer.transform_with_result(extraction_result.rows)
print(f"Transformed {transformation_result.row_count} rows")

# Validate
validator = NEMWEBValidator(source)
validation_result = validator.validate(transformation_result.rows)
print(f"Valid: {validation_result.valid_count}, Invalid: {validation_result.invalid_count}")
print(f"Pass rate: {validation_result.pass_rate * 100:.1f}%")

# Use valid rows
for row in validation_result.valid_rows:
    print(f"{row['region']}: {row['demand_mw']} MW @ {row['price_per_mwh']}/MWh")
```

## Extending the Framework

### Adding a New Source

1. **Create a new extractor class:**

```python
from agentic_energy.extraction.base import DataExtractor

class MySourceExtractor(DataExtractor):
    def extract(self) -> bytes:
        # Implement source-specific extraction
        pass
    
    def parse(self, raw_data: bytes, source_file: str) -> list[dict]:
        # Implement source-specific parsing
        pass
```

2. **Add to registry:**

```python
MY_SOURCE_EXTRACTORS = {
    "my_source_id": MySourceExtractor,
}
```

3. **Create metadata entry:**

```json
{
    "source_id": "my_source_id",
    "url_or_fixture_path": "https://example.com/data/",
    "allowed_hosts": ["example.com"],
    "field_mapping": {...},
    "field_types": {...},
    "quality_checks": [...]
}
```

### Custom Transformations

```python
class MyTransformer(DataTransformer):
    def transform(self, rows: list[dict]) -> list[dict]:
        # Custom transformation logic
        transformed = []
        for row in rows:
            # Apply custom logic
            transformed.append(row)
        return transformed
```

## Testing

### Unit Tests

```bash
pytest tests/test_extraction.py -v
```

### Test Coverage

- ColumnMapping: Simple rename, computed columns, conditional mapping
- ColumnTransformer: Type coercion, custom functions, advanced specs
- TypeCoercer: All supported types, null handling, error cases
- CSVParser: Simple parsing, skip rows/footer, custom delimiters
- DispatchISExtractor: Multi-record parsing, timestamp normalization
- RooftopPVExtractor: Single-record parsing
- NEMWEBTransformer: Column mapping and type coercion
- NEMWEBValidator: Quality check validation
- Extractor registry: Getting correct extractor for source

## Performance Considerations

### Memory Usage

- **Large archives:** Stream CSV parsing instead of loading entire file
- **Many rows:** Process in batches rather than loading all into memory
- **Column mapping:** Lazy evaluation for computed columns

### Network

- **Rate limiting:** Built-in RateLimiter (10 requests/minute default)
- **Retry logic:** Exponential backoff for transient failures
- **Timeout:** 60-second timeout for HTTP requests

### Optimization Tips

1. **Use fixtures for testing** instead of live sources
2. **Cache metadata** to avoid repeated parsing
3. **Batch transformations** for large datasets
4. **Use generators** for streaming data processing

## References

- Base classes: `agentic_energy/extraction/base.py`
- Common utilities: `agentic_energy/extraction/common.py`
- NEMWEB extractors: `agentic_energy/extraction/nemweb.py`
- Tests: `tests/test_extraction.py`
- NEMWEB contract: `docs/nemweb-contract.md`
- NEMWEB plan: `docs/nemweb-extraction-plan.md`
