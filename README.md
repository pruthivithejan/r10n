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

---

### 📄 Certificate Generator
Fills blank PDF certificate templates with recipient information and generates personalized certificates.

**Steps:**
1. **Create or obtain a blank certificate PDF template** and place it in `data/certificates/templates/`

2. **Configure field positions** in `data/certificates/config.json`:
   ```json
   {
     "template_pdf": "templates/certificate_template.pdf",
     "output_directory": "output",
     "fields": {
       "name": {
         "x": 396, "y": 370,
         "font_size": 28, "font_weight": "bold",
         "color": [0, 0, 139], "alignment": "center"
       },
       "course": {
         "x": 396, "y": 270,
         "font_size": 20, "font_weight": "bold",
         "color": [0, 0, 0], "alignment": "center"
       }
     }
   }
   ```

3. **Add recipients** in `data/certificates/recipients.txt`:
   ```
   John Smith,Workshop on AI,2024-06-28,Excellent Performance
   Jane Doe,Data Science Bootcamp,2024-06-25,Outstanding Achievement
   ```

4. **Run the automation:**
   ```bash
   python src/main.py fill_certificates
   ```

5. **Find generated certificates** in `data/certificates/output/`

**Features:**
- ✅ PDF template overlay with precise positioning
- ✅ Customizable fonts, sizes, colors, and alignment
- ✅ Support for multiple data fields (name, course, date, achievement)
- ✅ Automatic filename generation from recipient names
- ✅ Batch processing with detailed progress reports

## Project Structure

```
data/                          # Data folder (excluded from git)
├── attachments/              # General attachments
├── certificates/             # Certificate generation assets
│   ├── config.json          # Field positions and styling
│   ├── recipients.txt       # Recipients with course/achievement data
│   ├── recipients_ex.txt    # Example recipients file
│   ├── templates/           # Blank PDF certificate templates
│   │   ├── CryptX.pdf      # Certificate template
│   │   └── Participants.pdf # Alternative template
│   └── output/              # Generated personalized certificates
├── email_config.json        # Global email configuration
├── email_config_enhanced.json # Enhanced email settings
├── email_config_template.md # Email config template/documentation
├── email_lists/             # Email list files
│   ├── icts_participants.txt # Workshop participants
│   └── icts_workshop_emails.csv # CSV format email lists
├── email_templates/         # Email template files
│   ├── icts_workshop_body.txt # Workshop email body
│   └── icts_workshop_enhanced.txt # Enhanced email template
├── emails/                  # Bulk email automation assets
│   ├── email_config.json   # Your Gmail/email settings
│   ├── email_list.txt      # Paste email addresses here (tab-separated name\temail)
│   ├── email.txt           # Paste email message here (supports {name} placeholder)
│   └── attachments/        # Individual certificate files for personalized sending
├── outlook/                 # Outlook email automation assets
│   ├── email_config.json   # Your Outlook settings
│   ├── recipients.txt      # Recipients with attachment filenames
│   ├── email.txt           # Email template with {name} placeholder
│   └── certificates/       # Individual attachment files
└── phone_numbers/          # Contact generation assets
    ├── numbers.txt         # Paste phone numbers here
    ├── sample_numbers.txt  # Example phone numbers
    ├── envision_contacts.vcf # Generated contact files
    ├── numbers_contacts.vcf # Generated contact files
    └── *.vcf               # Other generated contact files

src/
├── automations/            # Automation scripts
│   ├── fill_certificates.py # Certificate generation
│   ├── generate_contacts.py # Contact VCF generation
│   ├── send_emails_outlook.py # Outlook email sending
│   ├── send_enhanced_emails.py # Enhanced email features
│   └── send_same_email.py  # Bulk/personalized email sending
├── utils/                  # Utility modules
│   ├── email_template_generator.py # Email template utilities
│   └── file_utils.py       # File handling utilities
└── main.py                 # Main CLI interface

docs/                       # Documentation
├── email_deliverability_guide.md # Email best practices
└── PROJECT_SUMMARY.md      # Project overview

tests/                      # Test files
└── test_main.py           # Main tests
```

## Security Notes

- **Gmail Users:** Use App Passwords instead of regular passwords
- **Outlook Users:** Enable 2FA and create App Passwords for email sending
- **Data folder is excluded from git:** The entire `data/` folder is in `.gitignore` to protect sensitive information like email addresses, certificates, and configuration files
- **Never commit** config files with real credentials to version control
- **Test first** with a small recipient list before running bulk operations

## Getting Help

Run any automation without arguments to see available options:
```bash
python src/main.py generate_contacts --help
python src/main.py send_bulk_emails --help
python src/main.py send_outlook_emails --help
python src/main.py fill_certificates --help
```
