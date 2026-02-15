"""MCP tool for contact card generation."""

from src.automations.generate_contacts import generate_vcf_from_file
from src.mcp.server import mcp


@mcp.tool()
def generate_contacts(
    input_file: str,
    output_name: str = "contacts.vcf",
    prefix: str = "Contact",
) -> dict:
    """Generate VCF contact cards from a text file containing phone numbers.

    Args:
        input_file: Path to text file containing phone numbers (one per line).
        output_name: Path/name of the output VCF file.
        prefix: Prefix to use for contact names.

    Returns:
        dict with total, valid, duplicates, invalid counts and output_file path,
        or {"error": ...} on failure.
    """
    try:
        return generate_vcf_from_file(input_file, output_name, prefix)
    except Exception as e:
        return {"error": str(e)}
