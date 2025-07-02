# Setup Guide for Automations

This guide will help you set up the automation system from scratch.

## Prerequisites

1. **Python 3.8+** installed on your system
2. **Git** installed (to clone the repository)
3. **Gmail or Outlook account** (for email automations)

## Initial Setup

### 1. Clone the Repository
```bash
git clone https://github.com/pruthivithejan/automations.git
cd automations
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Data Folder Structure
```bash
mkdir -p data/{emails,outlook,certificates/{templates,output},phone_numbers}
mkdir -p data/emails/attachments
mkdir -p data/outlook/certificates
```

## Configuration Setup

### Email Automation Setup

#### For Gmail:
1. **Enable 2-Factor Authentication** on your Google account
2. **Generate App Password:**
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
   - Copy the 16-character password

3. **Copy example files:**
   ```bash
   cp examples/emails/email_config.json.example data/emails/email_config.json
   cp examples/emails/email_list.txt.example data/emails/email_list.txt
   cp examples/emails/email.txt.example data/emails/email.txt
   ```

4. **Edit configuration:**
   - Open `data/emails/email_config.json`
   - Replace placeholders with your actual information:
     ```json
     {
       "smtp_server": "smtp.gmail.com",
       "smtp_port": 587,
       "email": "your_actual_email@gmail.com",
       "password": "your_16_char_app_password",
       "sender_name": "Your Actual Name",
       "organization": "Your Organization"
     }
     ```

#### For Outlook:
1. **Copy example files:**
   ```bash
   cp examples/outlook/email_config.json.example data/outlook/email_config.json
   cp examples/outlook/recipients.txt.example data/outlook/recipients.txt
   cp examples/outlook/email.txt.example data/outlook/email.txt
   ```

2. **Edit configuration** with your Outlook credentials

### Certificate Generation Setup

1. **Copy example files:**
   ```bash
   cp examples/certificates/config.json.example data/certificates/config.json
   cp examples/certificates/recipients.txt.example data/certificates/recipients.txt
   ```

2. **Add your certificate template:**
   - Place your blank PDF certificate in `data/certificates/templates/`
   - Update the `template_pdf` path in `config.json`

3. **Configure field positions:**
   - Use a PDF viewer to find X,Y coordinates
   - Update the `fields` section in `config.json`

### Phone Numbers Setup

1. **Copy example file:**
   ```bash
   cp examples/phone_numbers/numbers.txt.example data/phone_numbers/numbers.txt
   ```

2. **Add your phone numbers** (one per line)

## Usage Examples

### Send Bulk Emails
```bash
python src/main.py send_bulk_emails --subject "Welcome to Our Workshop!"
```

### Generate Certificates
```bash
python src/main.py fill_certificates
```

### Create Contact Cards
```bash
python src/main.py generate_contacts --prefix "Workshop Participant"
```

### Send Outlook Emails
```bash
python src/main.py send_outlook_emails
```

## Security Best Practices

1. **Never commit real credentials** to version control
2. **Use App Passwords** instead of regular passwords
3. **Test with small lists** before bulk operations
4. **Keep the data folder local** (it's in .gitignore)
5. **Regularly update passwords** and review access

## Troubleshooting

### Common Issues:

1. **"Authentication failed"**
   - Verify you're using App Password, not regular password
   - Check 2FA is enabled
   - Ensure correct email/password in config

2. **"File not found"**
   - Verify all required files exist in data/ folders
   - Check file paths in configuration files

3. **"Permission denied"**
   - Activate virtual environment
   - Check file permissions
   - Run from project root directory

4. **"Module not found"**
   - Activate virtual environment
   - Run `pip install -r requirements.txt`

### Getting Help

Run any command with `--help` to see available options:
```bash
python src/main.py send_bulk_emails --help
python src/main.py fill_certificates --help
python src/main.py generate_contacts --help
python src/main.py send_outlook_emails --help
```

## File Structure After Setup

```
data/                          # Your local data (not in git)
├── emails/
│   ├── email_config.json     # Your Gmail credentials
│   ├── email_list.txt        # Tab-separated names and emails
│   ├── email.txt             # Email template with {name} placeholder
│   └── attachments/          # Individual certificate files
├── outlook/
│   ├── email_config.json     # Your Outlook credentials
│   ├── recipients.txt        # Name,email,filename format
│   ├── email.txt             # Email template
│   └── certificates/         # Certificate files
├── certificates/
│   ├── config.json           # Field positions and styling
│   ├── recipients.txt        # Name,course,date,achievement
│   ├── templates/            # Your blank PDF templates
│   └── output/               # Generated certificates
└── phone_numbers/
    └── numbers.txt           # Phone numbers list
```

## Next Steps

1. **Start with a test:** Use small lists to verify everything works
2. **Customize templates:** Modify email templates and certificate layouts
3. **Automate workflows:** Create scripts for repeated tasks
4. **Scale up:** Process larger lists once testing is complete

Happy automating! 🚀
