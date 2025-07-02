# Example Configuration Files

This folder contains example configuration files and templates to help you set up the automation system.

## 📁 Folder Structure

```
examples/
├── SETUP_GUIDE.md           # Complete setup instructions
├── emails/                  # Email automation examples
│   ├── email_config.json.example    # Gmail SMTP configuration
│   ├── email_list.txt.example       # Tab-separated names and emails
│   └── email.txt.example            # Email template with placeholders
├── outlook/                 # Outlook automation examples
│   ├── email_config.json.example    # Outlook SMTP configuration
│   ├── recipients.txt.example       # Recipients with attachments
│   └── email.txt.example            # Outlook email template
├── certificates/            # Certificate generation examples
│   ├── config.json.example          # PDF field positioning
│   └── recipients.txt.example       # Recipients with course data
└── phone_numbers/           # Contact generation examples
    └── numbers.txt.example          # Phone numbers list
```

## 🚀 Quick Start

1. **Copy the example files** to your `data/` folder (remove `.example` extension):
   ```bash
   # For email automation
   cp examples/emails/email_config.json.example data/emails/email_config.json
   cp examples/emails/email_list.txt.example data/emails/email_list.txt
   cp examples/emails/email.txt.example data/emails/email.txt
   
   # For certificate generation
   cp examples/certificates/config.json.example data/certificates/config.json
   cp examples/certificates/recipients.txt.example data/certificates/recipients.txt
   
   # For phone numbers
   cp examples/phone_numbers/numbers.txt.example data/phone_numbers/numbers.txt
   
   # For Outlook
   cp examples/outlook/email_config.json.example data/outlook/email_config.json
   cp examples/outlook/recipients.txt.example data/outlook/recipients.txt
   cp examples/outlook/email.txt.example data/outlook/email.txt
   ```

2. **Edit the configuration files** with your actual credentials and data

3. **Follow the SETUP_GUIDE.md** for detailed instructions

## ⚠️ Important Notes

- **Never use the example files directly** - they contain placeholder data
- **Always copy to the `data/` folder** and customize with your information
- **Keep your real credentials secure** - the `data/` folder is excluded from git
- **Test with small lists first** before running bulk operations

## 🔧 Configuration Tips

### Email Templates
- Use `{name}` placeholder for personalization
- Keep templates professional and concise
- Test with different email clients

### Certificate Configuration
- Use a PDF viewer to find exact X,Y coordinates
- Test positioning with a single certificate first
- Adjust font sizes based on your template

### Phone Numbers
- Supports multiple formats (local, international, with spaces)
- One number per line
- Will automatically format for contact cards

## 📋 File Formats

### email_list.txt (Tab-separated)
```
John Smith	john.smith@example.com
Jane Doe	jane.doe@example.com
```

### recipients.txt (Comma-separated)
```
Name,Email,AttachmentFile
John Smith,john@example.com,john_certificate.pdf
```

### Certificate recipients.txt (Comma-separated)
```
Name,Course,Date,Achievement
John Smith,Python Workshop,2024-07-01,Outstanding
```

## 🆘 Need Help?

- Read the **SETUP_GUIDE.md** for complete instructions
- Check the main **README.md** for automation details
- Run commands with `--help` flag for options
- Test with small data sets first

Happy automating! 🎉
