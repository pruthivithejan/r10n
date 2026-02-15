"""MCP tool for sending bulk personalized emails."""

from src.automations.send_same_email import send_personalized_emails_with_certificates
from src.mcp.server import mcp


@mcp.tool()
def send_email(
    email_list_file: str,
    subject: str,
    body_template: str,
    config_file: str,
    certificates_dir: str | None = None,
) -> dict:
    """Send bulk personalized emails with optional certificate attachments.

    Args:
        email_list_file: Path to CSV file with Name and Email columns.
        subject: Email subject line.
        body_template: Path to email body template file (use {name} for personalization).
        config_file: Path to SMTP configuration JSON file.
        certificates_dir: Directory with PDF certificate attachments (optional).
    """
    try:
        return send_personalized_emails_with_certificates(
            email_list_file=email_list_file,
            subject=subject,
            body_template=body_template,
            config_file=config_file,
            certificates_dir=certificates_dir or "",
        )
    except Exception as e:
        return {"error": str(e)}
