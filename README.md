# Automations

This is a Python automation project with organized data folders for easy use.

## Quick Start

1. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Choose your automation and paste your data into the appropriate files**

## Available Automations

### 📞 Contact Card Generator
Converts phone numbers to VCF contact files for importing into your phone.

**Steps:**
1. **Paste your phone numbers** into `data/phone_numbers/numbers.txt` (one per line)
2. **Run the automation:**
   ```bash
   python src/main.py generate_contacts
   ```
3. **Find your VCF file** in `data/phone_numbers/` directory

**Example:**
```bash
# Generate contacts with custom prefix
python src/main.py generate_contacts --prefix "Workshop Participant"
```

**Supported Phone Formats:**
- 0712345678 (Sri Lankan)
- +94712345678 (International)
- 071 234 5678 (With spaces)

---

### 📧 Bulk Email Sender
Sends the same email to multiple recipients with enhanced deliverability.

**Steps:**
1. **Setup email configuration** in `data/emails/email_config.json`:
   ```json
   {
     "smtp_server": "smtp.gmail.com",
     "smtp_port": 587,
     "email": "your_email@gmail.com",
     "password": "your_app_password",
     "sender_name": "Your Name",
     "organization": "Your Organization"
   }
   ```

2. **Paste your email addresses** into `data/emails/email_list.txt` (one per line)

3. **Paste your email message** into `data/emails/email.txt`

4. **Add attachments** (optional) to `data/emails/attachments/`

5. **Run the automation:**
   ```bash
   python src/main.py send_bulk_emails --subject "Your Email Subject"
   ```

**Example:**
```bash
python src/main.py send_bulk_emails --subject "Workshop Invitation - Join Us Today!"
```

**Features:**
- ✅ Anti-spam headers and formatting
- ✅ Rate limiting to protect sender reputation
- ✅ Professional organization footer
- ✅ Attachment support
- ✅ Detailed delivery reporting

## Project Structure

```
data/
├── emails/                    # Email automation assets
│   ├── email_config.json     # Your email settings
│   ├── email_list.txt        # Paste email addresses here
│   ├── email.txt             # Paste email message here
│   └── attachments/          # Add files to attach
├── phone_numbers/            # Contact generation assets
│   ├── numbers.txt           # Paste phone numbers here
│   └── *.vcf                 # Generated contact files
src/
├── automations/              # Automation scripts
└── main.py                   # Main CLI interface
```

## Security Notes

- **Gmail Users:** Use App Passwords instead of regular passwords
- **Never commit** `email_config.json` with real credentials
- **Test first** with a small email list

## Getting Help

Run any automation without arguments to see available options:
```bash
python src/main.py generate_contacts --help
python src/main.py send_bulk_emails --help
```
