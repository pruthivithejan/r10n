"""
Tests for the CSV Data Validator automation.

These tests are written FIRST (TDD red phase) to define the expected
behavior of the validate_csv automation before implementation.

The automation should:
- Validate CSV files against schemas/rules
- Check data types, required fields, and custom constraints
- Clean and normalize data
- Generate validation reports
"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

# These imports will fail until the module is implemented (TDD red phase)
from src.automations.validate_csv import (
    ValidationConfig,
    ValidationResult,
    CsvValidator,
    validate_csv,
    validate_directory,
    load_schema,
    generate_report,
    clean_csv,
)


class TestValidationConfig:
    """Test ValidationConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = ValidationConfig(input_file="data.csv")
        assert config.input_file == "data.csv"
        assert config.schema_file is None
        assert config.output_file is None
        assert config.strict_mode is False
        assert config.skip_empty_rows is True
        assert config.trim_whitespace is True
        assert config.encoding == "utf-8"

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = ValidationConfig(
            input_file="data.csv",
            schema_file="schema.json",
            output_file="cleaned.csv",
            strict_mode=True,
            skip_empty_rows=False,
            trim_whitespace=False,
            encoding="latin-1",
        )
        assert config.schema_file == "schema.json"
        assert config.strict_mode is True
        assert config.encoding == "latin-1"


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_result_valid(self):
        """Test valid result creation."""
        result = ValidationResult(
            is_valid=True, total_rows=100, valid_rows=100, invalid_rows=0, errors=[], warnings=[]
        )
        assert result.is_valid is True
        assert result.total_rows == 100
        assert result.valid_rows == 100
        assert len(result.errors) == 0

    def test_result_invalid(self):
        """Test invalid result with errors."""
        result = ValidationResult(
            is_valid=False,
            total_rows=100,
            valid_rows=95,
            invalid_rows=5,
            errors=[
                {"row": 10, "column": "email", "message": "Invalid email format"},
                {"row": 25, "column": "age", "message": "Must be a positive integer"},
            ],
            warnings=[],
        )
        assert result.is_valid is False
        assert result.invalid_rows == 5
        assert len(result.errors) == 2


class TestLoadSchema:
    """Test schema loading functionality."""

    def test_load_schema_basic(self):
        """Test loading basic schema."""
        schema_data = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "min": 0, "max": 150},
                "email": {"type": "email", "required": True},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(schema_data, f)
            file_path = f.name

        try:
            schema = load_schema(file_path)
            assert "fields" in schema
            assert "name" in schema["fields"]
            assert schema["fields"]["name"]["type"] == "string"
        finally:
            Path(file_path).unlink()

    def test_load_schema_file_not_found(self):
        """Test error for missing schema file."""
        with pytest.raises(FileNotFoundError):
            load_schema("nonexistent_schema.json")

    def test_load_schema_invalid_json(self):
        """Test error for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            file_path = f.name

        try:
            with pytest.raises(Exception):
                load_schema(file_path)
        finally:
            Path(file_path).unlink()

    def test_load_schema_with_custom_validators(self):
        """Test schema with custom validation rules."""
        schema_data = {
            "fields": {
                "phone": {"type": "string", "pattern": r"^\d{3}-\d{3}-\d{4}$"},
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(schema_data, f)
            file_path = f.name

        try:
            schema = load_schema(file_path)
            assert schema["fields"]["phone"]["pattern"] is not None
            assert "active" in schema["fields"]["status"]["enum"]
        finally:
            Path(file_path).unlink()


class TestCsvValidator:
    """Test CsvValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a CsvValidator instance for testing."""
        config = ValidationConfig(input_file="test.csv")
        return CsvValidator(config)

    @pytest.fixture
    def sample_csv(self):
        """Create a sample CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "age", "email"])
            writer.writerow(["Alice", "30", "alice@example.com"])
            writer.writerow(["Bob", "25", "bob@example.com"])
            writer.writerow(["Charlie", "35", "charlie@example.com"])
            return f.name

    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator.config is not None
        assert validator.config.input_file == "test.csv"

    def test_validate_type_string(self, validator):
        """Test string type validation."""
        assert validator.validate_type("hello", "string") is True
        assert validator.validate_type("", "string") is True
        assert validator.validate_type("123", "string") is True

    def test_validate_type_integer(self, validator):
        """Test integer type validation."""
        assert validator.validate_type("42", "integer") is True
        assert validator.validate_type("-10", "integer") is True
        assert validator.validate_type("3.14", "integer") is False
        assert validator.validate_type("abc", "integer") is False

    def test_validate_type_float(self, validator):
        """Test float type validation."""
        assert validator.validate_type("3.14", "float") is True
        assert validator.validate_type("42", "float") is True
        assert validator.validate_type("-0.5", "float") is True
        assert validator.validate_type("abc", "float") is False

    def test_validate_type_email(self, validator):
        """Test email type validation."""
        assert validator.validate_type("user@example.com", "email") is True
        assert validator.validate_type("name.surname@domain.co.uk", "email") is True
        assert validator.validate_type("invalid-email", "email") is False
        assert validator.validate_type("@missing.com", "email") is False

    def test_validate_type_date(self, validator):
        """Test date type validation."""
        assert validator.validate_type("2024-01-15", "date") is True
        assert validator.validate_type("2024/01/15", "date") is True
        assert validator.validate_type("invalid-date", "date") is False

    def test_validate_type_boolean(self, validator):
        """Test boolean type validation."""
        assert validator.validate_type("true", "boolean") is True
        assert validator.validate_type("false", "boolean") is True
        assert validator.validate_type("yes", "boolean") is True
        assert validator.validate_type("no", "boolean") is True
        assert validator.validate_type("1", "boolean") is True
        assert validator.validate_type("0", "boolean") is True
        assert validator.validate_type("maybe", "boolean") is False

    def test_validate_required_field(self, validator):
        """Test required field validation."""
        schema = {"fields": {"name": {"required": True}}}
        assert validator.validate_required("Alice", schema["fields"]["name"]) is True
        assert validator.validate_required("", schema["fields"]["name"]) is False
        assert validator.validate_required(None, schema["fields"]["name"]) is False

    def test_validate_min_max_integer(self, validator):
        """Test min/max validation for integers."""
        field_schema = {"type": "integer", "min": 0, "max": 100}
        assert validator.validate_range("50", field_schema) is True
        assert validator.validate_range("0", field_schema) is True
        assert validator.validate_range("100", field_schema) is True
        assert validator.validate_range("-1", field_schema) is False
        assert validator.validate_range("101", field_schema) is False

    def test_validate_min_max_length(self, validator):
        """Test min/max length validation for strings."""
        field_schema = {"type": "string", "min_length": 3, "max_length": 10}
        assert validator.validate_length("hello", field_schema) is True
        assert validator.validate_length("hi", field_schema) is False
        assert validator.validate_length("hello world!", field_schema) is False

    def test_validate_pattern(self, validator):
        """Test regex pattern validation."""
        field_schema = {"pattern": r"^\d{3}-\d{4}$"}
        assert validator.validate_pattern("123-4567", field_schema) is True
        assert validator.validate_pattern("12-4567", field_schema) is False
        assert validator.validate_pattern("abc-defg", field_schema) is False

    def test_validate_enum(self, validator):
        """Test enum validation."""
        field_schema = {"enum": ["red", "green", "blue"]}
        assert validator.validate_enum("red", field_schema) is True
        assert validator.validate_enum("green", field_schema) is True
        assert validator.validate_enum("yellow", field_schema) is False

    def test_validate_file(self, sample_csv, validator):
        """Test validating entire file."""
        schema = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "min": 0},
                "email": {"type": "email"},
            }
        }
        validator.config.input_file = sample_csv

        try:
            result = validator.validate(schema)
            assert result.is_valid is True
            assert result.total_rows == 3
            assert result.valid_rows == 3
        finally:
            Path(sample_csv).unlink()


class TestValidateCsv:
    """Test the main validate_csv function."""

    @pytest.fixture
    def create_csv_and_schema(self):
        """Factory to create test CSV and schema files."""
        created_files = []

        def _create(csv_data, schema_data):
            # Create CSV
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, newline=""
            ) as f:
                writer = csv.writer(f)
                for row in csv_data:
                    writer.writerow(row)
                csv_path = f.name
                created_files.append(csv_path)

            # Create schema
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(schema_data, f)
                schema_path = f.name
                created_files.append(schema_path)

            return csv_path, schema_path

        yield _create

        # Cleanup
        for f in created_files:
            Path(f).unlink(missing_ok=True)

    def test_validate_csv_valid(self, create_csv_and_schema):
        """Test validating a valid CSV file."""
        csv_data = [
            ["name", "age", "email"],
            ["Alice", "30", "alice@example.com"],
            ["Bob", "25", "bob@example.com"],
        ]
        schema_data = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer", "min": 0},
                "email": {"type": "email"},
            }
        }

        csv_path, schema_path = create_csv_and_schema(csv_data, schema_data)

        result = validate_csv(input_file=csv_path, schema_file=schema_path)

        assert result.is_valid is True
        assert result.total_rows == 2
        assert result.invalid_rows == 0

    def test_validate_csv_invalid(self, create_csv_and_schema):
        """Test validating an invalid CSV file."""
        csv_data = [
            ["name", "age", "email"],
            ["Alice", "thirty", "alice@example.com"],  # Invalid age
            ["", "25", "invalid-email"],  # Missing name, invalid email
        ]
        schema_data = {
            "fields": {
                "name": {"type": "string", "required": True},
                "age": {"type": "integer"},
                "email": {"type": "email"},
            }
        }

        csv_path, schema_path = create_csv_and_schema(csv_data, schema_data)

        result = validate_csv(input_file=csv_path, schema_file=schema_path)

        assert result.is_valid is False
        assert result.invalid_rows == 2
        assert len(result.errors) > 0

    def test_validate_csv_without_schema(self):
        """Test validating CSV without schema (basic validation only)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["col1", "col2"])
            writer.writerow(["value1", "value2"])
            csv_path = f.name

        try:
            result = validate_csv(input_file=csv_path)
            # Should at least check structure
            assert result.total_rows >= 1
        finally:
            Path(csv_path).unlink()

    def test_validate_csv_file_not_found(self):
        """Test error for missing CSV file."""
        with pytest.raises(FileNotFoundError):
            validate_csv(input_file="nonexistent.csv")


class TestValidateDirectory:
    """Test batch directory validation."""

    def test_validate_directory_basic(self):
        """Test validating all CSV files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create CSV files
            for i in range(3):
                csv_path = temp_path / f"data{i}.csv"
                with open(csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["name", "value"])
                    writer.writerow(["test", str(i)])

            result = validate_directory(input_dir=str(temp_path))

            assert result["total_files"] == 3
            assert result["valid_files"] >= 0

    def test_validate_directory_with_schema(self):
        """Test validating directory with shared schema."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create schema
            schema_path = temp_path / "schema.json"
            schema_data = {"fields": {"name": {"type": "string", "required": True}}}
            schema_path.write_text(json.dumps(schema_data))

            # Create CSV files
            for i in range(2):
                csv_path = temp_path / f"data{i}.csv"
                with open(csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["name"])
                    writer.writerow([f"Test {i}"])

            result = validate_directory(input_dir=str(temp_path), schema_file=str(schema_path))

            assert result["total_files"] == 2

    def test_validate_directory_empty(self):
        """Test validating empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_directory(input_dir=temp_dir)
            assert result["total_files"] == 0


class TestCleanCsv:
    """Test CSV cleaning functionality."""

    def test_clean_csv_trim_whitespace(self):
        """Test trimming whitespace from values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "dirty.csv"
            output_path = Path(temp_dir) / "clean.csv"

            with open(input_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "email"])
                writer.writerow(["  Alice  ", "  alice@example.com  "])

            result = clean_csv(
                input_file=str(input_path), output_file=str(output_path), trim_whitespace=True
            )

            assert result["success"] is True

            # Read and verify
            with open(output_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                row = next(reader)
                assert row[0] == "Alice"
                assert row[1] == "alice@example.com"

    def test_clean_csv_remove_empty_rows(self):
        """Test removing empty rows."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "with_empty.csv"
            output_path = Path(temp_dir) / "no_empty.csv"

            with open(input_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "value"])
                writer.writerow(["Alice", "1"])
                writer.writerow(["", ""])
                writer.writerow(["Bob", "2"])

            result = clean_csv(
                input_file=str(input_path), output_file=str(output_path), remove_empty_rows=True
            )

            assert result["rows_removed"] >= 1

            # Verify
            with open(output_path, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert len(rows) == 3  # Header + 2 data rows

    def test_clean_csv_normalize_case(self):
        """Test normalizing text case."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "mixed_case.csv"
            output_path = Path(temp_dir) / "normalized.csv"

            with open(input_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "status"])
                writer.writerow(["ALICE", "ACTIVE"])

            result = clean_csv(
                input_file=str(input_path), output_file=str(output_path), normalize_case="lower"
            )

            assert result["success"] is True

    def test_clean_csv_fill_missing(self):
        """Test filling missing values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "missing.csv"
            output_path = Path(temp_dir) / "filled.csv"

            with open(input_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "age"])
                writer.writerow(["Alice", ""])
                writer.writerow(["Bob", "30"])

            result = clean_csv(
                input_file=str(input_path), output_file=str(output_path), fill_missing={"age": "0"}
            )

            assert result["success"] is True

    def test_clean_csv_creates_nested_output_directory(self):
        """Test cleaning writes to nested output directories when needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "source.csv"
            output_path = Path(temp_dir) / "nested" / "clean" / "output.csv"

            with open(input_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["name"])
                writer.writerow(["Alice"])

            result = clean_csv(input_file=str(input_path), output_file=str(output_path))

            assert result["success"] is True
            assert output_path.exists()


class TestGenerateReport:
    """Test validation report generation."""

    def test_generate_report_text(self):
        """Test generating text report."""
        result = ValidationResult(
            is_valid=False,
            total_rows=100,
            valid_rows=95,
            invalid_rows=5,
            errors=[{"row": 10, "column": "email", "message": "Invalid email"}],
            warnings=[{"row": 20, "column": "name", "message": "Name is very short"}],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            report_path = f.name

        try:
            generate_report(result, output_path=report_path, format="text")

            content = Path(report_path).read_text()
            assert "100" in content  # Total rows
            assert "95" in content  # Valid rows
            assert "Invalid email" in content
        finally:
            Path(report_path).unlink()

    def test_generate_report_json(self):
        """Test generating JSON report."""
        result = ValidationResult(
            is_valid=True, total_rows=50, valid_rows=50, invalid_rows=0, errors=[], warnings=[]
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            report_path = f.name

        try:
            generate_report(result, output_path=report_path, format="json")

            with open(report_path) as f:
                report_data = json.load(f)

            assert report_data["is_valid"] is True
            assert report_data["total_rows"] == 50
        finally:
            Path(report_path).unlink()

    def test_generate_report_html(self):
        """Test generating HTML report."""
        result = ValidationResult(
            is_valid=False,
            total_rows=10,
            valid_rows=8,
            invalid_rows=2,
            errors=[{"row": 5, "column": "age", "message": "Not a number"}],
            warnings=[],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            report_path = f.name

        try:
            generate_report(result, output_path=report_path, format="html")

            content = Path(report_path).read_text()
            assert "<html" in content.lower()
            assert "Not a number" in content
        finally:
            Path(report_path).unlink()


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import validate_csv as mod

        assert hasattr(mod, "ValidationConfig")
        assert hasattr(mod, "ValidationResult")
        assert hasattr(mod, "CsvValidator")
        assert hasattr(mod, "validate_csv")
        assert hasattr(mod, "validate_directory")
        assert hasattr(mod, "load_schema")
        assert hasattr(mod, "generate_report")
        assert hasattr(mod, "clean_csv")

    def test_dataclass_fields(self):
        """Test ValidationConfig has all expected fields."""
        from dataclasses import fields

        field_names = {f.name for f in fields(ValidationConfig)}
        expected_fields = {
            "input_file",
            "schema_file",
            "output_file",
            "strict_mode",
            "skip_empty_rows",
            "trim_whitespace",
            "encoding",
        }
        assert field_names == expected_fields


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_validate_csv_with_bom(self):
        """Test validating CSV with BOM."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
            f.write(b"\xef\xbb\xbfname,value\n")
            f.write(b"test,123\n")
            csv_path = f.name

        try:
            result = validate_csv(input_file=csv_path)
            # Should handle BOM gracefully
            assert result.total_rows >= 1
        finally:
            Path(csv_path).unlink()

    def test_validate_csv_different_encodings(self):
        """Test validating CSV with different encodings."""
        encodings = ["utf-8", "latin-1", "cp1252"]

        for encoding in encodings:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, encoding=encoding, newline=""
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["name"])
                writer.writerow(["Test"])
                csv_path = f.name

            try:
                result = validate_csv(input_file=csv_path, encoding=encoding)
                assert result.total_rows >= 1
            finally:
                Path(csv_path).unlink()

    def test_validate_csv_with_quotes(self):
        """Test validating CSV with quoted fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(["name", "description"])
            writer.writerow(["Test", 'A "quoted" description'])
            csv_path = f.name

        try:
            result = validate_csv(input_file=csv_path)
            assert result.total_rows >= 1
        finally:
            Path(csv_path).unlink()

    def test_validate_csv_inconsistent_columns(self):
        """Test handling CSV with inconsistent column counts."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            f.write("col1,col2,col3\n")
            f.write("a,b,c\n")
            f.write("x,y\n")  # Missing column
            f.write("1,2,3,4\n")  # Extra column
            csv_path = f.name

        try:
            result = validate_csv(input_file=csv_path)
            # Should detect structural issues
            assert len(result.errors) > 0 or len(result.warnings) > 0
        finally:
            Path(csv_path).unlink()

    def test_validate_large_csv(self):
        """Test validating a large CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "value"])
            for i in range(10000):
                writer.writerow([i, f"Item {i}", i * 10])
            csv_path = f.name

        try:
            result = validate_csv(input_file=csv_path)
            assert result.total_rows == 10000
        finally:
            Path(csv_path).unlink()
