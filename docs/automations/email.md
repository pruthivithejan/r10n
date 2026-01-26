---
icon: material/email
---

# Email Automation

Bulk send personalized emails — with optional certificate attachments — to a list of recipients securely.

## What It Does
- Reads contacts from CSV
- Fills in template variables in your message
- Handles SMTP configuration securely
- Can attach PDFs (e.g., from Certificates automation)

## Usage

Interactive:
```bash
uv run r10n email
```

Command-line:
```bash
uv run r10n email --config local/configs/email.json --recipients local/inputs/email/recipients.csv --template local/inputs/email/template.txt
```

Run with uv / uvx

Run instantly (no install):

```
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email
```

Install locally and run:

```
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n email --config local/configs/email.json --recipients local/inputs/email/recipients.csv --template local/inputs/email/template.txt
```

## Quick Start Steps
1. Set up `local/configs/email.json` with SMTP and credentials:
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
   - Gmail: use an [App Password](https://support.google.com/accounts/answer/185833)
2. Create `local/inputs/email/recipients.csv`:
   ```csv
   Name,Email
   John Doe,john@example.com
   Jane Smith,jane@example.com
   ```
3. Draft message `local/inputs/email/template.txt`:
   ```text
   Dear {name},

   Congratulations! Please find your certificate attached.
   Best regards,
   The Team
   ```
4. Generate certificates beforehand (if attaching)
5. Run the automation

## Input Files
- CSV for contacts, TXT for message template
- Optional: certificates in `local/outputs/certificates/`

## Options
| Option       | Description                       |
|--------------|-----------------------------------|
| `--config`   | Path to email/config JSON          |
| `--recipients` | Path to recipients CSV file      |
| `--template` | Email template TXT                |

## Troubleshooting
- If you get authentication errors, check your SMTP/App Password
- Output/attachment problems? Make sure certificates exist and files are readable
