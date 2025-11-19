import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import csv

from src.automations.send_same_email import (
    SimpleEmailConfig,
    SimpleEmailSender,
    load_simple_config,
    send_same_email_to_all,
    find_matching_certificate,
    normalize_name_for_matching,
)





class TestSimpleEmailSender:
    """Test SimpleEmailSender class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = SimpleEmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            email="test@example.com",
            password="password123",
            subject="Test Subject"
        )
        self.sender = SimpleEmailSender(self.config)



    def test_create_message_basic(self):
        """Test creating basic email message."""
        msg = self.sender.create_message(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body content"
        )
        
        assert msg["From"] == "test@example.com"
        assert msg["To"] == "recipient@example.com"
        assert msg["Subject"] == "Test Subject"

    def test_create_message_with_attachments(self):
        """Test creating email message with attachments."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"Test attachment content")
            temp_file_path = temp_file.name

        try:
            msg = self.sender.create_message(
                to_email="recipient@example.com",
                subject="Test Subject",
                body="Test body content",
                attachments=[temp_file_path]
            )
            
            assert msg["From"] == "test@example.com"
            assert msg["To"] == "recipient@example.com"
            assert msg["Subject"] == "Test Subject"
            # Check that attachment was added
            assert len(msg.get_payload()) > 1  # Body + attachment
            
        finally:
            Path(temp_file_path).unlink()

    @patch('src.automations.send_same_email.smtplib.SMTP')
    def test_send_same_email_to_multiple(self, mock_smtp):
        """Test sending same email to multiple recipients."""
        mock_connection = Mock()
        mock_smtp.return_value = mock_connection
        
        email_list = ["test1@example.com", "test2@example.com"]
        result = self.sender.send_same_email_to_multiple(
            email_list=email_list,
            subject="Test Subject",
            body="Test body",
            attachments=None
        )
        
        assert result["total"] == 2
        assert result["sent"] == 2
        assert result["failed"] == 0
        assert len(result["failed_emails"]) == 0

    @patch('src.automations.send_same_email.smtplib.SMTP')
    def test_send_same_email_with_failures(self, mock_smtp):
        """Test sending emails with some failures."""
        mock_connection = Mock()
        mock_connection.send_message.side_effect = [None, Exception("Send failed")]
        mock_smtp.return_value = mock_connection
        
        email_list = ["test1@example.com", "test2@example.com"]
        result = self.sender.send_same_email_to_multiple(
            email_list=email_list,
            subject="Test Subject",
            body="Test body",
            attachments=None
        )
        
        assert result["total"] == 2
        assert result["sent"] == 1
        assert result["failed"] == 1
        assert "test2@example.com" in result["failed_emails"]





class TestSendSameEmailToAll:
    """Test high-level email sending function."""

    @patch('src.automations.send_same_email.SimpleEmailSender')
    @patch('src.automations.send_same_email.load_simple_config')
    def test_send_same_email_to_all_success(self, mock_load_config, mock_sender_class):
        """Test successful bulk email sending."""
        # Mock configuration
        mock_config = SimpleEmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            email="test@example.com",
            password="password123",
            subject="Test Subject"
        )
        mock_load_config.return_value = mock_config
        
        # Mock sender
        mock_sender = Mock()
        mock_sender.send_same_email_to_multiple.return_value = {
            "sent": 2,
            "failed": 0,
            "total": 2,
            "failed_emails": []
        }
        mock_sender_class.return_value = mock_sender
        
        email_list = ["test1@example.com", "test2@example.com"]
        result = send_same_email_to_all(
            email_list=email_list,
            body="Test email body",
            config_file="test_config.json"
        )
        
        assert result["sent"] == 2
        assert result["failed"] == 0
        assert result["total"] == 2


class TestCertificateMatching:
    """Test certificate matching functions."""

    def test_normalize_name_for_matching(self):
        """Test name normalization for certificate matching."""
        assert normalize_name_for_matching("John Doe") == "john_doe"
        assert normalize_name_for_matching("Jane Smith-Jones") == "jane_smithjones"
        assert normalize_name_for_matching("Mike O'Connor") == "mike_oconnor"
        assert normalize_name_for_matching("  Extra   Spaces  ") == "extra_spaces"

    def test_find_matching_certificate_exact_match(self):
        """Test finding certificate with exact match."""
        certificate_files = {
            "john_doe": "/path/to/john_doe.pdf",
            "jane_smith": "/path/to/jane_smith.pdf"
        }
        
        result = find_matching_certificate("John Doe", certificate_files)
        assert result == "/path/to/john_doe.pdf"

    def test_find_matching_certificate_partial_match(self):
        """Test finding certificate with partial match."""
        certificate_files = {
            "john_doe_certificate": "/path/to/john_doe_certificate.pdf",
            "jane_smith_cert": "/path/to/jane_smith_cert.pdf"
        }
        
        result = find_matching_certificate("John Doe", certificate_files)
        assert result == "/path/to/john_doe_certificate.pdf"

    def test_find_matching_certificate_no_match(self):
        """Test finding certificate with no match."""
        certificate_files = {
            "alice_wonder": "/path/to/alice_wonder.pdf",
            "bob_builder": "/path/to/bob_builder.pdf"
        }
        
        result = find_matching_certificate("John Doe", certificate_files)
        assert result is None


class TestEmailIntegration:
    """Integration tests for email functionality."""

    def test_email_workflow_with_temp_files(self):
        """Test complete email workflow with temporary files."""
        # Create temporary config file
        config_data = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email": "test@example.com",
            "password": "password123",
            "subject": "Test Subject",
            "use_tls": True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
            json.dump(config_data, config_file)
            config_path = config_file.name

        # Create temporary CSV file
        csv_data = [
            ["Name", "Email"],
            ["John Doe", "john@example.com"],
            ["Jane Smith", "jane@example.com"]
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(csv_data)
            csv_path = csv_file.name

        # Create temporary body file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as body_file:
            body_file.write("Hello {name}, this is a test email.")
            body_path = body_file.name

        try:
            # Test configuration loading
            config = load_simple_config(config_path)
            assert config.email == "test@example.com"
            
            # Test reading body file
            with open(body_path) as f:
                body_content = f.read()
            assert "{name}" in body_content
            
            # Test CSV parsing (simulated)
            recipients = []
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    recipients.append({"name": row["Name"], "email": row["Email"]})
            
            assert len(recipients) == 2
            assert recipients[0]["name"] == "John Doe"
            assert recipients[1]["email"] == "jane@example.com"
            
        finally:
            # Cleanup
            Path(config_path).unlink()
            Path(csv_path).unlink()
            Path(body_path).unlink()

