"""Tests for the MCP CLI command."""

from click.testing import CliRunner

from src.cli import main


class TestMcpCommand:
    """Test the r10n mcp CLI command."""

    def test_mcp_command_exists(self):
        """Verify the mcp command is registered."""
        runner = CliRunner()
        result = runner.invoke(main, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "MCP" in result.output or "mcp" in result.output.lower()
