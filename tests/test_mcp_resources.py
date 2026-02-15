"""Tests for MCP resources."""

import asyncio
import json

from src.mcp.server import mcp


class TestMcpResources:
    """Test MCP resource registration and access."""

    def test_automations_resource_registered(self):
        """Verify r10n://automations resource is registered."""
        resources = asyncio.run(mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert "r10n://automations" in uris

    def test_config_resources_registered(self):
        """Verify config resources are registered."""
        resources = asyncio.run(mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert "r10n://configs/certificates" in uris
        assert "r10n://configs/email" in uris
        assert "r10n://configs/images" in uris
        assert "r10n://configs/blog" in uris

    def test_automations_resource_content(self):
        """Verify automations resource returns valid JSON with all tools."""
        from src.mcp.resources.configs import list_automations

        content = list_automations()
        automations = json.loads(content)
        names = [a["name"] for a in automations]
        assert len(automations) == 8
        assert "generate_contacts" in names
        assert "validate_csv" in names

    def test_certificates_config_content(self):
        """Verify certificates config resource returns valid JSON."""
        from src.mcp.resources.configs import certificates_config

        content = certificates_config()
        config = json.loads(content)
        assert "fields" in config
