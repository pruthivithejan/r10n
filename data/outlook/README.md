# Outlook Email Automation

This folder contains the data files for the Outlook email automation with attachments.

## Files:

### `recipients.txt`
CSV format with recipient information:
```
Name,Email,Certificate_Filename
Student One,student1@outlook.com,student1.pdf
```

### `email.txt`
Email body template. Use `{name}` as placeholder for recipient name.

### `email_config.json`
Outlook SMTP configuration:
- Update `sender_email` with your Outlook email
- Update `password` with your App Password (recommended) or account password
- Modify `subject` as needed

### `certificates/`
Place all certificate PDF files in this folder. Filenames should match those listed in `recipients.txt`.

## Setup:
1. Enable 2FA on your Outlook account
2. Generate an App Password for email sending
3. Update the config file with your credentials
4. Add recipients to `recipients.txt`
5. Place certificate files in `certificates/` folder

## Usage:
```bash
python src/main.py send_outlook_emails --subject "Your Certificate"
```
