"""Tests for the MCP email tool."""

import asyncio

from src.mcp.server import mcp


class TestEmailTool:
    """Test the send_email MCP tool."""

    def test_tool_registered(self):
        """Verify send_email tool is registered."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "send_email" in tool_names

    def test_missing_config_returns_zero_sent(self):
        """Test that missing config results in no emails sent."""
        from src.mcp.tools.email import send_email

        result = send_email(
            email_list_file="/nonexistent/list.csv",
            subject="Test",
            body_template="/nonexistent/body.txt",
            config_file="/nonexistent/config.json",
        )
        # The email automation handles errors internally, returning zero counts
        assert result.get("sent", 0) == 0
