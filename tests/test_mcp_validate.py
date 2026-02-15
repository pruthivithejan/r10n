"""Tests for the MCP validate tool."""

import asyncio

from src.mcp.server import mcp


class TestValidateTool:
    """Test the validate_csv MCP tool."""

    def test_tool_registered(self):
        """Verify validate_csv tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "validate_csv" in tool_names

    def test_validate_csv(self, tmp_path):
        """Test CSV validation."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,email\nJohn,john@example.com\n")

        from src.mcp.tools.validate import validate_csv

        result = validate_csv(input_file=str(csv_file))
        assert result["is_valid"] is True
        assert result["total_rows"] == 1

    def test_missing_file(self):
        """Test error handling for missing file."""
        from src.mcp.tools.validate import validate_csv

        result = validate_csv(input_file="/nonexistent/file.csv")
        assert "error" in result
