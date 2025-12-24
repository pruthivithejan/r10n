---
icon: material/rocket-launch
---

# Get Started

r10n can be used in two ways: run instantly with `uvx` or set up locally for repeated use.

## Two Ways to Use r10n

### Option 1: Run on Terminal (uvx)

Best for: Quick, one-off tasks without any installation.

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts
```

[Learn more about running on terminal](run-on-terminal.md){ .md-button }

### Option 2: Setup Locally

Best for: Repeated use, custom configurations, and development.

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n contacts
```

[Learn more about local setup](setup-locally.md){ .md-button }

## What's Included

r10n includes 4 automation tools:

### Contacts

Generate VCF contact cards from a list of phone numbers.

- Supports Sri Lankan phone number formats
- Automatically removes duplicates
- Validates number formats
- Outputs standard VCF files

### Certificates

Create personalized PDF certificates from a template.

- Uses any PDF as a template
- Customizable text placement
- Supports CSV or TXT input
- Batch generation

### Images

Optimize and convert images to WebP format.

- Reduces file sizes significantly
- Maintains quality
- Batch processing
- Configurable compression

### Email

Send bulk personalized emails with attachments.

- SMTP support (Gmail, etc.)
- Personal name replacement
- Attach certificates automatically
- Retry on failures

## Prerequisites

Before using r10n, you need:

1. **Python 3.10 or higher**

    Check your version:
    ```bash
    python --version
    ```

2. **uv package manager**

    Install uv:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

    Or on Windows:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

## License

r10n is open source software licensed under the MIT License.

You are free to:

- Use it commercially
- Modify it
- Distribute it
- Use it privately

See the full [LICENSE](https://github.com/pruthivithejan/r10n/blob/main/LICENSE) for details.
