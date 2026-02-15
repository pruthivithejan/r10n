"""MCP tool for certificate generation."""

from src.automations.fill_certificates import fill_certificates_from_file
from src.mcp.server import mcp


@mcp.tool()
def generate_certificates(
    recipients_file: str,
    config_file: str,
    base_dir: str = "data/certificates",
) -> dict:
    """Generate personalized PDF certificates from a template.

    Args:
        recipients_file: Path to CSV/TXT file with recipient data.
        config_file: Path to JSON configuration file with template, font, and field positions.
        base_dir: Base directory for resolving relative paths in config.
    """
    try:
        return fill_certificates_from_file(recipients_file, config_file, base_dir)
    except Exception as e:
        return {"error": str(e)}
