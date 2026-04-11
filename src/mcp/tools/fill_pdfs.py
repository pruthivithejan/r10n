"""MCP tool for PDF filling."""

from src.automations.fill_pdfs import fill_certificates_from_file
from src.mcp.server import mcp


@mcp.tool()
def fill_pdfs(
    recipients_file: str,
    config_file: str,
    base_dir: str = "data/fill-pdfs",
) -> dict:
    """Fill PDF templates with data from a CSV/TXT file.

    Args:
        recipients_file: Path to CSV/TXT file with row data.
        config_file: Path to JSON configuration file with template, font, and field positions.
        base_dir: Base directory for resolving relative paths in config.
    """
    try:
        return fill_certificates_from_file(recipients_file, config_file, base_dir)
    except Exception as e:
        return {"error": str(e)}
