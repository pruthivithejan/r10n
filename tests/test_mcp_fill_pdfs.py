"""Tests for the MCP fill-pdfs tool."""

import asyncio

from src.mcp.server import mcp


class TestFillPdfsTool:
    """Test the fill_pdfs MCP tool."""

    def test_tool_registered(self):
        """Verify fill_pdfs tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "fill_pdfs" in tool_names

    def test_missing_config_file(self):
        """Test error handling for missing config."""
        from src.mcp.tools.fill_pdfs import fill_pdfs

        result = fill_pdfs(
            recipients_file="/nonexistent/recipients.csv",
            config_file="/nonexistent/config.json",
        )
        assert "error" in result
