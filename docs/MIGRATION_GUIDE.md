# Migration Guide to Automation Toolkit 2.0

## 🚀 What's New

The Automation Toolkit has been completely restructured for better usability, faster execution, and modern Python tooling:

### Key Improvements
- **UV Package Manager**: 10-100x faster than pip
- **Interactive CLI**: Beautiful terminal UI with guided execution
- **One-Command Setup**: `make setup` initializes everything
- **Task Runner**: Makefile provides npm-like script commands
- **Clean Separation**: Code vs. configuration vs. user data
- **Ruff Linting**: Lightning-fast Python linting and formatting
- **Rich Terminal UI**: Professional command-line interface

## 📁 New Project Structure

```
automation/
├── pyproject.toml          # Project configuration (like package.json)
├── Makefile               # Task runner with simple commands
├── .env.example           # Environment template
│
├── src/                   # Source code
│   ├── cli.py            # New interactive CLI
│   └── automations/      # Your existing automations
│
├── configs/               # Default configurations (in git)
├── templates/             # File templates (in git)
├── workspace/             # User workspace (gitignored)
│   ├── .env              # Your credentials
│   ├── configs/          # Your custom configs
│   ├── inputs/           # Input files
│   └── outputs/          # Generated outputs
│
└── scripts/               # Utility scripts
    └── setup.py          # Smart setup wizard
```

## 🔄 Migration Steps

### Step 1: Initial Setup

```bash
# 1. Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Run the setup
make setup

# Or manually:
uv venv
uv pip install -e .
uv run python scripts/setup.py --init
```

### Step 2: Migrate Your Data

Move your existing data to the new workspace structure:

```bash
# Move email data
cp data/emails/email_list.csv workspace/inputs/email/recipients.csv
cp data/emails/email.txt workspace/inputs/email/email_template.txt
cp data/emails/email_config.json workspace/configs/email.json

# Move certificate data
cp data/certificates/recipients.txt workspace/inputs/certificates/
cp data/certificates/templates/*.pdf templates/certificates/
cp data/certificates/config.json workspace/configs/certificates.json

# Move contact data
cp data/phone_numbers/numbers.txt workspace/inputs/contacts/

# Move any existing outputs
cp -r data/certificates/output/* workspace/outputs/certificates/
```

### Step 3: Update Environment Variables

Edit `workspace/.env` with your credentials:

```bash
# Open the file
nano workspace/.env  # or use your preferred editor

# Update these values:
EMAIL_ADDRESS=your-actual-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password
OPENAI_API_KEY=your-actual-api-key
```

### Step 4: Test the New Setup

Run a simple test to ensure everything works:

```bash
# Check status
make version
uv run automate status

# Try contact generation (simplest test)
make contacts

# Or run directly
uv run automate contacts --interactive
```

## 🎯 Quick Command Reference

### Old Way vs. New Way

| Task | Old Command | New Command |
|------|------------|-------------|
| Setup | `./setup.sh` | `make setup` |
| Generate Contacts | `python3 src/main.py generate_contacts --input data/phone_numbers/numbers.txt` | `make contacts` |
| Send Emails | `python3 src/main.py send_bulk_emails --emails data/emails/email_list.csv` | `make email` |
| Generate Certificates | `python3 src/main.py fill_certificates --recipients data/certificates/recipients.txt` | `make certs` |
| Optimize Images | `python3 src/main.py optimize_images --input path/to/images` | `make images` |
| Generate Blog | `python3 src/main.py generate_blog_mdx --input blog.txt` | `make blog` |

### New Interactive Mode

All commands now support an interactive mode that guides you through the process:

```bash
# Interactive mode (recommended for beginners)
uv run automate email --interactive
uv run automate certificates --interactive

# Direct mode (for automation/scripts)
uv run automate contacts \
  --input workspace/inputs/contacts/numbers.txt \
  --output workspace/outputs/contacts/contacts.vcf \
  --prefix "Customer"
```

## 🔧 Configuration Management

### Configuration Hierarchy

1. **Default Configs** (`configs/*.default.json`): Template configurations in git
2. **User Configs** (`workspace/configs/*.json`): Your custom settings (gitignored)
3. **Environment Variables** (`workspace/.env`): Sensitive credentials (gitignored)
4. **Command-line Arguments**: Override any setting at runtime

### Example: Email Configuration

```json
// workspace/configs/email.json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "rate_limit": {
    "delay_seconds": 3,
    "batch_size": 5
  }
}
```

## 📝 Development Workflow

### Adding New Automations

1. Create module in `src/automations/`
2. Add command to `src/cli.py`
3. Add Make target in `Makefile`
4. Create default config in `configs/`
5. Update documentation

### Running Tests

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Run linting
make lint
```

## 🆘 Troubleshooting

### Common Issues

**Issue**: `make: command not found`
```bash
# On macOS
brew install make

# On Linux
sudo apt-get install make  # Debian/Ubuntu
sudo yum install make       # RedHat/CentOS
```

**Issue**: UV not installed
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Issue**: Import errors
```bash
# Reinstall in development mode
uv pip install -e .
```

**Issue**: Configuration not found
```bash
# Run setup again
uv run python scripts/setup.py --init
```

## 🎉 Benefits of the New Structure

1. **Faster Execution**: UV installs dependencies in seconds, not minutes
2. **Better Organization**: Clear separation of code, config, and data
3. **Easier to Use**: Interactive mode guides you through each automation
4. **Professional CLI**: Rich terminal UI with colors, tables, and progress bars
5. **Git-Friendly**: Only code and templates in version control
6. **Portable**: Easy to clone and set up on any machine
7. **Maintainable**: Modern Python packaging standards

## 📚 Additional Resources

- **Make Help**: `make help` - Shows all available commands
- **CLI Help**: `uv run automate --help` - Detailed CLI documentation
- **Status Check**: `uv run automate status` - Check your setup
- **Interactive Mode**: Add `--interactive` to any command for guided execution

## 💡 Tips

1. Use `make` commands for common tasks - they're shorter and easier
2. Use interactive mode when you're unsure about parameters
3. Keep your workspace/.env file updated with current credentials
4. Review configs in workspace/configs/ before running automations
5. Check workspace/outputs/ for generated files

## 🔄 Rollback Plan

If you need to revert to the old structure:

1. Your original `data/` directory is untouched
2. The old `src/main.py` still works with the old structure
3. You can run `pip install -r requirements.txt` to use pip again

However, we strongly recommend adopting the new structure for its numerous benefits!

---

For questions or issues, please refer to the README.md or create an issue on GitHub.
