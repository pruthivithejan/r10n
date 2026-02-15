"""Tests for the MCP images tool."""

import asyncio

from src.mcp.server import mcp


class TestImagesTool:
    """Test the optimize_images MCP tool."""

    def test_tool_registered(self):
        """Verify optimize_images tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "optimize_images" in tool_names

    def test_missing_input_dir(self):
        """Test error handling for missing directory."""
        from src.mcp.tools.images import optimize_images

        result = optimize_images(input_dir="/nonexistent/dir")
        assert "error" in result
