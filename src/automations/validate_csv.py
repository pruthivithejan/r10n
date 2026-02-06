"""
CSV Data Validator automation.

Validates CSV files against schemas/rules, checks data types,
required fields, and custom constraints. Provides cleaning and
normalization features and generates validation reports.
"""

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ValidationConfig:
    """Configuration for CSV validation."""

    input_file: str
    schema_file: str | None = None
    output_file: str | None = None
    strict_mode: bool = False
    skip_empty_rows: bool = True
    trim_whitespace: bool = True
    encoding: str = "utf-8"


@dataclass
class ValidationResult:
    """Result of a CSV validation operation."""

    is_valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)


# Email regex pattern
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Date patterns to try
DATE_PATTERNS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%m/%d/%Y",
]

# Boolean true values
BOOLEAN_TRUE = {"true", "yes", "1", "t", "y"}
BOOLEAN_FALSE = {"false", "no", "0", "f", "n"}


def load_schema(schema_path: str) -> dict[str, Any]:
    """
    Load validation schema from a JSON file.

    Args:
        schema_path: Path to the schema JSON file

    Returns:
        Schema dictionary

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema is invalid JSON
    """
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(path, encoding="utf-8") as f:
        return json.load(f)


class CsvValidator:
    """Class for validating CSV files."""

    def __init__(self, config: ValidationConfig):
        """
        Initialize the CsvValidator.

        Args:
            config: Validation configuration
        """
        self.config = config

    def validate_type(self, value: str, type_name: str) -> bool:
        """
        Validate that a value matches the expected type.

        Args:
            value: The value to validate
            type_name: Expected type (string, integer, float, email, date, boolean)

        Returns:
            True if valid, False otherwise
        """
        if type_name == "string":
            return True  # All values are strings

        if type_name == "integer":
            try:
                int(value)
                return True
            except ValueError:
                return False

        if type_name == "float":
            try:
                float(value)
                return True
            except ValueError:
                return False

        if type_name == "email":
            return bool(EMAIL_PATTERN.match(value))

        if type_name == "date":
            for pattern in DATE_PATTERNS:
                try:
                    datetime.strptime(value, pattern)
                    return True
                except ValueError:
                    continue
            return False

        if type_name == "boolean":
            return value.lower() in BOOLEAN_TRUE | BOOLEAN_FALSE

        return True  # Unknown types pass

    def validate_required(self, value: str | None, field_schema: dict) -> bool:
        """
        Validate that a required field has a value.

        Args:
            value: The value to check
            field_schema: Schema for this field

        Returns:
            True if valid, False otherwise
        """
        if not field_schema.get("required", False):
            return True

        if value is None or value == "":
            return False

        return True

    def validate_range(self, value: str, field_schema: dict) -> bool:
        """
        Validate that a numeric value is within range.

        Args:
            value: The value to check
            field_schema: Schema with min/max constraints

        Returns:
            True if valid, False otherwise
        """
        try:
            num_value = float(value)
        except ValueError:
            return False

        min_val = field_schema.get("min")
        max_val = field_schema.get("max")

        if min_val is not None and num_value < min_val:
            return False

        if max_val is not None and num_value > max_val:
            return False

        return True

    def validate_length(self, value: str, field_schema: dict) -> bool:
        """
        Validate that a string value length is within bounds.

        Args:
            value: The value to check
            field_schema: Schema with min_length/max_length constraints

        Returns:
            True if valid, False otherwise
        """
        min_length = field_schema.get("min_length")
        max_length = field_schema.get("max_length")

        if min_length is not None and len(value) < min_length:
            return False

        if max_length is not None and len(value) > max_length:
            return False

        return True

    def validate_pattern(self, value: str, field_schema: dict) -> bool:
        """
        Validate that a value matches a regex pattern.

        Args:
            value: The value to check
            field_schema: Schema with pattern constraint

        Returns:
            True if valid, False otherwise
        """
        pattern = field_schema.get("pattern")
        if pattern is None:
            return True

        return bool(re.match(pattern, value))

    def validate_enum(self, value: str, field_schema: dict) -> bool:
        """
        Validate that a value is in an allowed set.

        Args:
            value: The value to check
            field_schema: Schema with enum constraint

        Returns:
            True if valid, False otherwise
        """
        allowed = field_schema.get("enum")
        if allowed is None:
            return True

        return value in allowed

    def validate_field(
        self, value: str, field_name: str, field_schema: dict, row_num: int
    ) -> list[dict[str, Any]]:
        """
        Validate a single field against its schema.

        Args:
            value: The field value
            field_name: Name of the field
            field_schema: Schema for this field
            row_num: Row number for error reporting

        Returns:
            List of error dicts (empty if valid)
        """
        errors = []

        # Trim whitespace if configured
        if self.config.trim_whitespace:
            value = value.strip()

        # Check required
        if not self.validate_required(value, field_schema):
            errors.append(
                {
                    "row": row_num,
                    "column": field_name,
                    "message": f"Required field '{field_name}' is empty",
                }
            )
            return errors  # Skip other validations for empty required fields

        # Skip other validations for empty optional fields
        if value == "":
            return errors

        # Check type
        field_type = field_schema.get("type", "string")
        if not self.validate_type(value, field_type):
            errors.append(
                {
                    "row": row_num,
                    "column": field_name,
                    "message": f"Invalid {field_type} value: '{value}'",
                }
            )

        # Check range (for numeric types)
        if field_type in ("integer", "float"):
            if "min" in field_schema or "max" in field_schema:
                if not self.validate_range(value, field_schema):
                    errors.append(
                        {
                            "row": row_num,
                            "column": field_name,
                            "message": f"Value {value} out of range",
                        }
                    )

        # Check length (for strings)
        if field_type == "string":
            if "min_length" in field_schema or "max_length" in field_schema:
                if not self.validate_length(value, field_schema):
                    errors.append(
                        {
                            "row": row_num,
                            "column": field_name,
                            "message": f"Length of '{value}' out of bounds",
                        }
                    )

        # Check pattern
        if "pattern" in field_schema:
            if not self.validate_pattern(value, field_schema):
                errors.append(
                    {
                        "row": row_num,
                        "column": field_name,
                        "message": f"Value '{value}' does not match pattern",
                    }
                )

        # Check enum
        if "enum" in field_schema:
            if not self.validate_enum(value, field_schema):
                errors.append(
                    {
                        "row": row_num,
                        "column": field_name,
                        "message": f"Value '{value}' not in allowed values",
                    }
                )

        return errors

    def validate(self, schema: dict[str, Any] | None = None) -> ValidationResult:
        """
        Validate the CSV file against a schema.

        Args:
            schema: Validation schema (optional)

        Returns:
            ValidationResult with details
        """
        input_path = Path(self.config.input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.config.input_file}")

        all_errors = []
        all_warnings = []
        total_rows = 0
        valid_rows = 0
        invalid_rows = 0

        # Handle BOM
        encoding = self.config.encoding
        with open(input_path, "rb") as f:
            first_bytes = f.read(3)
            if first_bytes == b"\xef\xbb\xbf":
                encoding = "utf-8-sig"

        with open(input_path, encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Get field schemas if available
            field_schemas = {}
            if schema and "fields" in schema:
                field_schemas = schema["fields"]

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                # Check for empty rows
                if self.config.skip_empty_rows:
                    if all(not v or v.strip() == "" for v in row.values()):
                        continue

                total_rows += 1
                row_errors = []

                # Check column count consistency
                if len(row) != len(headers):
                    all_warnings.append(
                        {
                            "row": row_num,
                            "column": None,
                            "message": f"Inconsistent column count: expected {len(headers)}, got {len(row)}",
                        }
                    )

                # Validate each field
                for field_name, value in row.items():
                    if field_name is None:
                        continue

                    value = value or ""

                    if field_name in field_schemas:
                        field_errors = self.validate_field(
                            value, field_name, field_schemas[field_name], row_num
                        )
                        row_errors.extend(field_errors)

                if row_errors:
                    all_errors.extend(row_errors)
                    invalid_rows += 1
                else:
                    valid_rows += 1

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            errors=all_errors,
            warnings=all_warnings,
        )


def validate_csv(
    input_file: str,
    schema_file: str | None = None,
    output_file: str | None = None,
    strict_mode: bool = False,
    skip_empty_rows: bool = True,
    trim_whitespace: bool = True,
    encoding: str = "utf-8",
) -> ValidationResult:
    """
    Validate a CSV file against an optional schema.

    Args:
        input_file: Path to CSV file to validate
        schema_file: Path to JSON schema file (optional)
        output_file: Path for cleaned output (optional)
        strict_mode: Fail on warnings too
        skip_empty_rows: Skip rows that are entirely empty
        trim_whitespace: Trim whitespace from values
        encoding: File encoding

    Returns:
        ValidationResult with details

    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"CSV file not found: {input_file}")

    config = ValidationConfig(
        input_file=input_file,
        schema_file=schema_file,
        output_file=output_file,
        strict_mode=strict_mode,
        skip_empty_rows=skip_empty_rows,
        trim_whitespace=trim_whitespace,
        encoding=encoding,
    )

    schema = None
    if schema_file:
        schema = load_schema(schema_file)

    validator = CsvValidator(config)
    return validator.validate(schema)


def validate_directory(
    input_dir: str,
    schema_file: str | None = None,
    encoding: str = "utf-8",
) -> dict[str, Any]:
    """
    Validate all CSV files in a directory.

    Args:
        input_dir: Directory containing CSV files
        schema_file: Path to shared JSON schema (optional)
        encoding: File encoding

    Returns:
        Dictionary with validation summary
    """
    input_path = Path(input_dir)
    csv_files = list(input_path.glob("*.csv"))

    results = {
        "total_files": len(csv_files),
        "valid_files": 0,
        "invalid_files": 0,
        "files": [],
    }

    schema = None
    if schema_file:
        schema = load_schema(schema_file)

    for csv_file in csv_files:
        config = ValidationConfig(
            input_file=str(csv_file),
            encoding=encoding,
        )
        validator = CsvValidator(config)

        try:
            result = validator.validate(schema)
            results["files"].append(
                {
                    "file": str(csv_file.name),
                    "is_valid": result.is_valid,
                    "total_rows": result.total_rows,
                    "errors": len(result.errors),
                }
            )
            if result.is_valid:
                results["valid_files"] += 1
            else:
                results["invalid_files"] += 1
        except Exception as e:
            results["files"].append(
                {
                    "file": str(csv_file.name),
                    "is_valid": False,
                    "error": str(e),
                }
            )
            results["invalid_files"] += 1

    return results


def clean_csv(
    input_file: str,
    output_file: str,
    trim_whitespace: bool = True,
    remove_empty_rows: bool = False,
    normalize_case: str | None = None,
    fill_missing: dict[str, str] | None = None,
    encoding: str = "utf-8",
) -> dict[str, Any]:
    """
    Clean and normalize a CSV file.

    Args:
        input_file: Path to input CSV file
        output_file: Path for cleaned output
        trim_whitespace: Trim whitespace from values
        remove_empty_rows: Remove rows that are entirely empty
        normalize_case: Convert text to 'lower' or 'upper'
        fill_missing: Dict mapping column names to default values
        encoding: File encoding

    Returns:
        Dictionary with cleaning summary
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"CSV file not found: {input_file}")

    rows_read = 0
    rows_written = 0
    rows_removed = 0

    with open(input_path, encoding=encoding, newline="") as infile:
        reader = csv.DictReader(infile)
        headers = reader.fieldnames or []

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding=encoding, newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=headers)
            writer.writeheader()

            for row in reader:
                rows_read += 1

                # Check for empty rows
                if remove_empty_rows:
                    if all(not v or v.strip() == "" for v in row.values()):
                        rows_removed += 1
                        continue

                # Clean values
                cleaned_row = {}
                for key, value in row.items():
                    if value is None:
                        value = ""

                    # Trim whitespace
                    if trim_whitespace:
                        value = value.strip()

                    # Normalize case
                    if normalize_case == "lower":
                        value = value.lower()
                    elif normalize_case == "upper":
                        value = value.upper()

                    # Fill missing
                    if fill_missing and key in fill_missing and value == "":
                        value = fill_missing[key]

                    cleaned_row[key] = value

                writer.writerow(cleaned_row)
                rows_written += 1

    return {
        "success": True,
        "rows_read": rows_read,
        "rows_written": rows_written,
        "rows_removed": rows_removed,
    }


def generate_report(
    result: ValidationResult,
    output_path: str,
    format: str = "text",
) -> None:
    """
    Generate a validation report.

    Args:
        result: ValidationResult to report on
        output_path: Path for the report file
        format: Report format ('text', 'json', 'html')
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        report_data = {
            "is_valid": result.is_valid,
            "total_rows": result.total_rows,
            "valid_rows": result.valid_rows,
            "invalid_rows": result.invalid_rows,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

    elif format == "html":
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>CSV Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .valid {{ color: green; }}
        .invalid {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>CSV Validation Report</h1>
    <div class="summary">
        <p>Status: <span class="{"valid" if result.is_valid else "invalid"}">
            {"Valid" if result.is_valid else "Invalid"}</span></p>
        <p>Total Rows: {result.total_rows}</p>
        <p>Valid Rows: {result.valid_rows}</p>
        <p>Invalid Rows: {result.invalid_rows}</p>
    </div>
"""
        if result.errors:
            html += """
    <h2>Errors</h2>
    <table>
        <tr><th>Row</th><th>Column</th><th>Message</th></tr>
"""
            for error in result.errors:
                html += f"""        <tr>
            <td>{error.get("row", "")}</td>
            <td>{error.get("column", "")}</td>
            <td>{error.get("message", "")}</td>
        </tr>
"""
            html += "    </table>\n"

        html += "</body>\n</html>"

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    else:  # text format
        lines = [
            "CSV Validation Report",
            "=" * 50,
            f"Status: {'Valid' if result.is_valid else 'Invalid'}",
            f"Total Rows: {result.total_rows}",
            f"Valid Rows: {result.valid_rows}",
            f"Invalid Rows: {result.invalid_rows}",
            "",
        ]

        if result.errors:
            lines.append("Errors:")
            lines.append("-" * 30)
            for error in result.errors:
                lines.append(
                    f"  Row {error.get('row', '?')}, "
                    f"Column '{error.get('column', '?')}': "
                    f"{error.get('message', '')}"
                )
            lines.append("")

        if result.warnings:
            lines.append("Warnings:")
            lines.append("-" * 30)
            for warning in result.warnings:
                lines.append(f"  Row {warning.get('row', '?')}: {warning.get('message', '')}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


if __name__ == "__main__":
    print("CSV Data Validator automation")
    print("Use the main CLI: uv run r10n validate")
