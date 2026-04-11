"""
Tests for the contact card generation automation.

These tests verify the VCF contact card generation functionality
both for local usage and uvx distribution.
"""

import tempfile
from pathlib import Path

import pytest

from src.automations.generate_contacts import (
    clean_number,
    generate_vcf,
    generate_vcf_from_file,
)


class TestCleanNumber:
    """Test phone number cleaning functionality."""

    def test_number_starting_with_zero(self):
        """Test Sri Lankan number starting with 0."""
        assert clean_number("0771234567") == "+94771234567"

    def test_number_without_country_code(self):
        """Test number without country code."""
        assert clean_number("771234567") == "+94771234567"

    def test_number_with_country_code(self):
        """Test number with country code."""
        assert clean_number("+94771234567") == "+94771234567"

    def test_number_with_94_prefix(self):
        """Test number starting with 94."""
        assert clean_number("94771234567") == "+94771234567"

    def test_number_with_formatting(self):
        """Test number with spaces and dashes."""
        assert clean_number("077-123-4567") == "+94771234567"
        assert clean_number("077 123 4567") == "+94771234567"

    def test_invalid_short_number(self):
        """Test invalid short number."""
        assert clean_number("077123") is None

    def test_invalid_long_number(self):
        """Test invalid long number."""
        assert clean_number("07712345678901") is None

    def test_empty_string(self):
        """Test empty string."""
        assert clean_number("") is None

    def test_non_numeric_string(self):
        """Test non-numeric string."""
        assert clean_number("not a number") is None


class TestGenerateVcfFromFile:
    """Test VCF generation from file."""

    def test_default_output_path_uses_local_contacts_directory(self, monkeypatch, tmp_path):
        """Test bare output filenames are written to local/outputs/contacts."""
        monkeypatch.chdir(tmp_path)
        input_file = tmp_path / "numbers.txt"
        input_file.write_text("0771234567\n", encoding="utf-8")

        result = generate_vcf_from_file(str(input_file), "contacts.vcf", "Team")

        expected_output = tmp_path / "local" / "outputs" / "contacts" / "contacts.vcf"
        assert Path(result["output_file"]) == Path("local/outputs/contacts/contacts.vcf")
        assert expected_output.exists()
        assert "FN:Team 1" in expected_output.read_text(encoding="utf-8")

    def test_valid_numbers(self):
        """Test generating VCF with valid numbers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("0771234567\n0781234567\n0791234567\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contacts.vcf"

            result = generate_vcf_from_file(input_file, str(output_file), "Test")

            assert result["total"] == 3
            assert result["valid"] == 3
            assert result["duplicates"] == 0
            assert result["invalid"] == 0

            # Verify VCF content
            content = output_file.read_text()
            assert "BEGIN:VCARD" in content
            assert "VERSION:3.0" in content
            assert "FN:Test 1" in content
            assert "+94771234567" in content
            assert content.count("END:VCARD") == 3

        Path(input_file).unlink()

    def test_duplicate_removal(self):
        """Test duplicate numbers are removed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("0771234567\n0771234567\n+94771234567\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contacts.vcf"

            result = generate_vcf_from_file(input_file, str(output_file))

            assert result["total"] == 3
            assert result["valid"] == 1  # All same number
            assert result["duplicates"] == 2

        Path(input_file).unlink()

    def test_invalid_numbers_skipped(self):
        """Test invalid numbers are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("0771234567\ninvalid\n123\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contacts.vcf"

            result = generate_vcf_from_file(input_file, str(output_file))

            assert result["total"] == 3
            assert result["valid"] == 1
            assert result["invalid"] == 2

        Path(input_file).unlink()

    def test_comments_ignored(self):
        """Test comment lines are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# This is a comment\n0771234567\n# Another comment\n0781234567\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contacts.vcf"

            result = generate_vcf_from_file(input_file, str(output_file))

            assert result["total"] == 2  # Comments excluded from total
            assert result["valid"] == 2

        Path(input_file).unlink()

    def test_file_not_found(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            generate_vcf_from_file("nonexistent_file.txt")


class TestGenerateVcf:
    """Test VCF generation from string input."""

    def test_from_string(self):
        """Test generating VCF from string."""
        numbers = """
        0771234567
        0781234567
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "contacts.vcf"

            result = generate_vcf(numbers, str(output_file), "Contact")

            assert result["valid"] == 2
            assert Path(result["output_file"]).exists()


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx.

    These tests verify the package can be imported and used
    without a local folder structure.
    """

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import generate_contacts
        assert hasattr(generate_contacts, "generate_vcf_from_file")
        assert hasattr(generate_contacts, "generate_vcf")
        assert hasattr(generate_contacts, "clean_number")

    def test_output_to_absolute_path(self):
        """Test output to absolute path works without local folder."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("0771234567\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            # Use absolute path for output
            output_file = Path(temp_dir) / "output.vcf"

            result = generate_vcf_from_file(
                input_file,
                str(output_file),  # Absolute path
                "Test"
            )

            assert result["valid"] == 1
            assert output_file.exists()

        Path(input_file).unlink()
