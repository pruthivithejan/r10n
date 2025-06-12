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


def send_from_file(
    emails_file: str,
    subject: str,
    body_file: str,
    config_file: str = "data/email_config.json",
    attachments_dir: str = "data/attachments"
):
    """Send emails from a file containing email addresses and body from a text file"""
    try:
        # Read email addresses from file
        with open(emails_file, 'r') as f:
            email_list = [line.strip() for line in f if line.strip() and '@' in line]
        
        # Read email body from file
        with open(body_file, 'r') as f:
            body = f.read()
        
        # Get attachments if directory exists
        attachments = []
        if Path(attachments_dir).exists():
            for file_path in Path(attachments_dir).iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    attachments.append(str(file_path))
        
        print(f"📧 Found {len(email_list)} email addresses")
        print(f"📎 Found {len(attachments)} attachments")
        
        return send_same_email_to_all(email_list, subject, body, config_file, attachments if attachments else None)
        
    except Exception as e:
        print(f"❌ Error reading files: {str(e)}")
        return {"sent": 0, "failed": 0, "total": 0, "failed_emails": []}


if __name__ == "__main__":
    # Example usage
    example_emails = [
        "pruthivithejan@outlook.com",
        "ict22930@fot.sjp.ac.lk",
        "ict22911@fot.sjp.ac.lk",
        "ict22915@fot.sjp.ac.lk"
    ]
    
    example_subject = "[ Join ICTS ] Today and Maximize Your Envision Workshop Experience!"
    
    example_body = """Dear Participant,

Thank you for signing up for the Envision Workshop organized by ICTS. We're thrilled to have you on board for this exciting event that promises to offer valuable insights and opportunities.

To make the most out of your Envision Workshop experience and gain access to exclusive resources, we warmly invite you to become an ICTS member. Membership with ICTS opens doors to a vibrant community, exclusive events, and continuous learning opportunities.

Joining is simple! Please complete the membership form via the following link: https://forms.gle/4iDrYcB2QrJBniWn9

Sincerely,
Pruthivi Thejan,
Assistant Secretary, ICTS"""
    
    print("Simple Email Sender")
    print("Use the main CLI to run this automation:")
    print("python src/main.py send_same_email <emails_file> <subject> <body_file> [options]")
