import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class SimpleEmailConfig:
    """Simple email configuration"""
    smtp_server: str
    smtp_port: int
    email: str
    password: str
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
            print(f"❌ Failed to connect to SMTP server: {str(e)}")
            return False
    
    def disconnect(self):
        """Close SMTP connection"""
        if self.smtp_connection:
            self.smtp_connection.quit()
            print("📤 Disconnected from SMTP server")
    
    def create_message(self, to_email: str, subject: str, body: str, attachments: List[str] = None) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart()
        msg['From'] = self.config.email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
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
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {Path(file_path).name}'
        )
        msg.attach(part)
    
    def send_same_email_to_multiple(
        self, 
        email_list: List[str], 
        subject: str, 
        body: str, 
        attachments: List[str] = None
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
                print(f"✅ Email sent successfully")
            except Exception as e:
                results["failed"] += 1
                results["failed_emails"].append(email)
                print(f"❌ Failed to send email: {str(e)}")
        
        self.disconnect()
        return results


def load_simple_config(config_path: str) -> SimpleEmailConfig:
    """Load email configuration from JSON file"""
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    return SimpleEmailConfig(
        smtp_server=config_data['smtp_server'],
        smtp_port=config_data['smtp_port'],
        email=config_data['email'],
        password=config_data['password'],
        use_tls=config_data.get('use_tls', True)
    )


def send_same_email_to_all(
    email_list: List[str], 
    subject: str, 
    body: str, 
    config_file: str = "data/email_config.json",
    attachments: List[str] = None
):
    """Send the same email to all recipients in the list"""
    try:
        # Load configuration
        config = load_simple_config(config_file)
        
        # Send emails
        sender = SimpleEmailSender(config)
        results = sender.send_same_email_to_multiple(email_list, subject, body, attachments)
        
        # Print summary
        print("\n📊 Email Sending Summary:")
        print(f"Total recipients: {results['total']}")
        print(f"✅ Successfully sent: {results['sent']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"📈 Success rate: {(results['sent']/results['total']*100):.1f}%")
        
        if results['failed_emails']:
            print(f"\n❌ Failed email addresses:")
            for email in results['failed_emails']:
                print(f"  - {email}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in email sending: {str(e)}")
        return {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}


def send_personalized_emails_with_certificates(
    email_list_file: str,
    subject: str,
    body_template: str,
    config_file: str,
    certificates_dir: str
) -> dict:
    """Send personalized emails with individual certificate attachments"""
    try:
        # Load configuration
        config = load_simple_config(config_file)
        
        # Parse email list with names and emails
        recipients = []
        with open(email_list_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        email = parts[1].strip()
                        recipients.append({'name': name, 'email': email})
        
        if not recipients:
            print("❌ No valid recipients found in email list")
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
        results = {"sent": 0, "failed": 0, "total": len(recipients), "failed_emails": [], "missing_certificates": []}
        
        # Connect to SMTP
        sender = SimpleEmailSender(config)
        if not sender.connect():
            return results
        
        print(f"📤 Sending personalized emails...")
        print()
        
        for i, recipient in enumerate(recipients, 1):
            name = recipient['name']
            email = recipient['email']
            
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
                print(f"✅ Email sent successfully")
                
            except Exception as e:
                results["failed"] += 1
                results["failed_emails"].append(email)
                print(f"❌ Failed to send email: {str(e)}")
            
            print()
        
        sender.disconnect()
        
        # Print summary
        print("📊 Email Sending Summary:")
        print(f"Total recipients: {results['total']}")
        print(f"✅ Successfully sent: {results['sent']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"⚠️  Missing certificates: {len(results['missing_certificates'])}")
        print(f"📈 Success rate: {(results['sent']/results['total']*100):.1f}%")
        
        if results['failed_emails']:
            print(f"\n❌ Failed email addresses:")
            for email in results['failed_emails']:
                print(f"  - {email}")
        
        if results['missing_certificates']:
            print(f"\n⚠️  Missing certificates for:")
            for name in results['missing_certificates']:
                print(f"  - {name}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in email sending: {str(e)}")
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
    name_parts = normalized_name.split('_')
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
    normalized = re.sub(r'[^\w\s]', '', name)
    # Replace spaces with underscores and convert to lowercase
    normalized = re.sub(r'\s+', '_', normalized).lower()
    return normalized


def send_from_file(
    email_list_file: str,
    subject: str, 
    body_file: str,
    config_file: str,
    attachments_dir: str
) -> dict:
    """Send personalized emails from files with individual certificate attachments"""
    try:
        # Read email body from file
        with open(body_file, 'r', encoding='utf-8') as f:
            body_template = f.read()
        
        # Call the personalized email function
        return send_personalized_emails_with_certificates(
            email_list_file=email_list_file,
            subject=subject,
            body_template=body_template,
            config_file=config_file,
            certificates_dir=attachments_dir
        )
        
    except Exception as e:
        print(f"❌ Error reading files: {str(e)}")
        return {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}


if __name__ == "__main__":
    print("Simple Email Sender")
    print("Use the main CLI to run this automation:")
    print("python src/main.py send_bulk_emails --subject 'Your Subject Here'")
