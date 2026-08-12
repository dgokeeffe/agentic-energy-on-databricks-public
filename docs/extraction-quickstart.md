# ETL Extraction Framework — Quick Start Guide

## Installation

The extraction framework is part of the `agentic-energy` package:

```bash
pip install -e .
```

## Basic Usage

### Extract NEMWEB Data

```python
from agentic_energy.extraction.nemweb import get_nemweb_extractor

source = {
    "source_id": "aemo_dispatchis_live",
    "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/DispatchIS_Reports/",
    "allowed_hosts": ["nemweb.com.au"],
    "file_name_regex": "PUBLIC_DISPATCHIS_.*\\.zip$",
}

extractor = get_nemweb_extractor(source)
result = extractor.extract_and_parse("PUBLIC_DISPATCHIS_20240407_1000.zip")

print(f"Extracted {result.row_count} rows")
for row in result.rows[:3]:
    print(row)
```

### Transform Data

```python
from agentic_energy.extraction.nemweb import NEMWEBTransformer

source = {
    "source_id": "aemo_dispatchis",
    "field_mapping": {
        "region": "region",
        "demand": "demand_mw",
        "price": "price_per_mwh",
    },
    "field_types": {
        "demand": "float",
        "price": "float",
    }
}

transformer = NEMWEBTransformer(source)
result = transformer.transform_with_result(rows)

print(f"Transformed {result.row_count} rows")
```

### Validate Data

```python
from agentic_energy.extraction.nemweb import NEMWEBValidator

source = {
    "source_id": "aemo_dispatchis",
    "quality_checks": [
        "demand_mw >= 0",
        "price_per_mwh is not null",
    ]
}

validator = NEMWEBValidator(source)
result = validator.validate(rows)

print(f"Valid: {result.valid_count}, Invalid: {result.invalid_count}")
print(f"Pass rate: {result.pass_rate * 100:.1f}%")
```

## Common Tasks

### Map Columns

```python
from agentic_energy.extraction.common import ColumnMapping

mapping = ColumnMapping({
    "region": "REGION",
    "demand": "DEMAND_MW",
    "total": lambda row: row["DEMAND_MW"] * row["PRICE"],
})

result = mapping.apply({"REGION": "NSW1", "DEMAND_MW": "5000", "PRICE": "50"})
# {"region": "NSW1", "demand": "5000", "total": 250000}
```

### Coerce Types

```python
from agentic_energy.extraction.common import TypeCoercer

TypeCoercer.coerce("123.45", "float")    # 123.45
TypeCoercer.coerce("true", "bool")       # True
TypeCoercer.coerce("100", "int")         # 100
```

### Transform Columns

```python
from agentic_energy.extraction.common import ColumnTransformer

transformer = ColumnTransformer({
    "price": "float",
    "region": lambda v: v.upper(),
    "value": {
        "type": "float",
        "transformer": lambda v: v * 2,
    }
})

result = transformer.apply({"price": "99.99", "region": "nsw1", "value": "50"})
# {"price": 99.99, "region": "NSW1", "value": 100.0}
```

### Parse CSV

```python
from agentic_energy.extraction.common import CSVParser

parser = CSVParser(delimiter=",", skip_rows=1)
rows = parser.parse(csv_content)
```

### Fetch Remote Archive

```python
from agentic_energy.extraction.common import RemoteArchiveFetcher

fetcher = RemoteArchiveFetcher()
url, archive_bytes = fetcher.fetch_latest_archive(source)
csv_content = fetcher.extract_csv_from_zip(archive_bytes)
```

## Supported NEMWEB Sources

| Source | ID | Grain | Frequency |
|---|---|---|---|
| DISPATCHIS | `aemo_dispatchis` | Region × Interval | 5 min |
| PREDISPATCHIS | `aemo_predispatchis` | Region × Interval | 30 min |
| ROOFTOP_PV | `aemo_rooftop_pv` | Region × Interval | 30 min |
| DSP | `aemo_dsp` | Region × Interval | 5 min |

## Supported Data Types

- `string`: Text values
- `int`: Integer numbers
- `float`: Floating-point numbers
- `bool`: Boolean values (true/false/1/0/yes/no)

## Error Handling

```python
from agentic_energy.extraction.base import (
    ExtractionError,
    TransformationError,
    ValidationError,
)

try:
    extractor.extract()
except ExtractionError as e:
    print(f"Error: {e.message}")
    print(f"Details: {e.details}")
```

## Complete Example

```python
from agentic_energy.extraction.nemweb import (
    get_nemweb_extractor,
    NEMWEBTransformer,
    NEMWEBValidator,
)

# Configuration
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

# 1. Extract
extractor = get_nemweb_extractor(source)
extraction_result = extractor.extract_and_parse("PUBLIC_DISPATCHIS_20240407_1000.zip")
print(f"Extracted {extraction_result.row_count} rows")

# 2. Transform
transformer = NEMWEBTransformer(source)
transformation_result = transformer.transform_with_result(extraction_result.rows)
print(f"Transformed {transformation_result.row_count} rows")

# 3. Validate
validator = NEMWEBValidator(source)
validation_result = validator.validate(transformation_result.rows)
print(f"Valid: {validation_result.valid_count}, Invalid: {validation_result.invalid_count}")

# 4. Process valid rows
for row in validation_result.valid_rows:
    print(f"{row['region']}: {row['demand']} MW @ {row['price']}/MWh")
```

## Testing

```bash
# Run all extraction tests
pytest tests/test_extraction.py -v

# Run specific test
pytest tests/test_extraction.py::TestDispatchISExtractor -v

# Run with coverage
pytest tests/test_extraction.py --cov=agentic_energy.extraction
```

## API Reference

### DataExtractor

```python
class DataExtractor(ABC):
    def extract(self) -> bytes: ...
    def parse(self, raw_data: bytes, source_file: str) -> list[dict]: ...
    def extract_and_parse(self, source_file: str) -> ExtractionResult: ...
```

### DataTransformer

```python
class DataTransformer(ABC):
    def transform(self, rows: list[dict]) -> list[dict]: ...
    def transform_with_result(self, rows: list[dict]) -> TransformationResult: ...
```

### DataValidator

```python
class DataValidator(ABC):
    def validate(self, rows: list[dict]) -> ValidationResult: ...
    def validate_row(self, row: dict, row_number: int) -> tuple[bool, list[str]]: ...
```

### ColumnMapping

```python
class ColumnMapping:
    def __init__(self, mapping: dict[str, Any]): ...
    def apply(self, row: dict) -> dict: ...
```

### ColumnTransformer

```python
class ColumnTransformer:
    def __init__(self, transformations: dict[str, Any]): ...
    def apply(self, row: dict) -> dict: ...
```

### TypeCoercer

```python
class TypeCoercer:
    @classmethod
    def coerce(cls, value: Any, target_type: str) -> Any: ...
```

### RemoteArchiveFetcher

```python
class RemoteArchiveFetcher:
    def fetch_latest_archive(self, source: dict) -> tuple[str, bytes]: ...
    def extract_csv_from_zip(self, archive_bytes: bytes, csv_pattern: Optional[str] = None) -> str: ...
```

### CSVParser

```python
class CSVParser:
    def __init__(self, delimiter: str = ",", encoding: str = "utf-8", 
                 skip_rows: int = 0, skip_footer: int = 0): ...
    def parse(self, csv_content: str) -> list[dict]: ...
```

## Resources

- **Full documentation:** `docs/extraction-framework.md`
- **Implementation summary:** `docs/etl-implementation-summary.md`
- **NEMWEB plan:** `docs/nemweb-extraction-plan.md`
- **Source code:** `agentic_energy/extraction/`
- **Tests:** `tests/test_extraction.py`
