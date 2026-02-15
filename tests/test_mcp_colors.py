"""Tests for the MCP colors tool."""

import asyncio

from src.mcp.server import mcp


class TestColorsTool:
    """Test the convert_colors MCP tool."""

    def test_tool_registered(self):
        """Verify convert_colors tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "convert_colors" in tool_names

    def test_convert_colors_dry_run(self, tmp_path):
        """Test color conversion in dry-run mode."""
        css_file = tmp_path / "test.css"
        css_file.write_text("body { color: #ff0000; }")

        from src.mcp.tools.colors import convert_colors

        result = convert_colors(path=str(tmp_path), dry_run=True)
        assert result["files_found"] >= 1
        assert result["dry_run"] is True

    def test_missing_path(self):
        """Test error handling for missing path."""
        from src.mcp.tools.colors import convert_colors

        result = convert_colors(path="/nonexistent/dir")
        assert "error" in result
