"""Tests for the MCP markdown-to-pdf tool."""

import asyncio

from src.mcp.server import mcp


class TestMarkdownToPdfTool:
    """Test the convert_markdown_to_pdf MCP tool."""

    def test_tool_registered(self):
        """Verify convert_markdown_to_pdf tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "convert_markdown_to_pdf" in tool_names

    def test_convert_markdown(self, tmp_path):
        """Test markdown to PDF conversion."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nThis is a test.\n")
        output_file = tmp_path / "test.pdf"

        from src.mcp.tools.markdown_to_pdf import convert_markdown_to_pdf

        result = convert_markdown_to_pdf(
            input_path=str(md_file),
            output_path=str(output_file),
        )
        assert result.get("success") is True
        assert output_file.exists()

    def test_missing_file(self):
        """Test error handling for missing file."""
        from src.mcp.tools.markdown_to_pdf import convert_markdown_to_pdf

        result = convert_markdown_to_pdf(input_path="/nonexistent/file.md")
        assert "error" in result
