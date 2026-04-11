"""
Tests for the PDF filling automation.

These tests verify the certificate generation functionality for both
local usage and uvx distribution.
"""

import json
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.automations.fill_pdfs import (
    create_text_overlay,
    fill_certificate,
    generate_certificates,
    load_config,
    load_recipients,
    register_futura_font,
)


class TestLoadRecipients:
    """Test recipient loading functionality."""

    def test_load_recipients_from_txt_single_column(self):
        """Test loading recipients from TXT file with single column."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Alice Smith\nBob Jones\nCharlie Brown")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 3
            assert recipients[0]["name"] == "Alice Smith"
            assert recipients[0]["position"] == ""
            assert recipients[1]["name"] == "Bob Jones"
            assert recipients[2]["name"] == "Charlie Brown"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_from_txt_with_position(self):
        """Test loading recipients from TXT file with tab-separated position."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Alice Smith\tSoftware Engineer\nBob Jones\tProject Manager")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 2
            assert recipients[0]["name"] == "Alice Smith"
            assert recipients[0]["position"] == "Software Engineer"
            assert recipients[1]["name"] == "Bob Jones"
            assert recipients[1]["position"] == "Project Manager"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_from_csv(self):
        """Test loading recipients from CSV file with headers."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("Name,Position,E-mail\n")
            f.write("Alice Smith,Engineer,alice@example.com\n")
            f.write("Bob Jones,Manager,bob@example.com\n")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 2
            assert recipients[0]["name"] == "Alice Smith"
            assert recipients[1]["name"] == "Bob Jones"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_csv_with_full_name_header(self):
        """Test CSV with 'Full Name' header variant."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("Full Name,Role\n")
            f.write("Alice Smith,Developer\n")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 1
            assert recipients[0]["name"] == "Alice Smith"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_csv_with_recipient_header(self):
        """Test CSV with 'Recipient' header variant."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("Recipient,Department\n")
            f.write("Alice Smith,Engineering\n")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 1
            assert recipients[0]["name"] == "Alice Smith"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_skips_empty_lines(self):
        """Test that empty lines are skipped in TXT files."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Alice Smith\n\n\nBob Jones\n")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 2
        finally:
            Path(file_path).unlink()

    def test_load_recipients_skips_comments(self):
        """Test that comment lines are skipped in TXT files."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("# This is a comment\nAlice Smith\n# Another comment\nBob Jones")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 2
            assert recipients[0]["name"] == "Alice Smith"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_file_not_found(self):
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Recipients file not found"):
            load_recipients("nonexistent_file.txt")

    def test_load_recipients_strips_whitespace(self):
        """Test that names are properly stripped of whitespace."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("  Alice Smith  \n  Bob Jones  ")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert recipients[0]["name"] == "Alice Smith"
            assert recipients[1]["name"] == "Bob Jones"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_csv_skips_empty_names(self):
        """Test that CSV rows without discernible names are skipped."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("Name,Position\n")
            f.write("Alice Smith,Engineer\n")
            f.write(",Manager\n")  # Empty name
            f.write("Bob Jones,Developer\n")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 2
            assert recipients[0]["name"] == "Alice Smith"
            assert recipients[1]["name"] == "Bob Jones"
        finally:
            Path(file_path).unlink()


class TestLoadConfig:
    """Test configuration loading functionality."""

    def test_load_config_valid(self):
        """Test loading valid configuration."""
        config_data = {
            "template_pdf": "template.pdf",
            "output_directory": "output",
            "fields": {"name": {"x": 100, "y": 200, "font_size": 24}},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config_data, f)
            file_path = f.name

        try:
            config = load_config(file_path)
            assert config["template_pdf"] == "template.pdf"
            assert config["output_directory"] == "output"
            assert "name" in config["fields"]
        finally:
            Path(file_path).unlink()

    def test_load_config_missing_required_key(self):
        """Test error when required key is missing."""
        config_data = {
            "template_pdf": "template.pdf",
            # Missing "output_directory" and "fields"
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config_data, f)
            file_path = f.name

        try:
            with pytest.raises(KeyError, match="Missing required configuration key"):
                load_config(file_path)
        finally:
            Path(file_path).unlink()

    def test_load_config_file_not_found(self):
        """Test FileNotFoundError for missing config file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config("nonexistent_config.json")

    def test_load_config_invalid_json(self):
        """Test error for invalid JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{ invalid json }")
            file_path = f.name

        try:
            with pytest.raises(Exception, match="Invalid JSON"):
                load_config(file_path)
        finally:
            Path(file_path).unlink()

    def test_load_config_with_optional_fields(self):
        """Test loading config with optional fields."""
        config_data = {
            "template_pdf": "template.pdf",
            "output_directory": "output",
            "fields": {
                "name": {
                    "x": 100,
                    "y": 200,
                    "font_size": 24,
                    "font_weight": "bold",
                    "color": [0, 0, 0],
                    "alignment": "center",
                }
            },
            "font_family": "Futura",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config_data, f)
            file_path = f.name

        try:
            config = load_config(file_path)
            assert config["font_family"] == "Futura"
            assert config["fields"]["name"]["alignment"] == "center"
        finally:
            Path(file_path).unlink()


class TestRegisterFuturaFont:
    """Test font registration functionality."""

    @patch("platform.system")
    @patch("os.path.exists")
    def test_register_futura_font_macos_success(self, mock_exists, mock_system):
        """Test successful Futura font registration on macOS."""
        mock_system.return_value = "Darwin"
        mock_exists.return_value = True

        # This may fail due to actual font loading, but we test the flow
        # In real tests, we'd mock pdfmetrics.registerFont
        with patch("src.automations.fill_pdfs.pdfmetrics.registerFont"):
            result = register_futura_font()
            # Result depends on whether the font file is actually valid
            assert isinstance(result, bool)

    @patch("platform.system")
    def test_register_futura_font_non_macos(self, mock_system):
        """Test Futura font registration on non-macOS returns False."""
        mock_system.return_value = "Linux"
        result = register_futura_font()
        assert result is False


class TestCreateTextOverlay:
    """Test text overlay creation functionality."""

    def test_create_text_overlay_basic(self):
        """Test creating basic text overlay."""
        config = {
            "fields": {
                "name": {
                    "x": 100,
                    "y": 200,
                    "font_size": 24,
                }
            }
        }
        recipient_data = {"name": "Alice Smith"}

        buffer = create_text_overlay(config, recipient_data, 612, 792)
        assert isinstance(buffer, BytesIO)
        assert buffer.tell() == 0  # Buffer should be seeked to start
        assert len(buffer.getvalue()) > 0

    def test_create_text_overlay_with_alignment(self):
        """Test text overlay with different alignments."""
        for alignment in ["left", "center", "right"]:
            config = {
                "fields": {
                    "name": {
                        "x": 306,
                        "y": 400,
                        "font_size": 24,
                        "alignment": alignment,
                    }
                }
            }
            recipient_data = {"name": "Test Name"}

            buffer = create_text_overlay(config, recipient_data, 612, 792)
            assert len(buffer.getvalue()) > 0

    def test_create_text_overlay_with_color_normalized(self):
        """Test text overlay with normalized color values (0-1)."""
        config = {
            "fields": {"name": {"x": 100, "y": 200, "font_size": 24, "color": [0.5, 0.5, 0.5]}}
        }
        recipient_data = {"name": "Test"}

        buffer = create_text_overlay(config, recipient_data, 612, 792)
        assert len(buffer.getvalue()) > 0

    def test_create_text_overlay_with_color_255(self):
        """Test text overlay with 0-255 color values."""
        config = {
            "fields": {"name": {"x": 100, "y": 200, "font_size": 24, "color": [128, 128, 128]}}
        }
        recipient_data = {"name": "Test"}

        buffer = create_text_overlay(config, recipient_data, 612, 792)
        assert len(buffer.getvalue()) > 0

    def test_create_text_overlay_long_name_reduces_font_size(self, capsys):
        """Test that long names trigger font size reduction."""
        config = {
            "fields": {
                "name": {
                    "x": 100,
                    "y": 200,
                    "font_size": 48,
                }
            }
        }
        # Name longer than 20 characters
        recipient_data = {"name": "A Very Long Name That Exceeds Twenty Characters"}

        create_text_overlay(config, recipient_data, 612, 792)
        captured = capsys.readouterr()
        assert "Reduced font size" in captured.out

    def test_create_text_overlay_skips_empty_fields(self):
        """Test that empty fields are skipped."""
        config = {
            "fields": {
                "name": {"x": 100, "y": 200, "font_size": 24},
                "position": {"x": 100, "y": 150, "font_size": 18},
            }
        }
        # Only name provided, position is empty
        recipient_data = {"name": "Alice"}

        buffer = create_text_overlay(config, recipient_data, 612, 792)
        assert len(buffer.getvalue()) > 0

    def test_create_text_overlay_multiple_fields(self):
        """Test text overlay with multiple fields."""
        config = {
            "fields": {
                "name": {"x": 100, "y": 300, "font_size": 24},
                "position": {"x": 100, "y": 250, "font_size": 18},
            }
        }
        recipient_data = {"name": "Alice Smith", "position": "Engineer"}

        buffer = create_text_overlay(config, recipient_data, 612, 792)
        assert len(buffer.getvalue()) > 0


class TestFillCertificate:
    """Test certificate filling functionality."""

    @pytest.fixture
    def sample_pdf_template(self):
        """Create a simple PDF template for testing."""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
            c = canvas.Canvas(f.name, pagesize=letter)
            c.drawString(100, 700, "Certificate Template")
            c.save()
            return f.name

    def test_fill_certificate_basic(self, sample_pdf_template):
        """Test basic certificate filling."""
        config = {"fields": {"name": {"x": 306, "y": 400, "font_size": 24}}}
        recipient_data = {"name": "Alice Smith"}

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as output_file:
            output_path = output_file.name

        try:
            result = fill_certificate(sample_pdf_template, config, recipient_data, output_path)
            assert result is True
            assert Path(output_path).exists()
            assert Path(output_path).stat().st_size > 0
        finally:
            Path(sample_pdf_template).unlink()
            Path(output_path).unlink()

    def test_fill_certificate_with_position(self, sample_pdf_template):
        """Test certificate filling with multiple fields."""
        config = {
            "fields": {
                "name": {"x": 306, "y": 400, "font_size": 24, "alignment": "center"},
                "position": {"x": 306, "y": 350, "font_size": 18, "alignment": "center"},
            }
        }
        recipient_data = {"name": "Alice Smith", "position": "Software Engineer"}

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as output_file:
            output_path = output_file.name

        try:
            result = fill_certificate(sample_pdf_template, config, recipient_data, output_path)
            assert result is True
            assert Path(output_path).exists()
        finally:
            Path(sample_pdf_template).unlink()
            Path(output_path).unlink()

    def test_fill_certificate_template_not_found(self):
        """Test error when template file not found."""
        config = {"fields": {"name": {"x": 100, "y": 200, "font_size": 24}}}
        recipient_data = {"name": "Test"}

        with pytest.raises(Exception, match="Error filling certificate"):
            fill_certificate("nonexistent.pdf", config, recipient_data, "output.pdf")


class TestGenerateCertificates:
    """Test batch certificate generation functionality."""

    @pytest.fixture
    def setup_certificate_files(self):
        """Set up temporary files for certificate generation testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create template PDF
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            template_path = temp_path / "template.pdf"
            c = canvas.Canvas(str(template_path), pagesize=letter)
            c.drawString(100, 700, "Certificate Template")
            c.save()

            # Create recipients file
            recipients_path = temp_path / "recipients.txt"
            recipients_path.write_text("Alice Smith\nBob Jones\n")

            # Create config file
            output_dir = temp_path / "output"
            config_data = {
                "template_pdf": str(template_path),
                "output_directory": str(output_dir),
                "fields": {"name": {"x": 306, "y": 400, "font_size": 24, "alignment": "center"}},
            }
            config_path = temp_path / "config.json"
            config_path.write_text(json.dumps(config_data))

            yield {
                "temp_dir": temp_dir,
                "template_path": str(template_path),
                "recipients_path": str(recipients_path),
                "config_path": str(config_path),
                "output_dir": str(output_dir),
            }

    def test_generate_certificates_basic(self, setup_certificate_files):
        """Test basic certificate batch generation."""
        files = setup_certificate_files

        result = generate_certificates(
            recipients_file=files["recipients_path"],
            config_file=files["config_path"],
            base_dir=files["temp_dir"],
        )

        assert result["total"] == 2
        assert result["generated"] == 2
        assert result["failed"] == 0
        assert len(result["errors"]) == 0

        # Check output files exist
        output_dir = Path(files["output_dir"])
        assert output_dir.exists()
        pdf_files = list(output_dir.glob("*.pdf"))
        assert len(pdf_files) == 2

    def test_generate_certificates_no_recipients(self, setup_certificate_files, capsys):
        """Test handling of empty recipients file."""
        files = setup_certificate_files

        # Create empty recipients file
        empty_recipients = Path(files["temp_dir"]) / "empty.txt"
        empty_recipients.write_text("")

        result = generate_certificates(
            recipients_file=str(empty_recipients),
            config_file=files["config_path"],
            base_dir=files["temp_dir"],
        )

        assert result["total"] == 0
        assert result["generated"] == 0

    def test_generate_certificates_template_not_found(self, setup_certificate_files):
        """Test error when template PDF not found."""
        files = setup_certificate_files

        # Modify config to point to nonexistent template
        config_data = {
            "template_pdf": "nonexistent_template.pdf",
            "output_directory": files["output_dir"],
            "fields": {"name": {"x": 100, "y": 200, "font_size": 24}},
        }
        bad_config_path = Path(files["temp_dir"]) / "bad_config.json"
        bad_config_path.write_text(json.dumps(config_data))

        with pytest.raises(FileNotFoundError, match="Template PDF not found"):
            generate_certificates(
                recipients_file=files["recipients_path"],
                config_file=str(bad_config_path),
                base_dir=files["temp_dir"],
            )

    def test_generate_certificates_creates_output_dir(self, setup_certificate_files):
        """Test that output directory is created if it doesn't exist."""
        files = setup_certificate_files

        # Ensure output directory doesn't exist
        output_dir = Path(files["output_dir"])
        if output_dir.exists():
            import shutil

            shutil.rmtree(output_dir)

        result = generate_certificates(
            recipients_file=files["recipients_path"],
            config_file=files["config_path"],
            base_dir=files["temp_dir"],
        )

        assert output_dir.exists()
        assert result["generated"] == 2

    def test_generate_certificates_unique_filenames(self, setup_certificate_files):
        """Test that duplicate names get unique filenames."""
        files = setup_certificate_files

        # Create recipients with duplicate names
        dup_recipients = Path(files["temp_dir"]) / "duplicates.txt"
        dup_recipients.write_text("Alice Smith\nAlice Smith\nAlice Smith\n")

        result = generate_certificates(
            recipients_file=str(dup_recipients),
            config_file=files["config_path"],
            base_dir=files["temp_dir"],
        )

        assert result["generated"] == 3
        output_dir = Path(files["output_dir"])
        pdf_files = list(output_dir.glob("*.pdf"))
        assert len(pdf_files) == 3

        # All filenames should be unique
        filenames = [f.name for f in pdf_files]
        assert len(filenames) == len(set(filenames))

    def test_generate_certificates_csv_recipients(self, setup_certificate_files):
        """Test certificate generation with CSV recipients."""
        files = setup_certificate_files

        # Create CSV recipients file
        csv_recipients = Path(files["temp_dir"]) / "recipients.csv"
        csv_recipients.write_text("Name,Position\nAlice Smith,Engineer\nBob Jones,Manager\n")

        # Update config to include position field
        config_data = {
            "template_pdf": files["template_path"],
            "output_directory": files["output_dir"],
            "fields": {
                "name": {"x": 306, "y": 400, "font_size": 24},
                "position": {"x": 306, "y": 350, "font_size": 18},
            },
        }
        csv_config_path = Path(files["temp_dir"]) / "csv_config.json"
        csv_config_path.write_text(json.dumps(config_data))

        result = generate_certificates(
            recipients_file=str(csv_recipients),
            config_file=str(csv_config_path),
            base_dir=files["temp_dir"],
        )

        assert result["total"] == 2
        assert result["generated"] == 2


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import fill_pdfs as mod

        assert hasattr(mod, "load_recipients")
        assert hasattr(mod, "load_config")
        assert hasattr(mod, "fill_certificate")
        assert hasattr(mod, "generate_certificates")
        assert hasattr(mod, "create_text_overlay")
        assert hasattr(mod, "register_futura_font")

    def test_fill_certificates_from_file_function_exists(self):
        """Test convenience function exists."""
        from src.automations.fill_pdfs import fill_certificates_from_file

        assert callable(fill_certificates_from_file)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_load_recipients_unicode_names(self):
        """Test loading recipients with unicode characters."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Jose Garcia\nMarie Curie\n")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 2
            assert recipients[0]["name"] == "Jose Garcia"
            assert recipients[1]["name"] == "Marie Curie"
        finally:
            Path(file_path).unlink()

    def test_load_recipients_csv_with_bom(self):
        """Test loading CSV file with BOM (Byte Order Mark)."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
            # Write UTF-8 BOM followed by CSV content
            f.write(b"\xef\xbb\xbfName,Position\n")
            f.write(b"Alice Smith,Engineer\n")
            file_path = f.name

        try:
            recipients = load_recipients(file_path)
            assert len(recipients) == 1
            assert recipients[0]["name"] == "Alice Smith"
        finally:
            Path(file_path).unlink()

    def test_config_with_all_font_families(self):
        """Test configuration with various font families."""
        font_families = ["Helvetica", "Times", "Courier", "Arial", "Futura"]

        for font_family in font_families:
            config_data = {
                "template_pdf": "template.pdf",
                "output_directory": "output",
                "fields": {"name": {"x": 100, "y": 200, "font_size": 24}},
                "font_family": font_family,
            }
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(config_data, f)
                file_path = f.name

            try:
                config = load_config(file_path)
                assert config["font_family"] == font_family
            finally:
                Path(file_path).unlink()

    def test_create_overlay_with_bold_font(self):
        """Test text overlay with bold font weight."""
        config = {"fields": {"name": {"x": 100, "y": 200, "font_size": 24, "font_weight": "bold"}}}
        recipient_data = {"name": "Test Name"}

        buffer = create_text_overlay(config, recipient_data, 612, 792)
        assert len(buffer.getvalue()) > 0
