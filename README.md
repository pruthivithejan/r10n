# r10n

**Routine Automation** - Automate repetitive tasks with a beautiful CLI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Go](https://img.shields.io/badge/Go-1.24+-00ADD8.svg)](https://go.dev/)
[![uv](https://img.shields.io/badge/uv-Package%20Manager-green.svg)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **Contacts** - Generate VCF contact cards from phone numbers
- **Fill PDFs** - Fill PDF templates with data from CSV/TXT files
- **Images** - Optimize and convert images to WebP format
- **Logos** - Download company logos from SVGL
- **Email** - Send bulk personalized emails with attachments
- **Native Charm shell** - Prebuilt installs use Go, huh forms, and Bubble Tea progress around the existing Python engine
- **Terminal workspace** - Search by task or role, complete validated forms, review inputs, and follow live results
- **Interactive commands** - Step-by-step prompts guide you through each automation
- **Scriptable commands** - Existing Typer subcommands remain available for shell scripts and CI
- **Colors** - Convert CSS color codes (hex, hsl/hsla) to `oklch()` for perceptual color consistency
- **Fast** - Powered by [uv](https://docs.astral.sh/uv/) for lightning-fast dependency management

## Quick Start

### Run Instantly (No Installation)

Use `uvx` to open the terminal workspace without cloning the repository:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n
```

Use `r10n --help` when you want the traditional scriptable command list.

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

## Releases

Use the tag-backed release helper to update all version declarations without
editing them by hand. Patch releases are automatic by default; major and minor
releases require an explicit command.

```bash
# Fix or patch release: 0.11.1 -> 0.11.2
uv run python scripts/release_version.py --publish

# Manual version component changes
uv run python scripts/release_version.py minor --publish
uv run python scripts/release_version.py major --publish
```

The helper updates `pyproject.toml`, `src/cli.py`, and `uv.lock`, then creates
an annotated `vX.Y.Z` tag. `.github/workflows/release.yml` builds and publishes
native binaries and `SHA256SUMS` after a version bump on `main`, or a matching
`vX.Y.Z` tag. Unrelated metadata changes do not trigger publication.
The Go shell embeds the version from `pyproject.toml`; there is no separate Go version to update.

Launch the installed terminal UI:

```bash
r10n
```

## Usage

Prebuilt installs open the native Charm picker; `uvx` and `uv run r10n` retain the
Python/Textual workspace. Both use the same automation registry and Python engine.
Existing subcommand flags continue to work unchanged:

```bash
# Open the terminal workspace
r10n

# Generate contact cards
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts

# Fill PDFs
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n fill-pdfs

# Optimize images
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images

# Download company logos
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n logos --names "OpenAI, Apple, Google" --yes

# Send emails
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email
```

## Terminal Workspace

The workspace generates forms from the same validated automation definitions used by the
execution engine. Search for an automation by name, category, or role; review the resolved
inputs; then follow progress, logs, and generated artifact paths without leaving the app.

Keyboard shortcuts:

- `/` filters the native picker (or focuses search in Textual)
- Arrow keys move through the automation catalog
- Enter selects a task or advances the native form
- `Ctrl+C` cancels the active automation
- Esc cancels native progress; `Ctrl+P` and `Q` remain Textual-only shortcuts

Native installs also support JSON-driven execution:

```bash
r10n run contacts \
  --input-json '{"input_file":"/path/to/numbers.txt","output_file":"/path/to/contacts.vcf"}' \
  --json --yes
```

Use `r10n list --json` to inspect input schemas. `--json` emits the original worker
events without terminal decoration; headless runs require `--yes`. Use
`r10n legacy --help` for the original command list. See the
[native shell guide](docs/get-started/native-shell.md) for development and packaging details.

## CLI Example

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
- For native shell development: Go 1.24+ and the local Python environment

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

### Automation architecture

Automations are registered in `src/automation_registry.py` with a Pydantic input model,
role metadata, and an execution adapter. `src/backend.py` exports that catalog to Go;
both terminal interfaces render the model's JSON Schema. `src/worker.py` runs the automation
through the existing v1 JSON Lines protocol. No task metadata or automation logic is
duplicated in Go.

```bash
uv sync
go run ./cmd/r10n               # Native Charm picker
go test ./...                  # Native shell tests (no Python/network needed)
uv run --with pyinstaller python scripts/build_native.py
```

Unix release archives contain the native executable and a frozen Python sidecar under
`libexec/`. Windows embeds a frozen backend in the existing single `.exe` asset and
extracts it to a verified, private cache. End users need neither Python nor uv.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Pruthivi Thejan** - [@pruthivithejan](https://github.com/pruthivithejan)
