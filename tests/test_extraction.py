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


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_extraction_error_with_details(self):
        """Test ExtractionError includes source_id and details."""
        error = ExtractionError(
            "NO_CSV_IN_ARCHIVE",
            source_id="test_source",
            details={"archive": "file.zip"},
        )
        assert error.source_id == "test_source"
        assert error.details["archive"] == "file.zip"
        assert error.message == "NO_CSV_IN_ARCHIVE"

    def test_transformation_error_with_context(self):
        """Test TransformationError includes row context."""
        error = TransformationError(
            "Type coercion failed",
            row_number=5,
            details={"price": "invalid"},
        )
        assert error.row_number == 5
        assert error.details == {"price": "invalid"}

    def test_validation_error_with_reasons(self):
        """Test ValidationError includes failure reasons."""
        error = ValidationError(
            "Validation failed",
            reasons=["demand_mw >= 0", "price_per_mwh is not null"],
        )
        assert len(error.reasons) == 2
        assert "demand_mw >= 0" in error.reasons

    def test_type_coercer_scientific_notation(self):
        """Test TypeCoercer handles scientific notation."""
        assert TypeCoercer.coerce("1.23e5", "float") == 123000.0
        assert TypeCoercer.coerce("1e-2", "float") == 0.01

    def test_type_coercer_negative_numbers(self):
        """Test TypeCoercer handles negative numbers."""
        assert TypeCoercer.coerce("-123.45", "float") == -123.45
        assert TypeCoercer.coerce("-100", "int") == -100

    def test_type_coercer_zero_values(self):
        """Test TypeCoercer handles zero values."""
        assert TypeCoercer.coerce("0", "int") == 0
        assert TypeCoercer.coerce("0.0", "float") == 0.0
        assert TypeCoercer.coerce("0", "bool") is False

    def test_column_transformer_multiple_fields(self):
        """Test ColumnTransformer with multiple fields."""
        transformer = ColumnTransformer(
            {
                "price": "float",
                "quantity": "int",
                "region": lambda v: v.upper(),
            }
        )
        row = {"price": "99.99", "quantity": "10", "region": "nsw1"}
        result = transformer.apply(row)
        assert result["price"] == 99.99
        assert result["quantity"] == 10
        assert result["region"] == "NSW1"

    def test_csv_parser_empty_file(self):
        """Test CSVParser with empty file."""
        csv_content = ""
        parser = CSVParser()
        rows = parser.parse(csv_content)
        assert len(rows) == 0

    def test_csv_parser_header_only(self):
        """Test CSVParser with header only."""
        csv_content = "name,value"
        parser = CSVParser()
        rows = parser.parse(csv_content)
        assert len(rows) == 0

    def test_nemweb_validator_all_operators(self):
        """Test NEMWEBValidator with all supported operators."""
        source = {
            "source_id": "test",
            "quality_checks": [
                "value >= 0",
                "value <= 100",
                "value > -1",
                "value < 101",
                "value == 50",
                "value != 0",
                "region is not null",
                "description is null",
            ],
        }
        validator = NEMWEBValidator(source)
        rows = [
            {
                "value": 50,
                "region": "NSW1",
                "description": None,
            }  # Valid
        ]
        result = validator.validate(rows)
        assert result.valid_count == 1

    def test_nemweb_validator_edge_values(self):
        """Test NEMWEBValidator with edge values."""
        source = {
            "source_id": "test",
            "quality_checks": ["demand_mw >= 0"],
        }
        validator = NEMWEBValidator(source)
        rows = [
            {"demand_mw": 0},  # Valid (boundary)
            {"demand_mw": 9999999},  # Valid (large)
            {"demand_mw": -0.0001},  # Invalid (just below 0)
        ]
        result = validator.validate(rows)
        assert result.valid_count == 2
        assert result.invalid_count == 1

    def test_dispatchis_timestamp_edge_cases(self):
        """Test DISPATCHIS timestamp normalization with edge cases."""
        # Midnight
        assert DispatchISExtractor._normalize_timestamp("2024/04/07 00:00:00") == "2024-04-07T00:00:00"
        # End of day
        assert DispatchISExtractor._normalize_timestamp("2024/04/07 23:59:59") == "2024-04-07T23:59:59"
        # Single digit month/day
        assert DispatchISExtractor._normalize_timestamp("2024/1/1 1:1:1") == "2024-1-1T1:1:1"

    def test_dispatchis_number_parsing_edge_cases(self):
        """Test DISPATCHIS number parsing with edge cases."""
        # Scientific notation
        assert DispatchISExtractor._parse_number("1.23e5") == 123000.0
        # Very small number
        assert DispatchISExtractor._parse_number("0.0001") == 0.0001
        # Negative number
        assert DispatchISExtractor._parse_number("-123.45") == -123.45
        # Zero
        assert DispatchISExtractor._parse_number("0") == 0.0

    def test_column_mapping_empty_mapping(self):
        """Test ColumnMapping with empty mapping."""
        mapping = ColumnMapping({})
        row = {"field": "value"}
        result = mapping.apply(row)
        assert result == {}

    def test_column_mapping_multiple_computed_columns(self):
        """Test ColumnMapping with multiple computed columns."""
        mapping = ColumnMapping(
            {
                "sum": lambda row: (row.get("a") or 0) + (row.get("b") or 0),
                "product": lambda row: (row.get("a") or 1) * (row.get("b") or 1),
                "concat": lambda row: f"{row.get('a')}_{row.get('b')}",
            }
        )
        row = {"a": 10, "b": 20}
        result = mapping.apply(row)
        assert result["sum"] == 30
        assert result["product"] == 200
        assert result["concat"] == "10_20"

    def test_full_etl_pipeline(self):
        """Test complete extract → transform → validate pipeline."""
        source = {
            "source_id": "aemo_dispatchis",
            "field_mapping": {"region": "region", "demand": "demand_mw"},
            "field_types": {"demand": "float"},
            "quality_checks": ["demand >= 0"],
        }

        # Create test data
        csv_content = """I,1,PRICE,1,SETTLEMENTDATE,REGIONID,RRP,DISPATCHINTERVAL
D,1,PRICE,1,2024/04/07 10:00:00,NSW1,50.0,1
I,1,REGIONSUM,1,SETTLEMENTDATE,REGIONID,TOTALDEMAND,DISPATCHINTERVAL
D,1,REGIONSUM,1,2024/04/07 10:00:00,NSW1,5000.0,1"""

        # Extract
        extractor = DispatchISExtractor(source)
        extraction = extractor._parse_csv(csv_content, "test.csv")
        assert len(extraction) == 1

        # Transform
        transformer = NEMWEBTransformer(source)
        transformation = transformer.transform(extraction)
        assert len(transformation) == 1
        assert transformation[0]["demand"] == 5000.0

        # Validate
        validator = NEMWEBValidator(source)
        validation = validator.validate(transformation)
        assert validation.valid_count == 1
        assert validation.pass_rate == 1.0
