import smtplib
import csv
import json
import pandas as pd
import time
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, make_msgid
from pathlib import Path
from typing import List, Dict, Optional, Union
import os
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EmailConfig:
    """Email configuration settings with deliverability options"""
    smtp_server: str
    smtp_port: int
    email: str
    password: str
    use_tls: bool = True
    sender_name: str = ""
    organization: str = ""
    rate_limit_delay: int = 2  # seconds between emails
    batch_size: int = 10  # emails per batch
    batch_delay: int = 30  # seconds between batches


@dataclass
class EmailData:
    """Individual email data with deliverability features"""
    to_email: str
    subject: str
    body: str
    attachments: List[str] = None
    cc: List[str] = None
    bcc: List[str] = None
    reply_to: str = None
    organization_footer: bool = True


class EnhancedBulkEmailSender:
    def __init__(self, config: EmailConfig):
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
    
    def add_deliverability_headers(self, msg: MIMEMultipart, email_data: EmailData):
        """Add headers to improve deliverability"""
        # Message ID for uniqueness
        msg['Message-ID'] = make_msgid()
        
        # Date header
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Reply-To header
        if email_data.reply_to:
            msg['Reply-To'] = email_data.reply_to
        else:
            msg['Reply-To'] = self.config.email
        
        # List-Unsubscribe header (important for deliverability)
        if email_data.reply_to:
            msg['List-Unsubscribe'] = f'<mailto:{email_data.reply_to}?subject=Unsubscribe>'
        else:
            msg['List-Unsubscribe'] = f'<mailto:{self.config.email}?subject=Unsubscribe>'
        
        # Organization headers
        if self.config.organization:
            msg['Organization'] = self.config.organization
        
        # Precedence header to indicate bulk mail
        msg['Precedence'] = 'bulk'
        
        # Auto-Submitted header
        msg['Auto-Submitted'] = 'auto-generated'
    
    def add_organization_footer(self, body: str) -> str:
        """Add professional footer to email body"""
        footer = "\n\n" + "="*50 + "\n"
        
        if self.config.organization:
            footer += f"{self.config.organization}\n"
        
        footer += f"Email: {self.config.email}\n"
        
        footer += "\nTo unsubscribe from these emails, please reply with 'UNSUBSCRIBE' in the subject line.\n"
        footer += "This email was sent to you because you signed up for our workshop or services."
        
        return body + footer
    
    def create_message(self, email_data: EmailData) -> MIMEMultipart:
        """Create email message with deliverability best practices"""
        msg = MIMEMultipart()
        
        # From header with proper formatting
        if self.config.sender_name:
            msg['From'] = formataddr((self.config.sender_name, self.config.email))
        else:
            msg['From'] = self.config.email
        
        msg['To'] = email_data.to_email
        msg['Subject'] = email_data.subject
        
        # Add CC and BCC if provided
        if email_data.cc:
            msg['Cc'] = ', '.join(email_data.cc)
        if email_data.bcc:
            msg['Bcc'] = ', '.join(email_data.bcc)
        
        # Add deliverability headers
        self.add_deliverability_headers(msg, email_data)
        
        # Prepare email body
        body = email_data.body
        if email_data.organization_footer:
            body = self.add_organization_footer(body)
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        if email_data.attachments:
            for file_path in email_data.attachments:
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
    
    def send_email(self, email_data: EmailData) -> bool:
        """Send a single email"""
        try:
            msg = self.create_message(email_data)
            
            # Prepare recipient list (including CC and BCC)
            recipients = [email_data.to_email]
            if email_data.cc:
                recipients.extend(email_data.cc)
            if email_data.bcc:
                recipients.extend(email_data.bcc)
            
            self.smtp_connection.send_message(msg, to_addrs=recipients)
            return True
        except Exception as e:
            print(f"❌ Failed to send email to {email_data.to_email}: {str(e)}")
            return False
    
    def send_bulk_emails_with_throttling(self, email_list: List[EmailData]) -> Dict[str, int]:
        """Send multiple emails with rate limiting and batching for better deliverability"""
        results = {"sent": 0, "failed": 0, "total": len(email_list)}
        
        if not self.connect():
            return results
        
        print(f"📧 Starting to send {len(email_list)} emails with rate limiting...")
        print(f"⏱️  Rate limit: {self.config.rate_limit_delay}s between emails")
        print(f"📦 Batch size: {self.config.batch_size} emails per batch")
        print(f"⏳ Batch delay: {self.config.batch_delay}s between batches")
        
        for i, email_data in enumerate(email_list, 1):
            print(f"📤 Sending email {i}/{len(email_list)} to {email_data.to_email}...")
            
            if self.send_email(email_data):
                results["sent"] += 1
                print(f"✅ Email sent successfully")
            else:
                results["failed"] += 1
            
            # Rate limiting between individual emails
            if i < len(email_list):  # Don't delay after the last email
                time.sleep(self.config.rate_limit_delay)
            
            # Batch delay
            if i % self.config.batch_size == 0 and i < len(email_list):
                print(f"⏸️  Batch completed. Waiting {self.config.batch_delay} seconds...")
                time.sleep(self.config.batch_delay)
        
        self.disconnect()
        return results


def load_enhanced_email_config(config_path: str) -> EmailConfig:
    """Load enhanced email configuration from JSON file"""
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    return EmailConfig(
        smtp_server=config_data['smtp_server'],
        smtp_port=config_data['smtp_port'],
        email=config_data['email'],
        password=config_data['password'],
        use_tls=config_data.get('use_tls', True),
        sender_name=config_data.get('sender_name', ''),
        organization=config_data.get('organization', ''),
        rate_limit_delay=config_data.get('rate_limit_delay', 2),
        batch_size=config_data.get('batch_size', 10),
        batch_delay=config_data.get('batch_delay', 30)
    )


def send_same_email_enhanced(
    recipients_file: str,
    subject: str,
    body_file: str,
    config_file: str = "data/email_config.json"
):
    """Enhanced version with better deliverability"""
    try:
        # Load configuration
        config = load_enhanced_email_config(config_file)
        
        # Read recipients
        with open(recipients_file, 'r') as f:
            recipients = [line.strip() for line in f if line.strip()]
        
        # Read email body
        with open(body_file, 'r') as f:
            body = f.read()
        
        # Create email data for each recipient
        emails = []
        for recipient in recipients:
            email_data = EmailData(
                to_email=recipient,
                subject=subject,
                body=body,
                reply_to=config.email,
                organization_footer=True
            )
            emails.append(email_data)
        
        # Send emails with enhanced deliverability
        sender = EnhancedBulkEmailSender(config)
        results = sender.send_bulk_emails_with_throttling(emails)
        
        # Print summary
        print("\n📊 Enhanced Email Sending Summary:")
        print(f"Total emails: {results['total']}")
        print(f"✅ Successfully sent: {results['sent']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"📈 Success rate: {(results['sent']/results['total']*100):.1f}%")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in enhanced bulk email sending: {str(e)}")
        return {"sent": 0, "failed": 0, "total": 0}


if __name__ == "__main__":
    print("Enhanced Bulk Email Sender with Deliverability Features")
    print("Use the main CLI to run this automation")
    print("python src/main.py send_enhanced_emails <recipients_file> <subject> <body_file>")
