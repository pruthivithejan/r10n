import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.automations.generate_contacts import (
    clean_number,
    generate_vcf_from_file,
    generate_vcf,
)


class TestCleanNumber:
    """Test phone number cleaning functionality."""

    def test_clean_sri_lanka_number_starting_with_zero(self):
        """Test cleaning Sri Lankan number starting with 0."""
        result = clean_number("0771234567")
        assert result == "+94771234567"

    def test_clean_sri_lanka_number_without_country_code(self):
        """Test cleaning Sri Lankan number without country code."""
        result = clean_number("771234567")
        assert result == "+94771234567"

    def test_clean_number_with_country_code(self):
        """Test cleaning number that already has country code."""
        result = clean_number("+94771234567")
        assert result == "+94771234567"

    def test_clean_number_with_spaces_and_dashes(self):
        """Test cleaning number with formatting."""
        result = clean_number("077-123-4567")
        assert result == "+94771234567"

    def test_clean_invalid_number_too_short(self):
        """Test cleaning invalid short number."""
        result = clean_number("077123")
        assert result is None

    def test_clean_invalid_number_too_long(self):
        """Test cleaning invalid long number."""
        result = clean_number("07712345678901")
        assert result is None

    def test_clean_empty_string(self):
        """Test cleaning empty string."""
        result = clean_number("")
        assert result is None

    def test_clean_non_numeric_string(self):
        """Test cleaning non-numeric string."""
        result = clean_number("not a number")
        assert result is None


class TestGenerateVcfFromFile:
    """Test VCF generation from file."""

    def test_generate_vcf_from_valid_file(self):
        """Test generating VCF from a valid input file."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("0771234567\n0781234567\n0791234567\n")
            input_file = f.name

        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_contacts.vcf"
            
            result = generate_vcf_from_file(input_file, str(output_file), "Test")
            
            # Check results
            assert result["total"] == 3
            assert result["valid"] == 3
            assert result["duplicates"] == 0
            assert result["invalid"] == 0
            assert result["output_file"] == str(output_file)
            
            # Check VCF file content
            with open(output_file) as f:
                content = f.read()
            
            assert "BEGIN:VCARD" in content
            assert "VERSION:3.0" in content
            assert "FN:Test 1" in content
            assert "TEL;TYPE=CELL:+94771234567" in content
            assert "END:VCARD" in content

        # Cleanup
        Path(input_file).unlink()

    def test_generate_vcf_with_duplicates(self):
        """Test VCF generation with duplicate numbers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("0771234567\n0771234567\n0781234567\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_contacts.vcf"
            
            result = generate_vcf_from_file(input_file, str(output_file))
            
            assert result["total"] == 3
            assert result["valid"] == 2  # One duplicate removed
            assert result["duplicates"] == 1
            assert result["invalid"] == 0

        Path(input_file).unlink()

    def test_generate_vcf_with_invalid_numbers(self):
        """Test VCF generation with invalid numbers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("0771234567\ninvalid_number\n077123\n")
            input_file = f.name

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_contacts.vcf"
            
            result = generate_vcf_from_file(input_file, str(output_file))
            
            assert result["total"] == 3
            assert result["valid"] == 1
            assert result["duplicates"] == 0
            assert result["invalid"] == 2

        Path(input_file).unlink()

    def test_generate_vcf_file_not_found(self):
        """Test VCF generation with non-existent input file."""
        with pytest.raises(FileNotFoundError):
            generate_vcf_from_file("non_existent_file.txt")

    def test_generate_vcf_auto_output_filename(self):
        """Test VCF generation with auto-generated output filename."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("0771234567\n")
            input_file = f.name

        with tempfile.TemporaryDirectory():
            # Mock the workspace directory check
            with patch('src.automations.generate_contacts.Path') as mock_path:
                # Configure mock to return True for input file (first call) and False for workspace (subsequent calls)
                # or use side_effect to check path
                def exists_side_effect():
                    # The mock is called multiple times. 
                    # 1. Path(input_file).exists() -> needs True
                    # 2. Path("workspace/...").exists() -> needs False
                    # But mock_path is the CLASS. mock_path(input_file) returns a Mock instance.
                    # That instance's .exists() is called.
                    # Since we can't easily distinguish instances, we'll make .exists() return True by default
                    # but we need it to be False for the directory check if we want to test the fallback?
                    # Actually, the test just asserts output filename.
                    return True
                
                # We need to handle the fact that Path(input_file) and Path("workspace...") return different mocks
                # unless we configure the class return value.
                
                # Let's just make exists() return True for the input file.
                # The code: input_path = Path(input_file); if not input_path.exists(): ...
                
                # We can use a side effect on the instance's exists method
                mock_instance = mock_path.return_value
                mock_instance.exists.side_effect = [True, False, False, False] # Input exists, others don't
                
                mock_instance.stem = "test_input"
                mock_instance.is_absolute.return_value = False
                mock_instance.parts = ["test_input_contacts.vcf"]
                
                # Create a real Path object for the parent
                real_output_path = Path(input_file).parent / "test_input_contacts.vcf"
                mock_instance.parent.mkdir = MagicMock()
                
                result = generate_vcf_from_file(input_file)
                
                assert "test_input_contacts.vcf" in result["output_file"]

        Path(input_file).unlink()

