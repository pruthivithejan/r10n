---
icon: material/folder-cog
---

# Setup Locally

Set up r10n locally for repeated use, custom configurations, and working with templates.

## Prerequisites

You need Python 3.10+ and uv installed on your system.

### Install uv

=== "macOS / Linux"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

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

This creates a virtual environment and installs all dependencies.

### Step 3: Initialize Local Folder

```bash
uv run r10n init
```

This creates the folder structure:

```
local/
├── configs/          # Configuration files
├── inputs/
│   ├── contacts/     # Phone number files
│   ├── certificates/ # Recipients and templates
│   ├── images/       # Images to optimize
│   └── email/        # Email templates and recipients
└── outputs/
    ├── contacts/     # Generated VCF files
    ├── certificates/ # Generated PDF certificates
    └── images/       # Optimized images
```

### Step 4: Verify Installation

```bash
uv run r10n status
```

You should see:

```
┌──────────────────────┬─────────┐
│ Component            │ Status  │
├──────────────────────┼─────────┤
│ Local folder         │ Created │
│   local/configs/     │ Created │
│   local/inputs/      │ Created │
│   local/outputs/     │ Created │
│ Configuration files  │ 0 found │
│ Environment file     │ Missing │
└──────────────────────┴─────────┘
```

## Running Automations

Use `uv run r10n` to run any automation:

```bash
uv run r10n contacts
uv run r10n certificates
uv run r10n images
uv run r10n email
```

## Contacts

Generate VCF contact cards from phone numbers.

### Step 1: Create Input File

Create `local/inputs/contacts/numbers.txt`:

```text
# Phone numbers (comments start with #)
0771234567
0781234567
+94791234567
```

### Step 2: Run Automation

```bash
uv run r10n contacts
```

Follow the prompts or use command-line options:

```bash
uv run r10n contacts \
  --input local/inputs/contacts/numbers.txt \
  --prefix Customer \
  --output local/outputs/contacts/customers.vcf
```

### Output

VCF file is saved to `local/outputs/contacts/`.

## Certificates

Generate PDF certificates from a template.

### Step 1: Create Configuration

The first time you run the command, it offers to create an example config:

```bash
uv run r10n certificates
```

Or create `local/configs/certificates.json` manually:

```json
{
  "template_pdf": "local/inputs/certificates/template.pdf",
  "output_directory": "local/outputs/certificates",
  "font_family": "Helvetica",
  "fields": {
    "name": {
      "x": 300,
      "y": 400,
      "font_size": 36,
      "font_weight": "bold",
      "alignment": "center",
      "color": [0, 0, 0]
    },
    "position": {
      "x": 300,
      "y": 350,
      "font_size": 24,
      "font_weight": "normal",
      "alignment": "center",
      "color": [50, 50, 50]
    }
  }
}
```

### Step 2: Add Template PDF

Place your PDF template in `local/inputs/certificates/template.pdf`.

### Step 3: Create Recipients File

Create `local/inputs/certificates/recipients.txt`:

=== "TXT Format"

    ```text
    John Doe	Team Lead
    Jane Smith	Developer
    ```

=== "CSV Format"

    ```csv
    name,position
    John Doe,Team Lead
    Jane Smith,Developer
    ```

### Step 4: Run Automation

```bash
uv run r10n certificates
```

### Output

PDF certificates are saved to `local/outputs/certificates/`.

## Images

Optimize and convert images to WebP format.

### Step 1: Add Images

Place images in `local/inputs/images/`.

Supported formats: JPEG, PNG, GIF, BMP, TIFF, WebP.

### Step 2: Run Automation

```bash
uv run r10n images
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| Quality | Compression quality (1-100) | 85 |
| Max size | Maximum file size in MB | 1.0 |
| Max width | Maximum image width | 1920 |
| Max height | Maximum image height | 1080 |
| Preserve names | Keep original filenames | true |

### Output

Optimized WebP images are saved to `local/outputs/images/`.

## Email

Send bulk personalized emails with certificate attachments.

### Step 1: Create Configuration

Create `local/configs/email.json`:

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "email": "your-email@gmail.com",
  "password": "your-app-password",
  "subject": "Your Certificate",
  "use_tls": true
}
```

!!! warning "Gmail Users"
    Use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Step 2: Create Recipients File

Create `local/inputs/email/recipients.csv`:

```csv
Name,Email
John Doe,john@example.com
Jane Smith,jane@example.com
```

### Step 3: Create Email Template

Create `local/inputs/email/template.txt`:

```text
Dear {name},

Congratulations! Please find your certificate attached.

Best regards,
The Team
```

### Step 4: Generate Certificates First

Ensure you have generated certificates in `local/outputs/certificates/`.

### Step 5: Run Automation

```bash
uv run r10n email
```

## Environment Variables

Create `local/.env` for sensitive configuration:

```bash
# SMTP credentials (alternative to config file)
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# OpenAI (if using AI features)
OPENAI_API_KEY=sk-your-key
```

## Folder Structure

After setup, your project looks like:

```
r10n/
├── local/                  # Your data (gitignored)
│   ├── .env               # Environment variables
│   ├── configs/           # Configuration files
│   │   ├── certificates.json
│   │   └── email.json
│   ├── inputs/            # Input files
│   │   ├── contacts/
│   │   ├── certificates/
│   │   ├── images/
│   │   └── email/
│   └── outputs/           # Generated files
│       ├── contacts/
│       ├── certificates/
│       └── images/
├── src/                   # Source code
├── docs/                  # Documentation
├── tests/                 # Tests
└── pyproject.toml         # Project configuration
```

## Tips

### Create Alias

For convenience, create a shell alias:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias r10n='uv run r10n'
```

Then use:

```bash
r10n contacts
```

### Keep Config Templates

After customizing configs, back them up:

```bash
cp local/configs/certificates.json local/configs/certificates.backup.json
```

### Gitignore Local Folder

The `local/` folder is already gitignored to protect your data:

```gitignore
# In .gitignore
local/
```

## Troubleshooting

### Command Not Found

Make sure you're in the project directory:

```bash
cd path/to/r10n
uv run r10n --help
```

### Dependencies Missing

Reinstall dependencies:

```bash
uv sync --force-reinstall
```

### Permission Denied

On macOS/Linux, ensure uv is in your PATH:

```bash
source ~/.bashrc  # or ~/.zshrc
```
