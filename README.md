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

---

### 📬 Outlook Email with Individual Attachments
Sends personalized emails with individual attachments to each recipient via Outlook.

**Steps:**
1. **Setup Outlook configuration** in `data/outlook/email_config.json`:
   ```json
   {
     "smtp_server": "smtp.office365.com",
     "smtp_port": 587,
     "sender_email": "your_email@outlook.com",
     "password": "your_app_password",
     "subject": "Your Certificate"
   }
   ```

2. **Add recipients with their attachments** in `data/outlook/recipients.txt`:
   ```
   Student One,student1@outlook.com,student1.pdf
   Student Two,student2@outlook.com,student2.pdf
   ```

3. **Create email template** in `data/outlook/email.txt` (use `{name}` for personalization):
   ```
   Hi {name},
   
   Please find your certificate attached.
   
   Best regards,
   Your Name
   ```

4. **Add certificate files** to `data/outlook/certificates/` folder

5. **Run the automation:**
   ```bash
   python src/main.py send_outlook_emails
   ```

**Features:**
- ✅ Personalized emails with recipient names
- ✅ Individual attachments per recipient
- ✅ Outlook/Office365 SMTP support
- ✅ Certificate file validation
- ✅ Detailed sending reports

## Project Structure

```
data/
├── emails/                    # Bulk email automation assets
│   ├── email_config.json     # Your Gmail/email settings
│   ├── email_list.txt        # Paste email addresses here
│   ├── email.txt             # Paste email message here
│   └── attachments/          # Add files to attach
├── outlook/                   # Outlook email automation assets
│   ├── email_config.json     # Your Outlook settings
│   ├── recipients.txt        # Recipients with attachment filenames
│   ├── email.txt             # Email template with {name} placeholder
│   └── certificates/         # Individual attachment files
├── phone_numbers/            # Contact generation assets
│   ├── numbers.txt           # Paste phone numbers here
│   └── *.vcf                 # Generated contact files
src/
├── automations/              # Automation scripts
└── main.py                   # Main CLI interface
```

## Security Notes

- **Gmail Users:** Use App Passwords instead of regular passwords
- **Outlook Users:** Enable 2FA and create App Passwords for email sending
- **Never commit** config files with real credentials
- **Test first** with a small recipient list

## Getting Help

Run any automation without arguments to see available options:
```bash
python src/main.py generate_contacts --help
python src/main.py send_bulk_emails --help
python src/main.py send_outlook_emails --help
```
