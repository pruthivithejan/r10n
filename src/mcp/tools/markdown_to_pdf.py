"""MCP tool for converting Markdown to PDF."""

from src.automations.markdown_to_pdf import convert_markdown_to_pdf as _convert_markdown_to_pdf
from src.mcp.server import mcp


@mcp.tool()
def convert_markdown_to_pdf(
    input_path: str,
    output_path: str | None = None,
    css_file: str | None = None,
    page_size: str = "A4",
    margin_top: int = 20,
    margin_bottom: int = 20,
    include_toc: bool = False,
) -> dict:
    """Convert Markdown documents to styled PDF files.

    Args:
        input_path: Path to markdown file.
        output_path: Output PDF file path (auto-generated if not provided).
        css_file: Path to custom CSS file for styling.
        page_size: Page size - "A4" or "Letter".
        margin_top: Top margin in mm.
        margin_bottom: Bottom margin in mm.
        include_toc: Include table of contents.
    """
    try:
        return _convert_markdown_to_pdf(
            input_path=input_path,
            output_path=output_path,
            css_file=css_file,
            page_size=page_size,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            include_toc=include_toc,
        )
    except Exception as e:
        return {"error": str(e)}
