---
icon: lucide/mail
---

# Email

Send bulk personalized emails with optional PDF attachments. Perfect for sending filled PDFs, newsletters, or notifications.

---

## Overview

The Email automation reads a list of recipients from a CSV file, personalizes each email using a template, and optionally attaches PDF files (like filled PDFs from `r10n fill-pdfs`).

**Key Features:**

- Send to multiple recipients from CSV
- Personalize emails with template variables
- Attach PDF files automatically
- Secure SMTP with TLS support
- Gmail App Password support

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n email
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n email
```

Example session:

```
╭───────────────────────────────────────────────────────────────╮
│                      Email Sender                              │
│          Send personalized emails with attachments             │
╰───────────────────────────────────────────────────────────────╯

Step 1/4: Select email configuration
  Enter path to email configuration [local/configs/email.json]: 

Step 2/4: Select recipients file
  Enter path to recipients CSV (Name,Email columns) [local/inputs/email/recipients.csv]: 

Step 3/4: Select email body template
  Enter path to email body template [local/inputs/email/template.txt]: 

Step 4/4: Select attachments directory
  Enter path to directory with PDF attachments [local/outputs/fill-pdfs]:
  Found 25 PDFs in: local/outputs/fill-pdfs

Summary:
  Config:       local/configs/email.json
  Recipients:   local/inputs/email/recipients.csv
  Body:         local/inputs/email/template.txt
  Attachments:  local/outputs/fill-pdfs

Warning: This will send real emails!
Proceed with sending emails? [y/n]: y

Sending emails...

Done!
┌─────────────────────┬──────────────────────────────┐
│ Total recipients    │ 25                           │
│ Sent successfully   │ 25                           │
│ Failed              │ 0                            │
└─────────────────────┴──────────────────────────────┘
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n email \
  --config local/configs/email.json \
  --recipients local/inputs/email/recipients.csv \
  --body local/inputs/email/template.txt \
  --attachments-dir local/outputs/fill-pdfs
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--config` | `-c` | string | Yes | `local/configs/email.json` | Email configuration file |
| `--recipients` | `-r` | string | Yes | `local/inputs/email/recipients.csv` | Recipients CSV file |
| `--body` | `-b` | string | Yes | `local/inputs/email/template.txt` | Email body template |
| `--attachments-dir` | `-d` | string | No | `local/outputs/fill-pdfs` | Directory with PDF attachments |

---

## Examples

### Example 1: Basic Usage with uvx

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email \
  --config email-config.json \
  --recipients contacts.csv \
  --body message.txt
```

### Example 2: With Certificate Attachments

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email \
  --config local/configs/email.json \
  --recipients local/inputs/email/recipients.csv \
  --body local/inputs/email/template.txt \
  --attachments-dir local/outputs/fill-pdfs
```

### Example 3: Local Installation

```bash
uv run r10n email \
  --config local/configs/email.json \
  --recipients local/inputs/email/recipients.csv \
  --body local/inputs/email/template.txt \
  --attachments-dir local/outputs/fill-pdfs
```

### Example 4: Interactive Mode

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email
```

---

## Input Files

### Recipients CSV

Create `local/inputs/email/recipients.csv`:

```csv
Name,Email
John Doe,john@example.com
Jane Smith,jane@example.com
Bob Johnson,bob@example.com
```

**Required columns:**

- `Name`: Recipient's name (used for personalization and matching PDF attachments)
- `Email`: Recipient's email address

### Email Template

Create `local/inputs/email/template.txt`:

```text
Dear {name},

Congratulations on completing the course!

Please find your certificate attached to this email.

Best regards,
The Team
```

**Available variables:**

| Variable | Description |
|----------|-------------|
| `{name}` | Recipient's name from CSV |

---

## Configuration

Create `local/configs/email.json`:

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "email": "your-email@gmail.com",
  "password": "your-app-password",
  "subject": "Your Certificate",
  "use_tls": true
}
```

### Configuration Options

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `smtp_server` | string | Yes | SMTP server address |
| `smtp_port` | number | Yes | SMTP port (587 for TLS, 465 for SSL) |
| `email` | string | Yes | Sender email address |
| `password` | string | Yes | SMTP password or App Password |
| `subject` | string | Yes | Email subject line |
| `use_tls` | boolean | No | Enable TLS encryption (default: true) |

### Gmail Setup

To use Gmail, you need an App Password:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate a new App Password for "Mail"
5. Use this 16-character password in your config

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "email": "your-email@gmail.com",
  "password": "abcd efgh ijkl mnop",
  "subject": "Your Certificate",
  "use_tls": true
}
```

### Other Email Providers

**Outlook/Hotmail:**
```json
{
  "smtp_server": "smtp-mail.outlook.com",
  "smtp_port": 587,
  "email": "your-email@outlook.com",
  "password": "your-password",
  "subject": "Your Certificate",
  "use_tls": true
}
```

**Yahoo Mail:**
```json
{
  "smtp_server": "smtp.mail.yahoo.com",
  "smtp_port": 587,
  "email": "your-email@yahoo.com",
  "password": "your-app-password",
  "subject": "Your Certificate",
  "use_tls": true
}
```

---

## PDF Attachments

The automation matches PDFs to recipients by name:

1. PDF files should be named like: `John_Doe.pdf`
2. The automation looks for a PDF matching each recipient's name
3. If found, it attaches the PDF to that recipient's email

**Example structure:**

```
local/outputs/fill-pdfs/
+-- John_Doe.pdf
+-- Jane_Smith.pdf
+-- Bob_Johnson.pdf
```

---

## Output

The automation logs results for each email:

```
Sending emails...

[1/3] Sending to john@example.com... ✓
[2/3] Sending to jane@example.com... ✓
[3/3] Sending to bob@example.com... ✓

Done!
┌─────────────────────┬──────────────────────────────┐
│ Total recipients    │ 3                            │
│ Sent successfully   │ 3                            │
│ Failed              │ 0                            │
└─────────────────────┴──────────────────────────────┘
```

---

## Troubleshooting

### "Authentication failed"

- Check your email and password in the config
- For Gmail, use an App Password (not your regular password)
- Ensure 2-Step Verification is enabled for Gmail

### "Connection refused"

- Check your SMTP server and port
- Ensure your firewall allows outgoing connections on port 587
- Try port 465 with SSL if TLS doesn't work

### "PDF not found for recipient"

- Ensure PDF filenames match recipient names exactly
- Check for spaces vs underscores: `John Doe` should have `John_Doe.pdf`

### Emails Going to Spam

- Use a proper sender email address
- Add a descriptive subject line
- Avoid spam trigger words in your template
- Consider using a transactional email service for bulk sends

### Rate Limiting

- Gmail limits sending to ~100 emails per day for free accounts
- Add delays between sends for large batches
- Consider using a dedicated email service for high volume

---

## Security Notes

1. **Never commit credentials**: Add `local/` to `.gitignore`
2. **Use App Passwords**: Never use your main email password
3. **Test first**: Send to yourself before bulk sending
4. **Review recipients**: Double-check your CSV before sending

---

## See Also

- [Fill PDFs Automation](fill-pdfs.md) -- Generate filled PDFs to attach
- [Contacts Automation](contacts.md) — Generate contact cards
- [Get Started Guide](../get-started/index.md) — Setup instructions
