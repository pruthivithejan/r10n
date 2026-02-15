"""Tests for the MCP contacts tool."""

import asyncio

from src.mcp.server import mcp
from src.mcp.tools.contacts import generate_contacts


class TestToolRegistered:
    """Verify the generate_contacts tool is registered with the MCP server."""

    def test_tool_registered(self):
        """Tool should appear in the MCP server's tool list."""
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "generate_contacts" in tool_names


class TestGenerateContactsFromFile:
    """Test generate_contacts tool with valid input."""

    def test_generate_contacts_from_file(self, tmp_path):
        """Create a temp input file, call the tool, and verify results."""
        input_file = tmp_path / "numbers.txt"
        input_file.write_text("0771234567\n0781234567\n0791234567\n")
        output_file = tmp_path / "output.vcf"

        result = generate_contacts(
            input_file=str(input_file),
            output_name=str(output_file),
            prefix="Test",
        )

        assert result["total"] == 3
        assert result["valid"] == 3
        assert result["duplicates"] == 0
        assert result["invalid"] == 0
        assert output_file.exists()

        content = output_file.read_text()
        assert content.count("BEGIN:VCARD") == 3
        assert "FN:Test 1" in content


class TestGenerateContactsFileNotFound:
    """Test error handling when input file does not exist."""

    def test_generate_contacts_file_not_found(self):
        """Should return an error dict instead of raising."""
        result = generate_contacts(input_file="nonexistent_file.txt")
        assert "error" in result
        assert "not found" in result["error"].lower()
