"""MCP tool for validating CSV files."""

from src.automations.validate_csv import validate_csv as _validate_csv
from src.mcp.server import mcp


@mcp.tool()
def validate_csv(
    input_file: str,
    schema_file: str | None = None,
    output_file: str | None = None,
    strict_mode: bool = False,
) -> dict:
    """Validate CSV files against a schema with optional cleaning.

    Args:
        input_file: Path to CSV file to validate.
        schema_file: Path to JSON schema file for validation rules.
        output_file: Path for cleaned output CSV file.
        strict_mode: Fail on warnings in addition to errors.
    """
    try:
        result = _validate_csv(
            input_file=input_file,
            schema_file=schema_file,
            output_file=output_file,
            strict_mode=strict_mode,
        )
        return {
            "is_valid": result.is_valid,
            "total_rows": result.total_rows,
            "valid_rows": result.valid_rows,
            "invalid_rows": result.invalid_rows,
            "errors": [str(e) for e in result.errors],
            "warnings": [str(w) for w in result.warnings],
        }
    except Exception as e:
        return {"error": str(e)}
