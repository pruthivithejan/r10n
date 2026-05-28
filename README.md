# r10n

**Routine Automation** - Automate repetitive tasks with a beautiful CLI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-Package%20Manager-green.svg)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **Contacts** - Generate VCF contact cards from phone numbers
- **Fill PDFs** - Fill PDF templates with data from CSV/TXT files
- **Images** - Optimize and convert images to WebP format
- **Email** - Send bulk personalized emails with attachments
- **Persistent terminal UI** - Run `r10n` once, choose automations from the home screen, and stay in the session until Ctrl+C
- **Interactive commands** - Step-by-step prompts guide you through each automation
- **Colors** - Convert CSS color codes (hex, hsl/hsla) to `oklch()` for perceptual color consistency
- **Fast** - Powered by [uv](https://docs.astral.sh/uv/) for lightning-fast dependency management

## Quick Start

### Run Instantly (No Installation)

Use `uvx` to run `r10n` without cloning the repository. This installs only the runtime dependencies needed to execute the commands.

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
```

### Setup Locally

For local development or persistent use, clone the repository. `uv sync` installs all dependencies, including local contributor tooling like `zensical` for documentation and `pytest` for testing.

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n --help
```

### Install Binary (curl)

Install a prebuilt CLI app (no Python or uv required):

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh
```

Safer alternative:

```bash
curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh -o install.sh
sh install.sh
```

Update later with:

```bash
r10n upgrade
```

If an older installed binary fails during upgrade with a TLS certificate error, reinstall once with the same curl installer, then run `r10n --version`.

Launch the installed terminal UI:

```bash
r10n
```

## Usage

Each command is interactive - just run it and follow the prompts:

```bash
# Open the persistent home UI
r10n

# Generate contact cards
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts

# Fill PDFs
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n fill-pdfs

# Optimize images
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images

# Send emails
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email
```

## Example

```
$ uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts

  ██████╗  ██╗ ██████╗ ███╗   ██╗
  ██╔══██╗███║██╔═══██╗████╗  ██║
  ██████╔╝╚██║██║   ██║██╔██╗ ██║
  ██╔══██╗ ██║██║   ██║██║╚██╗██║
  ██║  ██║ ██║╚██████╔╝██║ ╚████║
  ╚═╝  ╚═╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝

Step 1/3: Select input file
  Enter path to file with phone numbers: numbers.txt
Step 2/3: Set contact name prefix
  Enter prefix for contact names: Customer
Step 3/3: Set output file
  Enter output VCF file path: contacts.vcf

Proceed with contact generation? [y/n]: y

Done!
┌─────────────────────┬──────────────┐
│ Total numbers       │ 50           │
│ Valid contacts      │ 48           │
│ Duplicates removed  │ 1            │
│ Invalid numbers     │ 1            │
│ Output file         │ contacts.vcf │
└─────────────────────┴──────────────┘
```

## Documentation

Full documentation is available at [pruthivithejan.github.io/r10n](https://pruthivithejan.github.io/r10n/)

- [Get Started](https://pruthivithejan.github.io/r10n/get-started/)
- [Run on Terminal](https://pruthivithejan.github.io/r10n/run-on-terminal/)
- [Setup Locally](https://pruthivithejan.github.io/r10n/setup-locally/)

## Requirements

- For `uvx` / local source install: Python 3.10+ and [uv](https://docs.astral.sh/uv/)
- For prebuilt binary install: `curl` (macOS/Linux)

## Local Development

```bash
# Clone
git clone https://github.com/pruthivithejan/r10n.git
cd r10n

# Install dependencies
uv sync

# Initialize local folder
uv run r10n init

# Run automations
uv run r10n contacts
uv run r10n fill-pdfs
uv run r10n images
uv run r10n email

# Run tests
uv run pytest

# Build docs
uv run zensical serve
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Pruthivi Thejan** - [@pruthivithejan](https://github.com/pruthivithejan)
