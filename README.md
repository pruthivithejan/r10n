# Automations by Pruthvi Thejan

> 🚀 A modern, versatile automation toolkit for bulk operations - emails, certificates, contacts, images, and more. Built with Python, enhanced with UV for blazing-fast performance, and featuring a beautiful CLI interface.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UV](https://img.shields.io/badge/UV-Package%20Manager-green.svg)](https://github.com/astral-sh/uv)
[![Rich CLI](https://img.shields.io/badge/CLI-Rich%20Interface-purple.svg)](https://github.com/Textualize/rich)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

- **📧 Bulk Email Automation** - Send personalized emails with templates and attachments
- **📜 Certificate Generation** - Create PDF certificates from templates with custom data
- **📱 Contact Management** - Generate VCF contact cards from phone numbers
- **🖼️ Image Optimization** - Batch convert and optimize images to WebP format
- **✍️ Blog MDX Generation** - Create SEO-optimized blog posts with AI proofreading
- **⚡ Lightning Fast** - 10-100x faster than traditional pip with UV package manager
- **🎨 Beautiful CLI** - Interactive mode with rich terminal UI
- **🔧 One-Command Setup** - Get started in seconds

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- macOS, Linux, or Windows
- UV package manager (installed automatically)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/pruthivithejan/automations.git
cd automations

# 2. Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Run the one-command setup
make setup
```

That's it! The setup will:
- Create a virtual environment
- Install all dependencies (super fast with UV)
- Set up your workspace structure
- Create configuration templates
- Generate example files

## 📖 Step-by-Step Usage Guide

### Step 1: Configure Your Environment

After setup, edit your credentials:

```bash
# Edit the environment file
nano workspace/.env

# Update these values:
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password  # Use app-specific password
OPENAI_API_KEY=sk-your-api-key    # For blog generation (optional)
```

### Step 2: Check Your Setup

Verify everything is configured correctly:

```bash
# Check status
uv run python -m src.cli status

# See all available commands
make help
```

### Step 3: Run Your First Automation

Let's start with the simplest - generating contacts:

```bash
# Run interactively (recommended for beginners)
make contacts
```

The interactive mode will guide you through:
1. Selecting input file
2. Setting contact prefix
3. Choosing output location
4. Confirming generation

## 🎯 Available Automations

### 📧 Email Automation

Send bulk emails with personalization:

```bash
# Interactive mode
make email

# Or direct command
uv run python -m src.cli email \
  --recipients workspace/inputs/email/recipients.csv \
  --body workspace/inputs/email/template.txt \
  --config workspace/configs/email.json
```

**Input Format** (`recipients.csv`):
```csv
name,email
John Doe,john@example.com
Jane Smith,jane@example.com
```

**Template** (`template.txt`):
```
Dear {name},

Your personalized message here.

Best regards,
{sender_name}
```

### 📜 Certificate Generation

Create personalized PDF certificates:

```bash
# Interactive mode
make certs

# Direct command
uv run python -m src.cli certificates \
  --recipients workspace/inputs/certificates/recipients.txt \
  --template templates/certificates/template.pdf
```

**Recipients Format** (`recipients.txt`):
```
John Doe,Python Mastery,2024-01-15,Excellence
Jane Smith,Data Science,2024-01-16,Outstanding
```

### 📱 Contact Generation

Convert phone numbers to VCF contact cards:

```bash
# Interactive mode
make contacts

# Direct command
uv run python -m src.cli contacts \
  --input workspace/inputs/contacts/numbers.txt \
  --prefix "Customer"
```

**Input Format** (`numbers.txt`):
```
0771234567
0712345678
+94771234567
```

### 🖼️ Image Optimization

Optimize and convert images to WebP:

```bash
# Interactive mode
make images

# Direct command
uv run python -m src.cli images \
  --input workspace/inputs/images \
  --quality 85 \
  --max-size 1.0
```

### ✍️ Blog MDX Generation

Generate SEO-optimized blog posts:

```bash
# Interactive mode
make blog

# Direct command
uv run python -m src.cli blog \
  --input workspace/inputs/blog/post.txt \
  --title "My Blog Title" \
  --author "Your Name"
```

## 📁 Project Structure

```
automations/
├── src/                    # Source code
│   ├── cli.py             # Enhanced CLI interface
│   └── automations/       # Core automation modules
├── workspace/             # Your data (gitignored)
│   ├── .env              # Your credentials
│   ├── configs/          # Your configurations
│   ├── inputs/           # Input files
│   └── outputs/          # Generated outputs
├── templates/             # Your templates (gitignored)
│   ├── email/            # Email templates
│   └── certificates/     # PDF templates
├── configs/               # Default configurations
├── scripts/               # Utility scripts
├── Makefile              # Task runner
└── pyproject.toml        # Project configuration
```

## 🛠️ Configuration

### Email Configuration (`workspace/configs/email.json`)

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "your-email@gmail.com",
  "rate_limit": {
    "delay_seconds": 3,
    "batch_size": 5
  }
}
```

### Certificate Configuration (`workspace/configs/certificates.json`)

```json
{
  "template_path": "templates/certificates/template.pdf",
  "fields": {
    "name": {"x": 300, "y": 400, "font_size": 30},
    "course": {"x": 300, "y": 350, "font_size": 20}
  }
}
```

## 🔄 Migrating from Old Structure

If you have data in the old structure:

```bash
# Preview what will be migrated
make migrate-dry

# Run migration
make migrate
```

## 🎮 All Available Commands

```bash
# Core Commands
make help          # Show all commands
make setup         # Initial setup
make clean         # Clean temporary files

# Automations
make email         # Email automation
make certs         # Certificate generation
make contacts      # Contact generation
make images        # Image optimization
make blog          # Blog generation

# Utilities
make migrate       # Migrate old data
make lint          # Run code linting
make test          # Run tests
make update        # Update dependencies
```

## 💡 Tips & Tricks

### 1. Use Interactive Mode
Perfect for beginners - guides you through each step:
```bash
make contacts  # Will prompt for all needed information
```

### 2. Batch Processing
For automation and scripts, use direct commands:
```bash
# Process all at once
make run-contacts-batch
make run-email-bulk
```

### 3. Custom Templates
Add your templates to `templates/` folder:
- They're automatically gitignored for privacy
- Reference them in your configs

### 4. Testing
Always test with small datasets first:
```bash
# Create a test file with 2-3 entries
echo "0771234567" > workspace/inputs/contacts/test.txt
make contacts
```

## 🔒 Security Notes

- **Never commit** `workspace/` or `templates/` folders (already gitignored)
- Use **app-specific passwords** for email automation
- Keep your `.env` file secure
- Test with small batches before bulk operations

## 📚 Documentation

- [Quick Start Guide](QUICK_START.md) - Get up and running quickly
- [Migration Guide](MIGRATION_GUIDE.md) - Migrate from old structure
- [Cleanup Guide](CLEANUP_GUIDE.md) - Remove old files safely
- [WARP Integration](WARP.md) - For Warp terminal users

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Pruthvi Thejan**
- GitHub: [@pruthivithejan](https://github.com/pruthivithejan)

## 🙏 Acknowledgments

- Built with [UV](https://github.com/astral-sh/uv) for blazing-fast package management
- CLI powered by [Click](https://click.palletsprojects.com/) and [Rich](https://github.com/Textualize/rich)
- PDF manipulation with [PyPDF2](https://pypdf2.readthedocs.io/) and [ReportLab](https://www.reportlab.com/)

---

<p align="center">
  Made with ❤️ by Pruthvi Thejan
</p>

<p align="center">
  ⭐ Star this repository if you find it helpful!
</p>
