"""
Tests for the Email sending automation.

These tests verify the email sending functionality for both
local usage and uvx distribution.
"""

import csv
import json
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.automations.send_same_email import (
    SimpleEmailConfig,
    SimpleEmailSender,
    find_matching_certificate,
    load_simple_config,
    preview_email_setup,
    normalize_name_for_matching,
    send_from_file,
    send_personalized_emails_with_certificates,
    send_same_email_to_all,
)


class TestSimpleEmailConfig:
    """Test SimpleEmailConfig dataclass."""

    def test_config_with_defaults(self):
        """Test config with default values."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="user@example.com",
            password="secret",
            subject="Test Subject",
        )
        assert config.smtp_server == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.email == "user@example.com"
        assert config.password == "secret"
        assert config.subject == "Test Subject"
        assert config.use_tls is True  # Default

    def test_config_without_tls(self):
        """Test config with TLS disabled."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=25,
            email="user@example.com",
            password="secret",
            subject="Test",
            use_tls=False,
        )
        assert config.use_tls is False


class TestSimpleEmailSender:
    """Test SimpleEmailSender class."""

    @pytest.fixture
    def sender(self):
        """Create a SimpleEmailSender instance for testing."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="sender@example.com",
            password="password",
            subject="Test Subject",
        )
        return SimpleEmailSender(config)

    def test_sender_initialization(self, sender):
        """Test sender initialization."""
        assert sender.smtp_connection is None
        assert sender.max_retries == 3
        assert sender.base_backoff == 2.0

    @patch("smtplib.SMTP")
    def test_connect_success(self, mock_smtp, sender):
        """Test successful SMTP connection."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        result = sender.connect()

        assert result is True
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("sender@example.com", "password")

    @patch("smtplib.SMTP")
    def test_connect_failure(self, mock_smtp, sender):
        """Test SMTP connection failure."""
        mock_smtp.side_effect = Exception("Connection failed")

        result = sender.connect()

        assert result is False

    @patch("smtplib.SMTP")
    def test_disconnect(self, mock_smtp, sender):
        """Test SMTP disconnection."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        sender.connect()
        sender.disconnect()

        mock_smtp_instance.quit.assert_called_once()

    def test_disconnect_when_not_connected(self, sender):
        """Test disconnect when not connected does nothing."""
        # Should not raise
        sender.disconnect()

    @patch("smtplib.SMTP")
    def test_ensure_connected_reconnects_after_noop_failure(self, mock_smtp, sender):
        """Test ensure_connected reconnects when the connection is stale."""
        first_connection = MagicMock()
        second_connection = MagicMock()
        mock_smtp.side_effect = [first_connection, second_connection]

        assert sender.connect() is True
        first_connection.noop.side_effect = smtplib.SMTPServerDisconnected("lost")

        assert sender.ensure_connected() is True
        first_connection.quit.assert_called_once()
        second_connection.login.assert_called_once_with("sender@example.com", "password")
        assert sender.smtp_connection is second_connection


class TestCreateMessage:
    """Test email message creation."""

    @pytest.fixture
    def sender(self):
        """Create a sender for testing."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="sender@example.com",
            password="password",
            subject="Test Subject",
        )
        return SimpleEmailSender(config)

    def test_create_message_basic(self, sender):
        """Test creating basic email message."""
        msg = sender.create_message(
            to_email="recipient@example.com", subject="Test Subject", body="Hello, World!"
        )

        assert isinstance(msg, MIMEMultipart)
        assert msg["From"] == "sender@example.com"
        assert msg["To"] == "recipient@example.com"
        assert msg["Subject"] == "Test Subject"

    def test_create_message_with_attachment(self, sender):
        """Test creating message with attachment."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Attachment content")
            attachment_path = f.name

        try:
            msg = sender.create_message(
                to_email="recipient@example.com",
                subject="With Attachment",
                body="See attached.",
                attachments=[attachment_path],
            )

            # Message should have multiple parts
            assert msg.is_multipart()
            parts = list(msg.walk())
            # Should have at least body and attachment
            assert len(parts) >= 2
        finally:
            Path(attachment_path).unlink()

    def test_create_message_attachment_not_found(self, sender, capsys):
        """Test warning when attachment not found."""
        msg = sender.create_message(
            to_email="recipient@example.com",
            subject="Test",
            body="Body",
            attachments=["nonexistent_file.pdf"],
        )

        captured = capsys.readouterr()
        assert "Attachment not found" in captured.out

    def test_create_message_multiple_attachments(self, sender):
        """Test creating message with multiple attachments."""
        attachments = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(mode="w", suffix=f"_{i}.txt", delete=False) as f:
                    f.write(f"Content {i}")
                    attachments.append(f.name)

            msg = sender.create_message(
                to_email="recipient@example.com",
                subject="Multiple Attachments",
                body="See attached files.",
                attachments=attachments,
            )

            assert msg.is_multipart()
        finally:
            for att in attachments:
                Path(att).unlink()


class TestSendMessageWithRetry:
    """Test message sending with retry logic."""

    @pytest.fixture
    def sender(self):
        """Create a sender for testing."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="sender@example.com",
            password="password",
            subject="Test",
        )
        sender = SimpleEmailSender(config)
        sender.base_backoff = 0.01  # Speed up tests
        return sender

    @patch("smtplib.SMTP")
    def test_send_with_retry_success(self, mock_smtp, sender):
        """Test successful send on first try."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        sender.connect()
        msg = sender.create_message("test@example.com", "Subject", "Body")

        # Should not raise
        sender.send_message_with_retry(msg)
        mock_smtp_instance.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_with_retry_reconnect(self, mock_smtp, sender):
        """Test retry on connection lost."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        # First send fails, second succeeds
        mock_smtp_instance.send_message.side_effect = [
            smtplib.SMTPServerDisconnected("Disconnected"),
            None,
        ]
        mock_smtp_instance.noop.side_effect = [Exception("Lost connection"), None]

        sender.connect()
        msg = sender.create_message("test@example.com", "Subject", "Body")

        # Should succeed after retry
        sender.send_message_with_retry(msg)

    @patch("smtplib.SMTP")
    def test_send_with_retry_max_retries_exceeded(self, mock_smtp, sender):
        """Test failure after max retries."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.send_message.side_effect = smtplib.SMTPServerDisconnected("Fail")

        sender.connect()
        msg = sender.create_message("test@example.com", "Subject", "Body")

        with pytest.raises(smtplib.SMTPServerDisconnected):
            sender.send_message_with_retry(msg)


class TestSendSameEmailToMultiple:
    """Test sending same email to multiple recipients."""

    @pytest.fixture
    def sender(self):
        """Create a sender for testing."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="sender@example.com",
            password="password",
            subject="Test",
        )
        sender = SimpleEmailSender(config)
        sender.base_backoff = 0.01
        return sender

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_to_multiple_success(self, mock_sleep, mock_smtp, sender):
        """Test sending to multiple recipients successfully."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        email_list = ["user1@example.com", "user2@example.com", "user3@example.com"]
        results = sender.send_same_email_to_multiple(email_list, "Subject", "Body")

        assert results["sent"] == 3
        assert results["failed"] == 0
        assert results["total"] == 3
        assert len(results["failed_emails"]) == 0

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_to_multiple_partial_failure(self, mock_sleep, mock_smtp, sender):
        """Test partial failure when sending to multiple recipients."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        # Second send fails
        mock_smtp_instance.send_message.side_effect = [None, Exception("Send failed"), None]

        email_list = ["user1@example.com", "user2@example.com", "user3@example.com"]
        results = sender.send_same_email_to_multiple(email_list, "Subject", "Body")

        assert results["sent"] == 2
        assert results["failed"] == 1
        assert "user2@example.com" in results["failed_emails"]

    @patch("smtplib.SMTP")
    def test_send_to_multiple_connect_failure(self, mock_smtp, sender):
        """Test handling when initial connection fails."""
        mock_smtp.side_effect = Exception("Connection failed")

        email_list = ["user@example.com"]
        results = sender.send_same_email_to_multiple(email_list, "Subject", "Body")

        assert results["sent"] == 0
        assert results["total"] == 1


class TestLoadSimpleConfig:
    """Test configuration loading from file."""

    def test_load_config_valid(self):
        """Test loading valid configuration."""
        config_data = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email": "user@gmail.com",
            "password": "app_password",
            "subject": "Test Email",
            "use_tls": True,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            file_path = f.name

        try:
            config = load_simple_config(file_path)
            assert isinstance(config, SimpleEmailConfig)
            assert config.smtp_server == "smtp.gmail.com"
            assert config.subject == "Test Email"
        finally:
            Path(file_path).unlink()

    def test_load_config_default_tls(self):
        """Test default TLS value when not specified."""
        config_data = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email": "user@example.com",
            "password": "password",
            "subject": "Test",
            # use_tls not specified
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            file_path = f.name

        try:
            config = load_simple_config(file_path)
            assert config.use_tls is True
        finally:
            Path(file_path).unlink()

    def test_load_config_file_not_found(self):
        """Test error for missing config file."""
        with pytest.raises(FileNotFoundError):
            load_simple_config("nonexistent_config.json")


class TestNormalizeNameForMatching:
    """Test name normalization for certificate matching."""

    def test_normalize_basic(self):
        """Test basic name normalization."""
        result = normalize_name_for_matching("John Doe")
        assert result == "john_doe"

    def test_normalize_with_special_chars(self):
        """Test normalization with special characters."""
        result = normalize_name_for_matching("John O'Connor")
        assert result == "john_oconnor"

    def test_normalize_with_multiple_spaces(self):
        """Test normalization with multiple spaces."""
        result = normalize_name_for_matching("John   Middle   Doe")
        assert result == "john_middle_doe"

    def test_normalize_with_hyphens(self):
        """Test normalization with hyphens."""
        result = normalize_name_for_matching("Mary-Jane Watson")
        assert result == "maryjane_watson"

    def test_normalize_unicode(self):
        """Test normalization with unicode characters."""
        result = normalize_name_for_matching("Jose Garcia")
        assert "jose" in result.lower()


class TestFindMatchingCertificate:
    """Test certificate file matching."""

    def test_find_exact_match(self):
        """Test finding certificate with exact match."""
        certificate_files = {
            "John_Doe_certificate": "/path/to/John_Doe_certificate.pdf",
            "Jane_Smith_certificate": "/path/to/Jane_Smith_certificate.pdf",
        }

        result = find_matching_certificate("John Doe", certificate_files)
        assert result == "/path/to/John_Doe_certificate.pdf"

    def test_find_partial_match(self):
        """Test finding certificate with partial match."""
        certificate_files = {"john_doe_engineer_certificate": "/path/to/cert.pdf"}

        result = find_matching_certificate("John Doe", certificate_files)
        assert result == "/path/to/cert.pdf"

    def test_find_no_match(self):
        """Test when no matching certificate found."""
        certificate_files = {"Alice_Smith_certificate": "/path/to/Alice_Smith.pdf"}

        result = find_matching_certificate("Bob Jones", certificate_files)
        assert result is None

    def test_find_case_insensitive(self):
        """Test case-insensitive matching."""
        certificate_files = {"JOHN_DOE_CERTIFICATE": "/path/to/cert.pdf"}

        result = find_matching_certificate("john doe", certificate_files)
        assert result == "/path/to/cert.pdf"

    def test_find_partial_name_match(self):
        """Test partial name matching."""
        certificate_files = {"Smith_John_certificate": "/path/to/cert.pdf"}

        result = find_matching_certificate("John Smith", certificate_files)
        assert result == "/path/to/cert.pdf"


class TestSendSameEmailToAll:
    """Test the send_same_email_to_all convenience function."""

    @patch("src.automations.send_same_email.SimpleEmailSender")
    @patch("src.automations.send_same_email.load_simple_config")
    def test_send_same_email_basic(self, mock_load_config, mock_sender_class):
        """Test basic email sending to all recipients."""
        mock_config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="sender@example.com",
            password="password",
            subject="Test Subject",
        )
        mock_load_config.return_value = mock_config

        mock_sender = MagicMock()
        mock_sender.send_same_email_to_multiple.return_value = {
            "sent": 2,
            "failed": 0,
            "total": 2,
            "failed_emails": [],
        }
        mock_sender_class.return_value = mock_sender

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "email": "sender@example.com",
                    "password": "password",
                    "subject": "Test",
                },
                f,
            )
            config_path = f.name

        try:
            results = send_same_email_to_all(
                email_list=["user1@example.com", "user2@example.com"],
                body="Hello!",
                config_file=config_path,
            )

            assert results["sent"] == 2
            assert results["failed"] == 0
        finally:
            Path(config_path).unlink()


class TestSendPersonalizedEmailsWithCertificates:
    """Test personalized email sending with certificates."""

    @pytest.fixture
    def setup_email_files(self):
        """Set up test files for personalized email sending."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create email list CSV
            email_list_path = temp_path / "emails.csv"
            with open(email_list_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Email"])
                writer.writerow(["Alice Smith", "alice@example.com"])
                writer.writerow(["Bob Jones", "bob@example.com"])

            # Create config file
            config_path = temp_path / "config.json"
            config_data = {
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "email": "sender@example.com",
                "password": "password",
                "subject": "Your Certificate",
            }
            config_path.write_text(json.dumps(config_data))

            # Create certificates directory
            certs_dir = temp_path / "certificates"
            certs_dir.mkdir()
            (certs_dir / "Alice_Smith_certificate.pdf").write_bytes(b"fake pdf")
            (certs_dir / "Bob_Jones_certificate.pdf").write_bytes(b"fake pdf")

            yield {
                "temp_dir": str(temp_path),
                "email_list": str(email_list_path),
                "config": str(config_path),
                "certs_dir": str(certs_dir),
            }

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_personalized_success(self, mock_sleep, mock_smtp, setup_email_files):
        """Test successful personalized email sending."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        files = setup_email_files
        results = send_personalized_emails_with_certificates(
            email_list_file=files["email_list"],
            subject="Your Certificate",
            body_template="Dear {name}, here is your certificate.",
            config_file=files["config"],
            certificates_dir=files["certs_dir"],
        )

        assert results["sent"] == 2
        assert results["failed"] == 0
        assert len(results["missing_certificates"]) == 0

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_personalized_missing_certificate(self, mock_sleep, mock_smtp, setup_email_files):
        """Test handling of missing certificates."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        files = setup_email_files

        # Remove one certificate
        Path(files["certs_dir"]).joinpath("Alice_Smith_certificate.pdf").unlink()

        results = send_personalized_emails_with_certificates(
            email_list_file=files["email_list"],
            subject="Your Certificate",
            body_template="Dear {name}, here is your certificate.",
            config_file=files["config"],
            certificates_dir=files["certs_dir"],
        )

        # Both emails should still be sent
        assert results["sent"] == 2
        assert "Alice Smith" in results["missing_certificates"]

    def test_send_personalized_with_no_valid_recipients(self, tmp_path):
        """Test early return when the CSV has no usable recipients."""
        email_list = tmp_path / "emails.csv"
        email_list.write_text("Name,Email\n,\n", encoding="utf-8")

        config = tmp_path / "config.json"
        config.write_text(
            json.dumps(
                {
                    "smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                    "email": "sender@example.com",
                    "password": "password",
                    "subject": "Your Certificate",
                }
            ),
            encoding="utf-8",
        )

        results = send_personalized_emails_with_certificates(
            email_list_file=str(email_list),
            subject="Your Certificate",
            body_template="Dear {name}, here is your certificate.",
            config_file=str(config),
            certificates_dir=str(tmp_path / "certificates"),
        )

        assert results == {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}


class TestSendFromFile:
    """Test send_from_file function."""

    @pytest.fixture
    def setup_files(self):
        """Set up test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create email list
            email_list_path = temp_path / "emails.csv"
            with open(email_list_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Email"])
                writer.writerow(["Test User", "test@example.com"])

            # Create body file
            body_path = temp_path / "body.txt"
            body_path.write_text("Dear {name}, this is a test email.")

            # Create config
            config_path = temp_path / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "email": "sender@example.com",
                        "password": "password",
                        "subject": "Test Email",
                    }
                )
            )

            # Create certificates dir
            certs_dir = temp_path / "certs"
            certs_dir.mkdir()
            (certs_dir / "Test_User_certificate.pdf").write_bytes(b"pdf")

            yield {
                "email_list": str(email_list_path),
                "body": str(body_path),
                "config": str(config_path),
                "certs_dir": str(certs_dir),
            }

    @patch("smtplib.SMTP")
    @patch("time.sleep")
    def test_send_from_file(self, mock_sleep, mock_smtp, setup_files):
        """Test send_from_file function."""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        files = setup_files
        results = send_from_file(
            email_list_file=files["email_list"],
            body_file=files["body"],
            config_file=files["config"],
            certificates_dir=files["certs_dir"],
        )

        assert results["sent"] == 1
        assert results["total"] == 1


class TestPreviewEmailSetup:
    """Test the preview_email_setup helper."""

    @pytest.fixture
    def setup_test_files(self):
        """Set up test files for setup testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create email list
            email_list_path = temp_path / "emails.csv"
            with open(email_list_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Email"])
                writer.writerow(["Test User", "test@example.com"])

            # Create body file
            body_path = temp_path / "body.txt"
            body_path.write_text("Dear {name}, welcome!")

            # Create config
            config_path = temp_path / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "email": "sender@example.com",
                        "password": "password",
                        "subject": "Test Email",
                    }
                )
            )

            # Create certificates dir
            certs_dir = temp_path / "certs"
            certs_dir.mkdir()
            (certs_dir / "Test_User_certificate.pdf").write_bytes(b"pdf")

            yield {
                "email_list": str(email_list_path),
                "body": str(body_path),
                "config": str(config_path),
                "certs_dir": str(certs_dir),
            }

    def test_email_setup_success(self, setup_test_files):
        """Test successful email setup test."""
        files = setup_test_files
        result = preview_email_setup(
            email_list_file=files["email_list"],
            body_file=files["body"],
            config_file=files["config"],
            certificates_dir=files["certs_dir"],
        )

        assert result["config_loaded"] is True
        assert result["body_loaded"] is True
        assert result["recipients_count"] == 1
        assert result["certificates_count"] == 1


class TestUvxCompatibility:
    """Test that the module works correctly when run via uvx."""

    def test_module_import(self):
        """Test module can be imported."""
        from src.automations import send_same_email as mod

        assert hasattr(mod, "SimpleEmailConfig")
        assert hasattr(mod, "SimpleEmailSender")
        assert hasattr(mod, "send_same_email_to_all")
        assert hasattr(mod, "send_personalized_emails_with_certificates")
        assert hasattr(mod, "find_matching_certificate")
        assert hasattr(mod, "normalize_name_for_matching")
        assert hasattr(mod, "preview_email_setup")

    def test_dataclass_fields(self):
        """Test SimpleEmailConfig has all expected fields."""
        from dataclasses import fields

        field_names = {f.name for f in fields(SimpleEmailConfig)}
        expected_fields = {"smtp_server", "smtp_port", "email", "password", "subject", "use_tls"}
        assert field_names == expected_fields


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_email_list(self):
        """Test handling empty email list."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="sender@example.com",
            password="password",
            subject="Test",
        )
        sender = SimpleEmailSender(config)

        with patch("smtplib.SMTP"):
            results = sender.send_same_email_to_multiple([], "Subject", "Body")

        assert results["total"] == 0
        assert results["sent"] == 0

    def test_normalize_empty_name(self):
        """Test normalizing empty name."""
        result = normalize_name_for_matching("")
        assert result == ""

    def test_normalize_whitespace_only(self):
        """Test normalizing whitespace-only name."""
        result = normalize_name_for_matching("   ")
        assert result == ""

    def test_find_certificate_empty_files(self):
        """Test finding certificate with empty files dict."""
        result = find_matching_certificate("John Doe", {})
        assert result is None

    def test_create_message_empty_body(self):
        """Test creating message with empty body."""
        config = SimpleEmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            email="sender@example.com",
            password="password",
            subject="Test",
        )
        sender = SimpleEmailSender(config)

        msg = sender.create_message("test@example.com", "Subject", "")
        assert msg is not None
        assert msg["Subject"] == "Subject"
