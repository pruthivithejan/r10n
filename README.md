# Automations

This is a basic Python project with a virtual environment setup.

## Setup

1. The virtual environment is already created in the `.venv` directory
2. To activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

- `src/`: Source code directory
  - `automations/`: Individual automation scripts
  - `utils/`: Shared utility functions
- `data/`: Configuration and data files
  - `email_config_enhanced.json`: Your email configuration (create from template)
  - `email_lists/`: Text files with email addresses
  - `email_templates/`: Email content templates
  - `phone_numbers/`: Text files with phone numbers for contact generation
  - `attachments/`: Files to attach to emails
  - Generated VCF files and outputs are saved here
- `docs/`: Documentation and guides
- `tests/`: Test files directory
- `requirements.txt`: Project dependencies

## Available Automations

1. **Contact Card Generator** - Convert phone numbers to VCF contact files
2. **Enhanced Bulk Email Sender** - Send emails with improved deliverability

## Key Features

- **Email Deliverability**: Built-in features to avoid spam folders
- **Rate Limiting**: Controlled sending to protect sender reputation
- **Professional Headers**: Proper email formatting and headers
- **Organization Footer**: Automatic footer with contact info and unsubscribe
- **Batch Processing**: Send emails in controlled batches
- **Security**: Template-based configuration to protect credentials

## Running Automations

This project contains various automation scripts that can be run from the command line. To see all available automations:
```bash
python src/main.py
```

### Contact Card Generator
Converts a list of phone numbers into a VCF file that can be imported into your contacts.

1. **Prepare Phone Numbers:**
   - Create a text file with phone numbers (one per line) in `data/phone_numbers/`
   - Supported formats: 0712345678, +94712345678, 071 234 5678, etc.

2. **Run the command:**
```bash
python src/main.py generate_contacts <input_file> [options]
```

Options:
- `--output`, `-o`: Output VCF file name (default: auto-generated from input filename)
- `--prefix`, `-p`: Prefix for contact names (default: Contact)

Examples:
```bash
# Basic usage - creates data/my_numbers_contacts.vcf
python src/main.py generate_contacts data/phone_numbers/my_numbers.txt

# Custom output filename and prefix
python src/main.py generate_contacts data/phone_numbers/friends.txt --output family_contacts.vcf --prefix "Friend"
```

**Features:**
- Automatically cleans and validates phone numbers
- Removes duplicates
- Converts to Sri Lankan (+94) format
- Outputs VCF files to `data/` directory for organization
- Reports statistics (total, valid, duplicates, invalid)

### Bulk Email Sender (Enhanced Deliverability)
Sends the same email to multiple recipients with enhanced deliverability features to avoid spam folders.

1. **Setup Email Configuration:**
   - Copy the template from `data/email_config_template.md`
   - Create `data/email_config_enhanced.json` with your email settings:
   ```json
   {
     "smtp_server": "smtp.gmail.com",
     "smtp_port": 587,
     "email": "your_email@gmail.com",
     "password": "your_app_password",
     "use_tls": true,
     "sender_name": "Your Name",
     "organization": "Your Organization",
     "rate_limit_delay": 3,
     "batch_size": 5,
     "batch_delay": 60
   }
   ```

2. **Prepare Email List:**
   - Create a text file with email addresses (one per line):
   ```
   user1@example.com
   user2@example.com
   user3@example.com
   ```

3. **Create Email Template:**
   - Write your email content in a text file in `data/email_templates/`

4. **Run the automation:**
```bash
python src/main.py send_bulk_emails <emails_file> "<subject>" <body_file> [options]
```

Options:
- `--config`, `-c`: Email configuration file (default: data/email_config_enhanced.json)

Example:
```bash
python src/main.py send_bulk_emails data/email_lists/participants.txt "Workshop Invitation" data/email_templates/workshop_invite.txt
```

**Deliverability Features:**
- Rate limiting to avoid spam detection
- Professional email headers
- Unsubscribe links
- Organization footer
- Batch processing
- Proper email formatting

**Important Security Notes:**
- For Gmail, use App Passwords instead of your regular password
- Never commit your email configuration file with real credentials to version control
- See `docs/email_deliverability_guide.md` for detailed best practices

## Running Tests

To run tests:
```bash
pytest tests/
```
