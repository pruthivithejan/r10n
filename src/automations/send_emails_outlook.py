import smtplib
import os
import json
import csv
import time
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def load_recipients(recipients_file):
    """Load recipients from CSV file"""
    recipients = []
    try:
        with open(recipients_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for line_num, row in enumerate(reader, 1):
                # Skip empty lines and comments
                if not row or row[0].strip().startswith('#'):
                    continue
                
                if len(row) >= 3:
                    recipients.append({
                        'name': row[0].strip(),
                        'email': row[1].strip(),
                        'file': row[2].strip()
                    })
                else:
                    print(f"Warning: Invalid format on line {line_num} in {recipients_file}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Recipients file not found: {recipients_file}")
    except Exception as e:
        raise Exception(f"Error reading recipients file: {str(e)}")
    
    return recipients


def load_email_config(config_file):
    """Load email configuration from JSON file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = ['smtp_server', 'smtp_port', 'sender_email', 'password', 'subject']
        for key in required_keys:
            if key not in config:
                raise KeyError(f"Missing required configuration key: {key}")
        
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in configuration file: {str(e)}")


def load_email_body(body_file):
    """Load email body template from file"""
    try:
        with open(body_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Email body file not found: {body_file}")


def send_outlook_emails_with_attachments(recipients_file, email_body_file, config_file, certificates_dir):
    """
    Send personalized emails with individual attachments via Outlook SMTP
    
    Args:
        recipients_file: Path to CSV file with recipient data
        email_body_file: Path to email body template file
        config_file: Path to email configuration JSON file
        certificates_dir: Directory containing certificate files
    
    Returns:
        dict: Summary of sending results
    """
    
    # Load configuration and data
    config = load_email_config(config_file)
    recipients = load_recipients(recipients_file)
    body_template = load_email_body(email_body_file)
    
    if not recipients:
        print("No valid recipients found.")
        return {'total': 0, 'sent': 0, 'failed': 0, 'errors': []}
    
    print(f"Loaded {len(recipients)} recipients")
    print(f"Using SMTP server: {config['smtp_server']}:{config['smtp_port']}")
    print(f"Sender: {config['sender_email']}")
    print(f"Certificates directory: {certificates_dir}")
    
    # Validate certificates directory
    if not os.path.exists(certificates_dir):
        raise FileNotFoundError(f"Certificates directory not found: {certificates_dir}")
    
    # Initialize counters
    sent_count = 0
    failed_count = 0
    errors = []
    
    try:
        # Connect to SMTP server
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['sender_email'], config['password'])
            print("Successfully connected to Outlook SMTP server")
            
            for i, recipient in enumerate(recipients, 1):
                try:
                    print(f"\n[{i}/{len(recipients)}] Processing {recipient['email']}...")
                    
                    # Create the email
                    msg = MIMEMultipart()
                    msg["From"] = config['sender_email']
                    msg["To"] = recipient["email"]
                    msg["Subject"] = config['subject']
                    
                    # Add personalized body
                    body = body_template.format(name=recipient["name"])
                    msg.attach(MIMEText(body, "plain"))
                    
                    # Attach certificate file
                    file_path = os.path.join(certificates_dir, recipient["file"])
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            part = MIMEApplication(f.read(), Name=recipient["file"])
                            part['Content-Disposition'] = f'attachment; filename="{recipient["file"]}"'
                            msg.attach(part)
                        print(f"  ✓ Attached: {recipient['file']}")
                    else:
                        error_msg = f"Certificate file not found: {file_path}"
                        print(f"  ✗ {error_msg}")
                        errors.append(f"{recipient['email']}: {error_msg}")
                        failed_count += 1
                        continue
                    
                    # Send the email
                    server.send_message(msg)
                    sent_count += 1
                    print(f"  ✓ Email sent successfully to {recipient['email']}")
                    
                    # Small delay to avoid overwhelming the server
                    time.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Failed to send to {recipient['email']}: {str(e)}"
                    print(f"  ✗ {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1
                    continue
    
    except Exception as e:
        raise Exception(f"SMTP connection error: {str(e)}")
    
    # Print summary
    print(f"\n{'='*50}")
    print("EMAIL SENDING SUMMARY")
    print(f"{'='*50}")
    print(f"Total recipients: {len(recipients)}")
    print(f"Successfully sent: {sent_count}")
    print(f"Failed: {failed_count}")
    
    if errors:
        print(f"\nErrors:")
        for error in errors:
            print(f"  - {error}")
    
    return {
        'total': len(recipients),
        'sent': sent_count, 
        'failed': failed_count,
        'errors': errors
    }


def send_from_file(recipients_file='data/outlook/recipients.txt', 
                  email_body_file='data/outlook/email.txt',
                  config_file='data/outlook/email_config.json',
                  certificates_dir='data/outlook/certificates'):
    """
    Convenience function to send emails using default file paths
    """
    return send_outlook_emails_with_attachments(
        recipients_file, email_body_file, config_file, certificates_dir
    )