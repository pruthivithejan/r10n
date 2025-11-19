import pytest
import tempfile
import json
import csv
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

from src.automations.fill_certificates import (
    register_futura_font,
    load_recipients,
    load_config,
    create_text_overlay,
    fill_certificate,
    generate_certificates,
    fill_certificates_from_file,
)





class TestLoadRecipients:
    """Test recipient loading functionality."""

    def test_load_recipients_csv_basic(self):
        """Test loading recipients from CSV file."""
        csv_data = [
            ["Name", "Position"],
            ["John Doe", "Manager"],
            ["Jane Smith", "Developer"]
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_path = f.name

        try:
            recipients = load_recipients(csv_path)
            
            assert len(recipients) == 2
            assert recipients[0]["name"] == "John Doe"
            assert recipients[0]["position"] == "Manager"
            assert recipients[1]["name"] == "Jane Smith"
            assert recipients[1]["position"] == "Developer"
            
        finally:
            Path(csv_path).unlink()

    def test_load_recipients_txt_basic(self):
        """Test loading recipients from TXT file."""
        txt_content = "John Doe\tManager\nJane Smith\tDeveloper\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(txt_content)
            txt_path = f.name

        try:
            recipients = load_recipients(txt_path)
            
            assert len(recipients) == 2
            assert recipients[0]["name"] == "John Doe"
            assert recipients[0]["position"] == "Manager"
            assert recipients[1]["name"] == "Jane Smith"
            assert recipients[1]["position"] == "Developer"
            
        finally:
            Path(txt_path).unlink()

    def test_load_recipients_txt_single_column(self):
        """Test loading recipients from TXT file with single column."""
        txt_content = "John Doe\nJane Smith\nBob Johnson\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(txt_content)
            txt_path = f.name

        try:
            recipients = load_recipients(txt_path)
            
            assert len(recipients) == 3
            assert recipients[0]["name"] == "John Doe"
            assert recipients[0]["position"] == ""
            assert recipients[1]["name"] == "Jane Smith"
            assert recipients[2]["name"] == "Bob Johnson"
            
        finally:
            Path(txt_path).unlink()

    def test_load_recipients_csv_with_comments(self):
        """Test loading recipients with comments and empty lines."""
        txt_content = "# This is a comment\nJohn Doe\tManager\n\n# Another comment\nJane Smith\tDeveloper\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(txt_content)
            txt_path = f.name

        try:
            recipients = load_recipients(txt_path)
            
            assert len(recipients) == 2
            assert recipients[0]["name"] == "John Doe"
            assert recipients[1]["name"] == "Jane Smith"
            
        finally:
            Path(txt_path).unlink()

    def test_load_recipients_file_not_found(self):
        """Test loading recipients from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_recipients("non_existent_file.txt")

    def test_load_recipients_csv_normalized_headers(self):
        """Test loading recipients with various header formats."""
        csv_data = [
            ["Full Name", "Role"],
            ["John Doe", "Manager"],
            ["Jane Smith", "Developer"]
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_path = f.name

        try:
            recipients = load_recipients(csv_path)
            
            assert len(recipients) == 2
            assert recipients[0]["name"] == "John Doe"
            
        finally:
            Path(csv_path).unlink()





class TestCreateTextOverlay:
    """Test text overlay creation functionality."""

    @patch('src.automations.fill_certificates.register_futura_font')
    @patch('src.automations.fill_certificates.canvas.Canvas')
    def test_create_text_overlay_basic(self, mock_canvas, mock_register_font):
        """Test creating basic text overlay."""
        mock_register_font.return_value = True
        mock_c = Mock()
        mock_c.stringWidth.return_value = 100  # Mock string width for calculations
        mock_canvas.return_value = mock_c
        
        config = {
            "font_family": "Helvetica",
            "fields": {
                "name": {
                    "x": 300,
                    "y": 200,
                    "font_size": 24,
                    "font_weight": "bold",
                    "color": [0, 0, 0],
                    "alignment": "center"
                }
            }
        }
        
        recipient_data = {"name": "John Doe"}
        
        result = create_text_overlay(config, recipient_data, 600, 400)
        
        # Verify canvas methods were called
        mock_c.setFont.assert_called()
        mock_c.setFillColorRGB.assert_called_with(0, 0, 0)
        mock_c.drawString.assert_called()
        mock_c.save.assert_called_once()

    @patch('src.automations.fill_certificates.register_futura_font')
    @patch('src.automations.fill_certificates.canvas.Canvas')
    def test_create_text_overlay_long_name(self, mock_canvas, mock_register_font):
        """Test creating text overlay with long name."""
        mock_register_font.return_value = False
        mock_c = Mock()
        mock_canvas.return_value = mock_c
        
        config = {
            "font_family": "Helvetica",
            "fields": {
                "name": {
                    "x": 300,
                    "y": 200,
                    "font_size": 24,
                    "font_weight": "normal",
                    "color": [0, 0, 0],
                    "alignment": "left"
                }
            }
        }
        
        recipient_data = {"name": "This is a very long name that should trigger font size reduction"}
        
        result = create_text_overlay(config, recipient_data, 600, 400)
        
        # Verify that font was set (font size should be reduced for long names)
        mock_c.setFont.assert_called()
        mock_c.drawString.assert_called()


class TestFillCertificate:
    """Test certificate filling functionality."""

    @patch('src.automations.fill_certificates.PdfReader')
    @patch('src.automations.fill_certificates.PdfWriter')
    @patch('src.automations.fill_certificates.create_text_overlay')
    def test_fill_certificate_success(self, mock_overlay, mock_writer, mock_reader):
        """Test successful certificate filling."""
        # Mock PDF reader
        mock_template_page = Mock()
        mock_template_page.mediabox.width = 600
        mock_template_page.mediabox.height = 400
        mock_template_reader = Mock()
        mock_template_reader.pages = [mock_template_page]
        mock_reader.return_value = mock_template_reader
        
        # Mock overlay
        mock_overlay_buffer = Mock()
        mock_overlay.return_value = mock_overlay_buffer
        
        # Mock overlay reader
        mock_overlay_page = Mock()
        mock_overlay_reader = Mock()
        mock_overlay_reader.pages = [mock_overlay_page]
        
        # Configure reader to return different objects for template and overlay
        reader_call_count = 0
        def reader_side_effect(arg):
            nonlocal reader_call_count
            reader_call_count += 1
            if reader_call_count == 1:  # First call is for template
                return mock_template_reader
            else:  # Second call is for overlay
                return mock_overlay_reader
        
        mock_reader.side_effect = reader_side_effect
        
        # Mock writer
        mock_writer_instance = Mock()
        mock_writer.return_value = mock_writer_instance
        
        config = {
            "fields": {
                "name": {
                    "x": 300,
                    "y": 200,
                    "font_size": 24
                }
            }
        }
        
        recipient_data = {"name": "John Doe"}
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as template_file:
            template_path = template_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
            output_path = output_file.name

        try:
            # Mock file operations
            with patch('builtins.open', mock=Mock()):
                result = fill_certificate(template_path, config, recipient_data, output_path)
            
            assert result is True
            mock_template_page.merge_page.assert_called_once_with(mock_overlay_page)
            mock_writer_instance.add_page.assert_called_once_with(mock_template_page)
            
        finally:
            Path(template_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


class TestGenerateCertificates:
    """Test certificate generation functionality."""

    @patch('src.automations.fill_certificates.load_config')
    @patch('src.automations.fill_certificates.load_recipients')
    @patch('src.automations.fill_certificates.fill_certificate')
    @patch('src.automations.fill_certificates.os.path.exists')
    @patch('src.automations.fill_certificates.os.makedirs')
    def test_generate_certificates_success(self, mock_makedirs, mock_exists, 
                                          mock_fill_cert, mock_load_recipients, mock_load_config):
        """Test successful certificate generation."""
        # Mock configuration
        mock_config = {
            "template_pdf": "template.pdf",
            "output_directory": "output",
            "fields": {
                "name": {"x": 300, "y": 200, "font_size": 24}
            }
        }
        mock_load_config.return_value = mock_config
        
        # Mock recipients
        mock_recipients = [
            {"name": "John Doe", "position": "Manager"},
            {"name": "Jane Smith", "position": "Developer"}
        ]
        mock_load_recipients.return_value = mock_recipients
        
        # Mock file existence and certificate filling
        def exists_side_effect(path):
            return "template.pdf" in str(path)
        
        mock_exists.side_effect = exists_side_effect
        mock_fill_cert.return_value = True
        
        result = generate_certificates("recipients.csv", "config.json", "test_base")
        
        assert result["total"] == 2
        assert result["generated"] == 2
        assert result["failed"] == 0
        assert len(result["errors"]) == 0
        
        # Verify functions were called
        mock_load_config.assert_called_once()
        mock_load_recipients.assert_called_once()
        assert mock_fill_cert.call_count == 2

    @patch('src.automations.fill_certificates.load_config')
    @patch('src.automations.fill_certificates.load_recipients')
    @patch('src.automations.fill_certificates.os.path.exists')
    def test_generate_certificates_no_recipients(self, mock_exists, mock_load_recipients, mock_load_config):
        """Test certificate generation with no recipients."""
        mock_config = {
            "template_pdf": "template.pdf",
            "output_directory": "output",
            "fields": {}
        }
        mock_load_config.return_value = mock_config
        mock_load_recipients.return_value = []
        mock_exists.return_value = True
        
        result = generate_certificates("recipients.csv", "config.json", "test_base")
        
        assert result["total"] == 0
        assert result["generated"] == 0
        assert result["failed"] == 0

    @patch('src.automations.fill_certificates.load_config')
    @patch('src.automations.fill_certificates.load_recipients')
    @patch('src.automations.fill_certificates.os.path.exists')
    def test_generate_certificates_template_not_found(self, mock_exists, mock_load_recipients, mock_load_config):
        """Test certificate generation with missing template."""
        mock_config = {
            "template_pdf": "template.pdf",
            "output_directory": "output",
            "fields": {}
        }
        mock_load_config.return_value = mock_config
        mock_load_recipients.return_value = [{"name": "John Doe"}]
        mock_exists.return_value = False  # Template doesn't exist
        
        with pytest.raises(FileNotFoundError):
            generate_certificates("recipients.csv", "config.json", "test_base")

    @patch('src.automations.fill_certificates.load_config')
    @patch('src.automations.fill_certificates.load_recipients')
    @patch('src.automations.fill_certificates.fill_certificate')
    @patch('src.automations.fill_certificates.os.path.exists')
    @patch('src.automations.fill_certificates.os.makedirs')
    def test_generate_certificates_with_failures(self, mock_makedirs, mock_exists,
                                                mock_fill_cert, mock_load_recipients, mock_load_config):
        """Test certificate generation with some failures."""
        mock_config = {
            "template_pdf": "template.pdf",
            "output_directory": "output",
            "fields": {"name": {"x": 300, "y": 200, "font_size": 24}}
        }
        mock_load_config.return_value = mock_config
        
        mock_recipients = [
            {"name": "John Doe"},
            {"name": "Jane Smith"}
        ]
        mock_load_recipients.return_value = mock_recipients
        
        mock_exists.side_effect = lambda p: "template.pdf" in str(p)
        
        # First call succeeds, second fails
        mock_fill_cert.side_effect = [True, Exception("Fill failed")]
        
        result = generate_certificates("recipients.csv", "config.json", "test_base")
        
        assert result["total"] == 2
        assert result["generated"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

