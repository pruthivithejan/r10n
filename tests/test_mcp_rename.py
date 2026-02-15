"""Tests for the MCP rename tool."""

import asyncio

from src.mcp.server import mcp


class TestRenameTool:
    """Test the rename_files MCP tool."""

    def test_tool_registered(self):
        """Verify rename_files tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "rename_files" in tool_names

    def test_rename_dry_run(self, tmp_path):
        """Test rename in dry-run mode."""
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "file2.txt").write_text("b")

        from src.mcp.tools.rename import rename_files

        result = rename_files(
            input_directory=str(tmp_path),
            prefix="renamed_",
            dry_run=True,
        )
        assert result["total_files"] >= 2
        assert result["renamed"] >= 2

    def test_missing_directory(self):
        """Test error handling for missing directory."""
        from src.mcp.tools.rename import rename_files

        result = rename_files(input_directory="/nonexistent/dir")
        assert "error" in result
