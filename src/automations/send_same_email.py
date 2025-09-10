import csv
import json
import smtplib
from dataclasses import dataclass
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List


@dataclass
class SimpleEmailConfig:
    """Simple email configuration"""

    smtp_server: str
    smtp_port: int
    email: str
    password: str
    subject: str
    use_tls: bool = True


class SimpleEmailSender:
    def __init__(self, config: SimpleEmailConfig):
        self.config = config
        self.smtp_connection = None

    def connect(self):
        """Establish SMTP connection"""
        try:
            self.smtp_connection = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            if self.config.use_tls:
                self.smtp_connection.starttls()
            self.smtp_connection.login(self.config.email, self.config.password)
            print(f"✅ Connected to SMTP server: {self.config.smtp_server}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to SMTP server: {e!s}")
            return False

    def disconnect(self):
        """Close SMTP connection"""
        if self.smtp_connection:
            self.smtp_connection.quit()
            print("📤 Disconnected from SMTP server")

    def create_message(
        self, to_email: str, subject: str, body: str, attachments: List[str] = None
    ) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart()
        msg["From"] = self.config.email
        msg["To"] = to_email
        msg["Subject"] = subject

        # Add body
        msg.attach(MIMEText(body, "plain"))

        # Add attachments if provided
        if attachments:
            for file_path in attachments:
                if Path(file_path).exists():
                    self._attach_file(msg, file_path)
                else:
                    print(f"⚠️  Attachment not found: {file_path}")

        return msg

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Attach a file to the email message"""
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {Path(file_path).name}")
        msg.attach(part)

    def send_same_email_to_multiple(
        self, email_list: List[str], subject: str, body: str, attachments: List[str] = None
    ) -> dict:
        """Send the same email to multiple recipients"""
        results = {"sent": 0, "failed": 0, "total": len(email_list), "failed_emails": []}

        if not self.connect():
            return results

        print(f"📧 Sending email to {len(email_list)} recipients...")
        print(f"📄 Subject: {subject}")
        print(f"📎 Attachments: {len(attachments) if attachments else 0}")
        print()

        for i, email in enumerate(email_list, 1):
            print(f"📤 Sending email {i}/{len(email_list)} to {email}...")

            try:
                msg = self.create_message(email, subject, body, attachments)
                self.smtp_connection.send_message(msg)
                results["sent"] += 1
                print("✅ Email sent successfully")
            except Exception as e:
                results["failed"] += 1
                results["failed_emails"].append(email)
                print(f"❌ Failed to send email: {e!s}")

        self.disconnect()
        return results


def load_simple_config(config_path: str) -> SimpleEmailConfig:
    """Load email configuration from JSON file"""
    with open(config_path) as f:
        config_data = json.load(f)

    return SimpleEmailConfig(
        smtp_server=config_data["smtp_server"],
        smtp_port=config_data["smtp_port"],
        email=config_data["email"],
        password=config_data["password"],
        subject=config_data["subject"],
        use_tls=config_data.get("use_tls", True),
    )


def send_same_email_to_all(
    email_list: List[str],
    body: str,
    config_file: str = "data/email_config.json",
    attachments: List[str] = None,
):
    """Send the same email to all recipients in the list"""
    try:
        # Load configuration
        config = load_simple_config(config_file)

        # Send emails
        sender = SimpleEmailSender(config)
        results = sender.send_same_email_to_multiple(email_list, config.subject, body, attachments)

        # Print summary
        print("\n📊 Email Sending Summary:")
        print(f"Total recipients: {results['total']}")
        print(f"✅ Successfully sent: {results['sent']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"📈 Success rate: {(results['sent'] / results['total'] * 100):.1f}%")

        if results["failed_emails"]:
            print("\n❌ Failed email addresses:")
            for email in results["failed_emails"]:
                print(f"  - {email}")

        return results

    except Exception as e:
        print(f"❌ Error in email sending: {e!s}")
        return {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}


def send_personalized_emails_with_certificates(
    email_list_file: str, subject: str, body_template: str, config_file: str, certificates_dir: str
) -> dict:
    """Send personalized emails with individual certificate attachments"""
    try:
        # Load configuration
        config = load_simple_config(config_file)

        # Parse email list from CSV
        recipients = []
        with open(email_list_file, encoding="utf-8") as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                if "Name" in row and "Email" in row:
                    name = row["Name"].strip()
                    email = row["Email"].strip()
                    if name and email:
                        recipients.append({"name": name, "email": email})

        if not recipients:
            print("❌ No valid recipients found in CSV file")
            return {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}

        # Create name to certificate mapping
        certificate_files = {}
        certificates_path = Path(certificates_dir)
        if certificates_path.exists():
            for cert_file in certificates_path.glob("*.pdf"):
                certificate_files[cert_file.stem] = str(cert_file)

        print(f"📧 Found {len(recipients)} recipients")
        print(f"📎 Found {len(certificate_files)} certificate files")

        # Initialize results
        results = {
            "sent": 0,
            "failed": 0,
            "total": len(recipients),
            "failed_emails": [],
            "missing_certificates": [],
        }

        # Connect to SMTP
        sender = SimpleEmailSender(config)
        if not sender.connect():
            return results

        print("📤 Sending personalized emails...")
        print()

        for i, recipient in enumerate(recipients, 1):
            name = recipient["name"]
            email = recipient["email"]

            print(f"📧 Processing {i}/{len(recipients)}: {name} ({email})")

            try:
                # Find matching certificate
                certificate_path = find_matching_certificate(name, certificate_files)

                if not certificate_path:
                    print(f"⚠️  No matching certificate found for {name}")
                    results["missing_certificates"].append(name)
                    # Still send email without certificate
                    attachments = []
                else:
                    print(f"📎 Found certificate: {Path(certificate_path).name}")
                    attachments = [certificate_path]

                # Personalize email body
                personalized_body = body_template.format(name=name)

                # Create and send email
                msg = sender.create_message(email, subject, personalized_body, attachments)
                sender.smtp_connection.send_message(msg)

                results["sent"] += 1
                print("✅ Email sent successfully")

            except Exception as e:
                results["failed"] += 1
                results["failed_emails"].append(email)
                print(f"❌ Failed to send email: {e!s}")

            print()

        sender.disconnect()

        # Print summary
        print("📊 Email Sending Summary:")
        print(f"Total recipients: {results['total']}")
        print(f"✅ Successfully sent: {results['sent']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"⚠️  Missing certificates: {len(results['missing_certificates'])}")
        print(f"📈 Success rate: {(results['sent'] / results['total'] * 100):.1f}%")

        if results["failed_emails"]:
            print("\n❌ Failed email addresses:")
            for email in results["failed_emails"]:
                print(f"  - {email}")

        if results["missing_certificates"]:
            print("\n⚠️  Missing certificates for:")
            for name in results["missing_certificates"]:
                print(f"  - {name}")

        return results

    except Exception as e:
        print(f"❌ Error in email sending: {e!s}")
        return {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}


def find_matching_certificate(name: str, certificate_files: dict) -> str:
    """Find matching certificate file for a given name"""
    # Normalize name for matching
    normalized_name = normalize_name_for_matching(name)

    # Try exact match first
    for cert_name, cert_path in certificate_files.items():
        if normalized_name in cert_name.lower():
            return cert_path

    # Try partial matching
    name_parts = normalized_name.split("_")
    for cert_name, cert_path in certificate_files.items():
        cert_name_lower = cert_name.lower()
        # Check if most name parts are in certificate name
        matches = sum(1 for part in name_parts if part in cert_name_lower and len(part) > 2)
        if matches >= max(1, len(name_parts) // 2):  # At least half the parts match
            return cert_path

    return None


def normalize_name_for_matching(name: str) -> str:
    """Normalize name for certificate matching"""
    import re

    # Remove special characters and normalize spacing
    normalized = re.sub(r"[^\w\s]", "", name)
    # Replace spaces with underscores and convert to lowercase
    normalized = re.sub(r"\s+", "_", normalized).lower()
    return normalized


def send_from_file(
    email_list_file: str, body_file: str, config_file: str, certificates_dir: str
) -> dict:
    """Send personalized emails from files with individual certificate attachments"""
    try:
        # Load configuration to get subject
        config = load_simple_config(config_file)

        # Read email body from file
        with open(body_file, encoding="utf-8") as f:
            body_template = f.read()

        # Call the personalized email function
        return send_personalized_emails_with_certificates(
            email_list_file=email_list_file,
            subject=config.subject,
            body_template=body_template,
            config_file=config_file,
            certificates_dir=certificates_dir,
        )

    except Exception as e:
        print(f"❌ Error reading files: {e!s}")
        return {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}


def test_email_setup(
    email_list_file: str, body_file: str, config_file: str, certificates_dir: str
) -> dict:
    """Test email setup without sending actual emails"""
    try:
        # Load configuration to get subject
        config = load_simple_config(config_file)
        print("📧 Email configuration loaded successfully")
        print(f"📬 SMTP Server: {config.smtp_server}:{config.smtp_port}")
        print(f"📨 From: {config.email}")
        print(f"📋 Subject: {config.subject}")
        print()

        # Parse email list from CSV
        recipients = []
        with open(email_list_file, encoding="utf-8") as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                if "Name" in row and "Email" in row:
                    name = row["Name"].strip()
                    email = row["Email"].strip()
                    if name and email:
                        recipients.append({"name": name, "email": email})

        print(f"📧 Found {len(recipients)} recipients in CSV:")
        for i, recipient in enumerate(recipients, 1):
            print(f"  {i}. {recipient['name']} ({recipient['email']})")
        print()

        # Read email body from file
        with open(body_file, encoding="utf-8") as f:
            body_template = f.read()

        print(f"📄 Email body template loaded ({len(body_template)} characters)")
        print("📝 Preview of body template:")
        print("=" * 50)
        print(body_template[:200] + "..." if len(body_template) > 200 else body_template)
        print("=" * 50)
        print()

        # Create name to certificate mapping
        certificate_files = {}
        certificates_path = Path(certificates_dir)
        if certificates_path.exists():
            for cert_file in certificates_path.glob("*.pdf"):
                certificate_files[cert_file.stem] = str(cert_file)

        print(f"📎 Found {len(certificate_files)} certificate files")

        # Test certificate matching for each recipient
        for recipient in recipients:
            name = recipient["name"]
            email = recipient["email"]

            print(f"\n🔍 Testing certificate matching for: {name}")
            certificate_path = find_matching_certificate(name, certificate_files)

            if certificate_path:
                print(f"✅ Found matching certificate: {Path(certificate_path).name}")
            else:
                print("❌ No matching certificate found")

            # Test personalized email body
            personalized_body = body_template.format(name=name)
            print("📝 Personalized email preview:")
            print("-" * 30)
            print(
                personalized_body[:150] + "..."
                if len(personalized_body) > 150
                else personalized_body
            )
            print("-" * 30)

        return {
            "recipients_count": len(recipients),
            "certificates_count": len(certificate_files),
            "config_loaded": True,
            "body_loaded": True,
        }

    except Exception as e:
        print(f"❌ Error in test setup: {e!s}")
        return {"error": str(e)}


if __name__ == "__main__":
    print("Simple Email Sender")
    print("Use the main CLI to run this automation:")
    print("python src/main.py send_bulk_emails --subject 'Your Subject Here'")
