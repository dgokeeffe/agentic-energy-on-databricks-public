"""Tests for the extraction framework and NEMWEB extractors."""

import pytest
from agentic_energy.extraction.base import (
    DataExtractor,
    DataTransformer,
    DataValidator,
    ExtractionError,
    TransformationError,
    ValidationError,
    ExtractionResult,
    TransformationResult,
    ValidationResult,
)
from agentic_energy.extraction.common import (
    ColumnMapping,
    ColumnTransformer,
    TypeCoercer,
    CSVParser,
)
from agentic_energy.extraction.nemweb import (
    DispatchISExtractor,
    RooftopPVExtractor,
    NEMWEBTransformer,
    NEMWEBValidator,
    get_nemweb_extractor,
)


class TestColumnMapping:
    """Test column mapping functionality."""

    def test_simple_rename(self):
        """Test simple field rename."""
        mapping = ColumnMapping({"canonical_field": "SOURCE_FIELD"})
        row = {"SOURCE_FIELD": "value"}
        result = mapping.apply(row)
        assert result == {"canonical_field": "value"}

    def test_computed_column(self):
        """Test computed column from lambda."""
        mapping = ColumnMapping(
            {
                "sum_field": lambda row: (row.get("a") or 0) + (row.get("b") or 0),
            }
        )
        row = {"a": 10, "b": 20}
        result = mapping.apply(row)
        assert result == {"sum_field": 30}

    def test_conditional_mapping(self):
        """Test conditional mapping with transformer."""
        mapping = ColumnMapping(
            {
                "transformed": ("SOURCE_FIELD", lambda v: v.upper() if v else None),
            }
        )
        row = {"SOURCE_FIELD": "hello"}
        result = mapping.apply(row)
        assert result == {"transformed": "HELLO"}

    def test_missing_field(self):
        """Test mapping with missing source field."""
        mapping = ColumnMapping({"canonical": "MISSING"})
        row = {"OTHER": "value"}
        result = mapping.apply(row)
        assert result == {"canonical": None}


class TestTypeCoercer:
    """Test type coercion functionality."""

    def test_coerce_to_float(self):
        """Test coercion to float."""
        assert TypeCoercer.coerce("123.45", "float") == 123.45
        assert TypeCoercer.coerce("100", "float") == 100.0
        assert TypeCoercer.coerce(None, "float") is None
        assert TypeCoercer.coerce("", "float") is None

    def test_coerce_to_int(self):
        """Test coercion to int."""
        assert TypeCoercer.coerce("123", "int") == 123
        assert TypeCoercer.coerce(None, "int") is None

    def test_coerce_to_bool(self):
        """Test coercion to bool."""
        assert TypeCoercer.coerce("true", "bool") is True
        assert TypeCoercer.coerce("1", "bool") is True
        assert TypeCoercer.coerce("yes", "bool") is True
        assert TypeCoercer.coerce("false", "bool") is False

    def test_coerce_invalid_type(self):
        """Test coercion with invalid type."""
        with pytest.raises(TransformationError):
            TypeCoercer.coerce("value", "invalid_type")

    def test_coerce_invalid_value(self):
        """Test coercion with invalid value for type."""
        with pytest.raises(TransformationError):
            TypeCoercer.coerce("not_a_number", "float")


class TestColumnTransformer:
    """Test column transformation functionality."""

    def test_type_coercion(self):
        """Test type coercion transformation."""
        transformer = ColumnTransformer({"price": "float", "quantity": "int"})
        row = {"price": "99.99", "quantity": "10"}
        result = transformer.apply(row)
        assert result == {"price": 99.99, "quantity": 10}

    def test_custom_transformer(self):
        """Test custom transformation function."""
        transformer = ColumnTransformer(
            {
                "region": lambda v: v.upper(),
            }
        )
        row = {"region": "nsw1"}
        result = transformer.apply(row)
        assert result == {"region": "NSW1"}

    def test_advanced_spec(self):
        """Test advanced transformation spec."""
        transformer = ColumnTransformer(
            {
                "value": {
                    "type": "float",
                    "transformer": lambda v: v * 2 if v else None,
                }
            }
        )
        row = {"value": "50"}
        result = transformer.apply(row)
        assert result == {"value": 100.0}

    def test_null_handling(self):
        """Test null value handling."""
        transformer = ColumnTransformer(
            {
                "field": {
                    "type": "float",
                    "null_handling": "keep",
                }
            }
        )
        row = {"field": None}
        result = transformer.apply(row)
        assert result == {"field": None}


class TestCSVParser:
    """Test CSV parsing functionality."""

    def test_parse_simple_csv(self):
        """Test parsing simple CSV."""
        csv_content = "name,value\nAlice,100\nBob,200"
        parser = CSVParser()
        rows = parser.parse(csv_content)
        assert len(rows) == 2
        assert rows[0] == {"name": "Alice", "value": "100"}
        assert rows[1] == {"name": "Bob", "value": "200"}

    def test_parse_with_skip_rows(self):
        """Test parsing with skip_rows."""
        csv_content = "# Comment\nname,value\nAlice,100"
        parser = CSVParser(skip_rows=1)
        rows = parser.parse(csv_content)
        assert len(rows) == 1
        assert rows[0] == {"name": "Alice", "value": "100"}

    def test_parse_with_skip_footer(self):
        """Test parsing with skip_footer."""
        csv_content = "name,value\nAlice,100\nBob,200\n# Footer"
        parser = CSVParser(skip_footer=1)
        rows = parser.parse(csv_content)
        assert len(rows) == 2

    def test_parse_custom_delimiter(self):
        """Test parsing with custom delimiter."""
        csv_content = "name|value\nAlice|100"
        parser = CSVParser(delimiter="|")
        rows = parser.parse(csv_content)
        assert rows[0] == {"name": "Alice", "value": "100"}


class TestDispatchISExtractor:
    """Test DISPATCHIS extractor."""

    def test_normalize_timestamp(self):
        """Test timestamp normalization."""
        ts = "2024/04/07 10:00:00"
        result = DispatchISExtractor._normalize_timestamp(ts)
        assert result == "2024-04-07T10:00:00"

    def test_parse_number(self):
        """Test number parsing."""
        assert DispatchISExtractor._parse_number("123.45") == 123.45
        assert DispatchISExtractor._parse_number(None) is None
        assert DispatchISExtractor._parse_number("") is None

    def test_parse_dispatchis_csv(self):
        """Test parsing DISPATCHIS multi-record CSV."""
        csv_content = """I,1,PRICE,1,SETTLEMENTDATE,REGIONID,RRP,DISPATCHINTERVAL
D,1,PRICE,1,2024/04/07 10:00:00,NSW1,50.0,1
I,1,REGIONSUM,1,SETTLEMENTDATE,REGIONID,TOTALDEMAND,DISPATCHINTERVAL
D,1,REGIONSUM,1,2024/04/07 10:00:00,NSW1,5000.0,1"""

        source = {
            "source_id": "aemo_dispatchis",
            "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/DispatchIS_Reports/",
            "allowed_hosts": ["nemweb.com.au"],
            "file_name_regex": "PUBLIC_DISPATCHIS_.*\\.zip$",
        }

        extractor = DispatchISExtractor(source)
        rows = extractor._parse_csv(csv_content, "test.csv")

        assert len(rows) == 1
        assert rows[0]["region"] == "NSW1"
        assert rows[0]["interval_datetime"] == "2024-04-07T10:00:00"
        assert rows[0]["demand_mw"] == 5000.0
        assert rows[0]["price_per_mwh"] == 50.0


class TestRooftopPVExtractor:
    """Test Rooftop PV extractor."""

    def test_parse_rooftop_pv_csv(self):
        """Test parsing Rooftop PV CSV."""
        csv_content = """SETTLEMENTDATE,REGIONID,TOTAL_ROOFTOP_PV
2024/04/07 10:00:00,NSW1,1500.0
2024/04/07 10:30:00,QLD1,2000.0"""

        source = {
            "source_id": "aemo_rooftop_pv",
            "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/Rooftop_PV_Reports/",
            "allowed_hosts": ["nemweb.com.au"],
            "file_name_regex": "PUBLIC_ROOFTOP_PV_.*\\.zip$",
        }

        extractor = RooftopPVExtractor(source)
        rows = extractor._parse_csv(csv_content, "test.csv")

        assert len(rows) == 2
        assert rows[0]["region"] == "NSW1"
        assert rows[0]["generation_mw"] == 1500.0
        assert rows[1]["region"] == "QLD1"
        assert rows[1]["generation_mw"] == 2000.0


class TestNEMWEBTransformer:
    """Test NEMWEB transformer."""

    def test_transform_with_mapping(self):
        """Test transformation with column mapping."""
        source = {
            "source_id": "aemo_dispatchis",
            "field_mapping": {
                "region": "REGION",
                "demand": "DEMAND_MW",
            },
            "field_types": {
                "demand": "float",
            },
        }

        transformer = NEMWEBTransformer(source)
        rows = [{"REGION": "NSW1", "DEMAND_MW": "5000"}]
        result = transformer.transform(rows)

        assert len(result) == 1
        assert result[0]["region"] == "NSW1"
        assert result[0]["demand"] == 5000.0


class TestNEMWEBValidator:
    """Test NEMWEB validator."""

    def test_validate_rows(self):
        """Test row validation."""
        source = {
            "source_id": "aemo_dispatchis",
            "quality_checks": [
                "demand_mw >= 0",
                "price_per_mwh is not null",
            ],
        }

        validator = NEMWEBValidator(source)
        rows = [
            {"demand_mw": 5000, "price_per_mwh": 50.0},  # Valid
            {"demand_mw": -100, "price_per_mwh": 50.0},  # Invalid demand
            {"demand_mw": 5000, "price_per_mwh": None},  # Invalid price
        ]

        result = validator.validate(rows)

        assert result.valid_count == 1
        assert result.invalid_count == 2
        assert result.pass_rate == 1 / 3


class TestGetNemwebExtractor:
    """Test extractor registry."""

    def test_get_dispatchis_extractor(self):
        """Test getting DISPATCHIS extractor."""
        source = {
            "source_id": "aemo_dispatchis",
            "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/DispatchIS_Reports/",
            "allowed_hosts": ["nemweb.com.au"],
        }
        extractor = get_nemweb_extractor(source)
        assert isinstance(extractor, DispatchISExtractor)

    def test_get_rooftop_pv_extractor(self):
        """Test getting Rooftop PV extractor."""
        source = {
            "source_id": "aemo_rooftop_pv",
            "url_or_fixture_path": "https://nemweb.com.au/Reports/Current/Rooftop_PV_Reports/",
            "allowed_hosts": ["nemweb.com.au"],
        }
        extractor = get_nemweb_extractor(source)
        assert isinstance(extractor, RooftopPVExtractor)

    def test_get_unknown_extractor(self):
        """Test getting unknown extractor raises error."""
        source = {
            "source_id": "unknown_source",
        }
        with pytest.raises(ValueError):
            get_nemweb_extractor(source)


class TestExtractionResult:
    """Test ExtractionResult data class."""

    def test_extraction_result_creation(self):
        """Test creating ExtractionResult."""
        result = ExtractionResult(
            source_id="test",
            source_file="test.csv",
            row_count=100,
            rows=[],
            extracted_at="",
            metadata={},
        )
        assert result.source_id == "test"
        assert result.row_count == 100
        assert result.extracted_at  # Should be auto-populated


class TestValidationResult:
    """Test ValidationResult data class."""

    def test_validation_result_metrics(self):
        """Test ValidationResult metrics."""
        result = ValidationResult(
            source_id="test",
            valid_rows=[{}, {}, {}],
            invalid_rows=[{}, {}],
            validation_summary={},
        )
        assert result.valid_count == 3
        assert result.invalid_count == 2
        assert result.total_count == 5
        assert result.pass_rate == 0.6

    def test_validation_result_empty(self):
        """Test ValidationResult with empty rows."""
        result = ValidationResult(
            source_id="test",
            valid_rows=[],
            invalid_rows=[],
            validation_summary={},
        )
        assert result.pass_rate == 1.0
