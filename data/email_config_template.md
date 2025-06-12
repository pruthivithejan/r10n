# Email Configuration Template

Copy this file to `data/email_config_enhanced.json` and update with your email settings.

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "email": "your_email@gmail.com",
  "password": "your_app_password",
  "use_tls": true,
  "sender_name": "Your Name",
  "organization": "Your Organization Name",
  "rate_limit_delay": 3,
  "batch_size": 5,
  "batch_delay": 60
}
```

## Configuration Options:

- **smtp_server**: Your email provider's SMTP server
- **smtp_port**: SMTP port (usually 587 for TLS)
- **email**: Your email address
- **password**: Your email password or app password
- **use_tls**: Enable TLS encryption (recommended: true)
- **sender_name**: Your display name in emails
- **organization**: Your organization name (appears in email headers)
- **rate_limit_delay**: Seconds to wait between individual emails
- **batch_size**: Number of emails per batch
- **batch_delay**: Seconds to wait between batches

## Gmail Setup:
1. Enable 2-Factor Authentication
2. Generate an App Password
3. Use the App Password in the config file
