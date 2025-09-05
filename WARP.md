# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

This is a Python automation framework for bulk operations including email sending, certificate generation, contact management, blog MDX generation, and image optimization. The project uses a modular architecture with separate automation scripts that can be invoked through a central CLI interface.

## Core Commands

### Setting up the development environment
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize data folder structure (Linux/Mac)
./setup.sh

# Initialize data folder structure (Windows)
setup.bat
```

### Running automations
```bash
# Generate VCF contact cards from phone numbers
python3 src/main.py generate_contacts --prefix "Contact Name"

# Send bulk emails with same content
python3 src/main.py send_bulk_emails --subject "Email Subject"

# Send personalized Outlook emails with individual attachments
python3 src/main.py send_outlook_emails

# Generate personalized PDF certificates from template
python3 src/main.py fill_certificates

# Generate MDX blog files with AI proofreading
python3 src/main.py generate_blog_mdx --input "blog_post.txt" --title "Blog Title"

# Optimize and convert images to WebP
python3 src/main.py optimize_images --input "path/to/images" --prefix "img"
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_main.py
```

### Getting help for any command
```bash
python3 src/main.py <automation_name> --help
```

## Architecture & Design Patterns

### Central CLI Router Pattern
The `src/main.py` file acts as a central command router that:
- Defines argument parsers for each automation using `argparse` subparsers
- Dynamically imports the needed automation module based on the selected command
- Provides a consistent interface for all automations with standardized error handling and result reporting

### Data Isolation Architecture
The project enforces strict separation between code and data:
- All user data lives in the `data/` directory (excluded from git via .gitignore)
- Example configurations are stored in `examples/` (safe to commit)
- Each automation has its own subdirectory under `data/` for isolation
- Configuration files use JSON format for easy parsing and modification

### Automation Module Pattern
Each automation in `src/automations/` follows a consistent pattern:
- Main entry function accepts file paths as parameters
- Returns a standardized results dictionary with success/failure counts
- Handles its own validation and error reporting
- Can be imported and used programmatically or via CLI

### Key Cross-File Dependencies

1. **Email Sending Flow** (`send_same_email.py` + `send_emails_outlook.py`):
   - Both read email configuration from JSON files
   - Support template variables like `{name}` for personalization
   - Handle attachment files from designated directories
   - Implement rate limiting and batch processing for deliverability

2. **Certificate Generation Pipeline** (`fill_certificates.py`):
   - Reads PDF template from `data/certificates/templates/`
   - Uses coordinate-based positioning configured in `config.json`
   - Supports multiple data fields (name, course, date, achievement)
   - Generates output files with recipient names as filenames

3. **Contact Management** (`generate_contacts.py`):
   - Validates and normalizes Sri Lankan phone numbers
   - Removes duplicates and invalid entries
   - Generates VCF 3.0 format compatible with most devices
   - Automatically prefixes numbers with country code (+94)

4. **Blog MDX Generation** (`generate_blog_mdx.py`):
   - Integrates with OpenAI API for content proofreading
   - Generates MDX frontmatter with SEO metadata
   - Preserves original writing style while fixing errors
   - Creates web-ready filenames from titles

5. **Image Optimization** (`optimize_images.py`):
   - Converts images to WebP format for better compression
   - Implements smart resizing with aspect ratio preservation
   - Adjusts quality dynamically to meet file size targets
   - Supports batch renaming with sequential numbering

### Configuration Management
The project uses a layered configuration approach:
- Global configs in `data/email_config.json` for email settings
- Module-specific configs (e.g., `data/certificates/config.json`)
- Command-line arguments override configuration file values
- Template files provide safe defaults for new users

## Important Project Context

### Security Considerations
- The `data/` directory contains sensitive information (emails, API keys, personal data) and is excluded from version control
- Email automations require app-specific passwords, not regular account passwords
- All credentials should be stored in JSON configuration files, never hardcoded

### Email Deliverability Features
The email automation includes sophisticated anti-spam measures:
- Rate limiting with 3-second delays between emails
- Batch processing in groups of 5 with 60-second pauses
- Professional headers (Message-ID, Date, Reply-To, List-Unsubscribe)
- Organization footer with contact information

### File Structure Conventions
- Input data files typically use `.txt` format with specific delimiters
- Email lists can be tab-separated (name\temail) or comma-separated CSV
- Certificate recipients use comma-separated format: name,course,date,achievement
- Generated files are placed in designated output directories

### Sri Lankan Phone Number Format
The contact generator specifically handles Sri Lankan numbers:
- Accepts formats: 0712345678, +94712345678, 071 234 5678
- Automatically adds +94 country code
- Validates for exactly 9 digits after country code

### Dependencies
Key Python packages used:
- `PyPDF2` and `reportlab` for PDF manipulation
- `openai` for AI-powered content processing
- `Pillow` for image optimization
- `pandas` for data handling (CSV/Excel)
- Standard library modules for email (smtplib, email)

## Common Development Tasks

### Adding a new automation
1. Create new module in `src/automations/`
2. Define main entry function that accepts file paths
3. Add argument parser in `src/main.py`
4. Create example files in `examples/`
5. Update README.md with usage instructions

### Debugging email sending issues
- Check app password configuration (not regular password)
- Verify SMTP settings match provider (Gmail: 587, Outlook: 587)
- Test with single recipient first
- Check spam folder for delivered emails
- Review rate limiting settings if emails are blocked

### Modifying certificate templates
- Use PDF viewer to identify X,Y coordinates for text placement
- Update `data/certificates/config.json` with new positions
- Test with single recipient before bulk generation
- Adjust font size and color in configuration

## Repository Links
- GitHub: https://github.com/pruthivithejan/automations.git
- Main documentation: README.md
- Setup guide: examples/SETUP_GUIDE.md
- Email best practices: docs/email_deliverability_guide.md
