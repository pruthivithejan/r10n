"""Tests for the MCP certificates tool."""

import asyncio

from src.mcp.server import mcp


class TestCertificatesTool:
    """Test the generate_certificates MCP tool."""

    def test_tool_registered(self):
        """Verify generate_certificates tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "generate_certificates" in tool_names

    def test_missing_config_file(self):
        """Test error handling for missing config."""
        from src.mcp.tools.certificates import generate_certificates

        result = generate_certificates(
            recipients_file="/nonexistent/recipients.csv",
            config_file="/nonexistent/config.json",
        )
        assert "error" in result
