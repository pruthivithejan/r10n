# Automations

This is a Python automation project with organized data folders for easy use.

## Quick Start

1. **Clone and setup:**
   ```bash
   git clone https://github.com/pruthivithejan/automations.git
   cd automations
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up data folder structure:**
   ```bash
   # Linux/Mac
   ./setup.sh
   
   # Windows
   setup.bat
   ```

5. **Configure your settings:**
   - Edit configuration files in `data/` folders with your credentials
   - Add your data (email lists, certificates, phone numbers)
   - See `examples/SETUP_GUIDE.md` for detailed instructions

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

---

### 🤖 AI Blog MDX Generator
Generates well-structured MDX blog files with AI proofreading using OpenAI API.

**Steps:**
1. **Get OpenAI API key** from [OpenAI Platform](https://platform.openai.com/api-keys)

2. **Setup blog configuration** in `data/blog_config.json`:
   ```json
   {
     "openai_api_key": "your_openai_api_key_here",
     "model": "gpt-4",
     "temperature": 0.3,
     "max_tokens": 4000,
     "output_directory": "data/blog_output",
     "author": "Your Name",
     "default_tags": ["blog", "article", "tech"]
   }
   ```

3. **Write your blog content** in a text file (e.g., `my_blog_post.txt`)

4. **Run the automation:**
   ```bash
   python src/main.py generate_blog_mdx --input "my_blog_post.txt" --title "My Amazing Blog Post"
   ```

**Example:**
```bash
python src/main.py generate_blog_mdx --input "examples/sample_blog_post.txt" --title "AI in Web Development" --author "John Doe" --tags "ai" "web-dev" "technology"
```

**Features:**
- ✅ AI-powered grammar and spelling correction
- ✅ Preserves original writing style and tone
- ✅ Automatic MDX frontmatter generation
- ✅ SEO-friendly metadata extraction
- ✅ Custom title, author, and tags support
- ✅ Structured content formatting
- ✅ Filename generation from title

---

### 🖼️ Image Optimizer
Optimizes and renames images for web use with WebP conversion and size compression.

**Steps:**
1. **Place your images** in a folder (supports JPG, PNG, GIF, BMP, TIFF, WebP)

2. **Run the automation:**
   ```bash
   python src/main.py optimize_images --input "path/to/images" --prefix "photo"
   ```

**Example:**
```bash
# Basic optimization with custom prefix
python src/main.py optimize_images --input "data/images/input" --prefix "gallery" --max-size 0.5

# Advanced optimization with custom dimensions
python src/main.py optimize_images --input "photos" --output "web-photos" --prefix "img" --quality 90 --max-width 1200 --max-height 800
```

**Features:**
- ✅ Converts images to WebP format for better compression
- ✅ Automatic file size reduction to under specified limit (default 1MB)
- ✅ Bulk renaming with custom prefix (img1.webp, img2.webp, etc.)
- ✅ Smart resizing while preserving aspect ratio
- ✅ Auto-orientation based on EXIF data
- ✅ Quality adjustment to meet size requirements
- ✅ Batch processing with detailed progress reports
- ✅ Supports all common image formats

**Configuration Options:**
- **Max file size:** Control final file size (default: 1MB)
- **Quality:** JPEG/WebP quality 10-100% (default: 85%)
- **Dimensions:** Max width/height (default: 1920x1080)
- **Prefix:** Custom filename prefix (default: "img")
- **Format:** Convert to WebP or keep original format

## Project Structure

```
examples/                    # Example configurations (safe to commit)
├── SETUP_GUIDE.md          # Complete setup instructions
├── README.md               # Examples documentation
├── emails/                 # Email automation examples
│   ├── email_config.json.example
│   ├── email_list.txt.example
│   └── email.txt.example
├── outlook/                # Outlook automation examples
├── certificates/           # Certificate generation examples
└── phone_numbers/          # Contact generation examples

data/                       # Your local data (excluded from git)
├── attachments/            # General attachments
├── certificates/           # Certificate generation assets
│   ├── config.json        # Field positions and styling
│   ├── recipients.txt     # Recipients with course/achievement data
│   ├── recipients_ex.txt  # Example recipients file
│   ├── templates/         # Blank PDF certificate templates
│   │   ├── CryptX.pdf    # Certificate template
│   │   └── Participants.pdf # Alternative template
│   └── output/            # Generated personalized certificates
├── email_config.json      # Global email configuration
├── email_config_enhanced.json # Enhanced email settings
├── email_config_template.md # Email config template/documentation
├── email_lists/           # Email list files
│   ├── icts_participants.txt # Workshop participants
│   └── icts_workshop_emails.csv # CSV format email lists
├── email_templates/       # Email template files
│   ├── icts_workshop_body.txt # Workshop email body
│   └── icts_workshop_enhanced.txt # Enhanced email template
├── emails/                # Bulk email automation assets
│   ├── email_config.json # Your Gmail/email settings
│   ├── email_list.txt    # Paste email addresses here (tab-separated name\temail)
│   ├── email.txt         # Paste email message here (supports {name} placeholder)
│   └── attachments/      # Individual certificate files for personalized sending
├── outlook/              # Outlook email automation assets
│   ├── email_config.json # Your Outlook settings
│   ├── recipients.txt    # Recipients with attachment filenames
│   ├── email.txt         # Email template with {name} placeholder
│   └── certificates/     # Individual attachment files
└── phone_numbers/        # Contact generation assets
    ├── numbers.txt       # Paste phone numbers here
    ├── sample_numbers.txt # Example phone numbers
    ├── envision_contacts.vcf # Generated contact files
    ├── numbers_contacts.vcf # Generated contact files
    └── *.vcf             # Other generated contact files

src/
├── automations/          # Automation scripts
│   ├── fill_certificates.py # Certificate generation
│   ├── generate_contacts.py # Contact VCF generation
│   ├── send_emails_outlook.py # Outlook email sending
│   ├── send_enhanced_emails.py # Enhanced email features
│   └── send_same_email.py # Bulk/personalized email sending
├── utils/                # Utility modules
│   ├── email_template_generator.py # Email template utilities
│   └── file_utils.py     # File handling utilities
└── main.py               # Main CLI interface

docs/                     # Documentation
├── email_deliverability_guide.md # Email best practices
└── PROJECT_SUMMARY.md    # Project overview

tests/                    # Test files
└── test_main.py         # Main tests

setup.sh                 # Linux/Mac setup script
setup.bat                # Windows setup script
```

## Security Notes

- **Gmail Users:** Use App Passwords instead of regular passwords
- **Outlook Users:** Enable 2FA and create App Passwords for email sending
- **Data folder is excluded from git:** The entire `data/` folder is in `.gitignore` to protect sensitive information like email addresses, certificates, and configuration files
- **Never commit** config files with real credentials to version control
- **Test first** with a small recipient list before running bulk operations

## Getting Help

- **Complete setup guide:** See `examples/SETUP_GUIDE.md` for detailed instructions
- **Example configurations:** Check the `examples/` folder for template files
- **Command help:** Run any automation without arguments to see available options:

```bash
python src/main.py generate_contacts --help
python src/main.py send_bulk_emails --help
python src/main.py send_outlook_emails --help
python src/main.py fill_certificates --help
python src/main.py generate_blog_mdx --help
python src/main.py optimize_images --help
```

- **Quick setup:** Run `./setup.sh` (Linux/Mac) or `setup.bat` (Windows) to create the data folder structure
