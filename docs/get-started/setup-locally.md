---
icon: lucide/laptop
---

# Setup Locally

Clone, install, and run r10n for repeated use or development. This makes all automation features available persistently on your machine.

---

## Prerequisites

You need [uv](https://docs.astral.sh/uv/) installed. If you don't have it:

=== "macOS / Linux"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

=== "Homebrew"

    ```bash
    brew install uv
    ```

Verify installation:

```bash
uv --version
```

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
```

### Step 2: Install Dependencies

```bash
uv sync
```

This creates a virtual environment and installs all dependencies automatically.

### Step 3: Verify Installation

```bash
uv run r10n --help
```

You should see:

```
Usage: r10n [OPTIONS] COMMAND [ARGS]...

  r10n - Automate repetitive data and workflow tasks

Options:
  --help  Show this message and exit.

Commands:
  certificates  Generate personalized PDF certificates
  colors        Convert CSS colors to oklch() format
  contacts      Generate VCF contact cards from phone numbers
  email         Send bulk personalized emails
  images        Optimize and convert images to WebP
```

---

## Project Structure

After installation, your directory looks like this:

```
r10n/
├── src/
│   ├── cli.py                    # Main CLI entry point
│   └── automations/              # Automation modules
├── local/                        # Your working directory (gitignored)
│   ├── inputs/                   # Place your input files here
│   │   ├── contacts/
│   │   ├── certificates/
│   │   ├── images/
│   │   └── email/
│   ├── outputs/                  # Generated files appear here
│   │   ├── contacts/
│   │   ├── certificates/
│   │   ├── images/
│   │   └── email/
│   └── configs/                  # Configuration files
├── configs/                      # Default config templates
├── docs/                         # Documentation
└── tests/                        # Test suite
```

---

## Running Automations

### Interactive Mode

Run any command without arguments for step-by-step prompts:

```bash
uv run r10n contacts
```

### Command Line Mode

Pass all options directly for scripting:

```bash
uv run r10n contacts \
  --input local/inputs/contacts/numbers.txt \
  --prefix Customer \
  --output local/outputs/contacts/customers.vcf
```

---

## Setting Up Your Workspace

### Create the Local Folder Structure

```bash
mkdir -p local/inputs/contacts
mkdir -p local/inputs/certificates
mkdir -p local/inputs/images
mkdir -p local/inputs/email
mkdir -p local/outputs/contacts
mkdir -p local/outputs/certificates
mkdir -p local/outputs/images
mkdir -p local/outputs/email
mkdir -p local/configs
```

Or run the setup script (if available):

```bash
uv run python scripts/setup.py
```

### Example: Contacts Workflow

1. Create your input file:

   ```bash
   cat > local/inputs/contacts/numbers.txt << 'EOF'
   # Customer phone numbers
   0771234567
   0781234567
   +94791234567
   EOF
   ```

2. Run the automation:

   ```bash
   uv run r10n contacts \
     --input local/inputs/contacts/numbers.txt \
     --prefix Customer \
     --output local/outputs/contacts/customers.vcf
   ```

3. Check the output:

   ```bash
   ls -la local/outputs/contacts/
   ```

### Example: Certificates Workflow

1. Place your template PDF in `local/inputs/certificates/`

2. Create your data file:

   ```bash
   cat > local/inputs/certificates/participants.csv << 'EOF'
   name,course,date
   John Doe,Web Development,2025-01-15
   Jane Smith,Data Science,2025-01-15
   EOF
   ```

3. Run the automation:

   ```bash
   uv run r10n certificates \
     --template local/inputs/certificates/template.pdf \
     --data local/inputs/certificates/participants.csv \
     --output-dir local/outputs/certificates/
   ```

### Example: Images Workflow

1. Copy images to process:

   ```bash
   cp ~/Desktop/photos/* local/inputs/images/
   ```

2. Run the optimization:

   ```bash
   uv run r10n images \
     --input local/inputs/images/ \
     --output local/outputs/images/ \
     --quality 85
   ```

---

## Configuration Files

Some automations support configuration files for default settings.

### Email Configuration

Create `local/configs/email.json`:

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "sender_email": "your-email@gmail.com"
}
```

### Images Configuration

Create `local/configs/images.json`:

```json
{
  "default_quality": 85,
  "default_format": "webp",
  "max_width": 1920,
  "max_height": 1080
}
```

---

## Updating r10n

Pull the latest changes:

```bash
cd r10n
git pull
uv sync
```

---

## Development Setup

If you want to contribute or modify r10n:

### Run Tests

```bash
uv run pytest
```

### Run Linting

```bash
uv run ruff check src tests
```

### Format Code

```bash
uv run black src tests
```

### Pre-commit Hooks

The project uses [lefthook](https://github.com/evilmartians/lefthook) for git hooks:

```bash
# Install lefthook (if not already installed)
brew install lefthook  # or: npm install -g lefthook

# Enable hooks
lefthook install
```

Now tests and linting run automatically before each commit.

---

## Troubleshooting

### "Command not found: uv"

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal or run:

```bash
source ~/.bashrc  # or ~/.zshrc
```

### "ModuleNotFoundError"

Run `uv sync` to install dependencies:

```bash
uv sync
```

### "Permission denied" on outputs

Make sure the output directory exists and is writable:

```bash
mkdir -p local/outputs/contacts
chmod 755 local/outputs/contacts
```

### Tests Failing

Run tests with verbose output to see details:

```bash
uv run pytest -v
```

---

## Next Steps

- [Run on Terminal](run-on-terminal.md) — For quick one-off tasks without local setup
- [Automations](../automations/index.md) — Detailed guides for each automation
- [GitHub Issues](https://github.com/pruthivithejan/r10n/issues) — Get help or report bugs
- [Contribute](https://github.com/pruthivithejan/r10n/blob/main/AGENTS.md) — Development guidelines
