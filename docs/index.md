---
icon: lucide/house
---

# r10n

Automate repetitive data and workflow tasks on your terms — with a beautiful CLI and full transparency.

---

<div style="display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 2rem">
  <a href="get-started/" style="flex:1; min-width:250px; border:1px solid var(--md-default-fg-color--lightest); border-radius:.7rem; padding:1.2rem 1rem; display:flex; align-items:center; text-decoration:none; background:var(--md-primary-fg-color--lightest)">
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>
    <span style="font-size:1.2rem; font-weight:600; margin-left:.7rem;">Get Started</span>
  </a>
  <a href="automations/" style="flex:1; min-width:250px; border:1px solid var(--md-default-fg-color--lightest); border-radius:.7rem; padding:1.2rem 1rem; display:flex; align-items:center; text-decoration:none; background:var(--md-accent-fg-color--lightest)">
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/><path d="m14 7 3 3"/><path d="M5 6v4"/><path d="M19 14v4"/><path d="M10 2v2"/><path d="M7 8H3"/><path d="M21 16h-4"/><path d="M11 3H9"/></svg>
    <span style="font-size:1.2rem; font-weight:600; margin-left:.7rem;">Automations</span>
  </a>
</div>

---

## What is r10n?

**r10n** (routine automation) is a Python CLI toolkit to automate day-to-day tasks without code. Each automation is interactive, safe, and auditable.

Run anywhere using [uv](https://docs.astral.sh/uv/) — no install needed!

**Features:**

- Beautiful Rich-powered terminal UI
- Persistent home screen for installed binary use
- Step-by-step interactive prompts
- Run instantly with `uvx` or install locally
- Generate contacts, fill PDFs, optimize images, send emails, and more

---

## Quick Start

=== "Run Instantly (uvx)"

    Run any automation without installation:

    ```bash
    uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
    ```

=== "Install Locally"

    Clone for repeated use:

    ```bash
    git clone https://github.com/pruthivithejan/r10n.git
    cd r10n
    uv sync
    uv run r10n --help
    ```

=== "Install Binary (curl)"

    Install the standalone binary:

    ```bash
    curl -fsSL https://raw.githubusercontent.com/pruthivithejan/r10n/main/install.sh | sh
    ```

    Update later with:

    ```bash
    r10n upgrade
    ```

    Launch the terminal UI:

    ```bash
    r10n
    ```

---

## Available Automations

| Automation | Command | Description |
|------------|---------|-------------|
| [Contacts](automations/contacts/) | `r10n contacts` | Generate VCF contact cards from phone numbers |
| [Fill PDFs](automations/fill-pdfs/) | `r10n fill-pdfs` | Fill PDF templates with data |
| [Images](automations/images/) | `r10n images` | Optimize and convert images to WebP |
| [Email](automations/email/) | `r10n email` | Send bulk emails with attachments |
| [Colors](automations/colors/) | `r10n colors` | Convert CSS colors to oklch() |

Browse all: [Automations](automations/)

---

## Example: Generate Contacts

```bash
$ uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts

╭───────────────────────────────────────────────────────────────╮
│               Contact Card Generator                           │
│        Convert phone numbers to VCF contact cards              │
╰───────────────────────────────────────────────────────────────╯

Step 1/3: Select input file
  Enter path to file with phone numbers: numbers.txt

Step 2/3: Set contact name prefix
  Enter prefix for contact names [Contact]: Customer

Step 3/3: Set output file
  Enter output VCF file path: customers.vcf

Summary:
  Input file:  numbers.txt
  Prefix:      Customer
  Output file: customers.vcf

Proceed with contact generation? [y/n]: y

Generating contacts...

Done!
┌─────────────────────┬──────────────┐
│ Total numbers       │ 150          │
│ Valid contacts      │ 145          │
│ Duplicates removed  │ 3            │
│ Invalid numbers     │ 2            │
│ Output file         │ customers.vcf│
└─────────────────────┴──────────────┘
```

---

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

**Install uv:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Get Help

- [Get Started Guide](get-started/) — Step-by-step setup
- [Automations](automations/) — All automation docs
- [GitHub Issues](https://github.com/pruthivithejan/r10n/issues) — Ask questions & report bugs

---

## License

MIT — see [LICENSE](https://github.com/pruthivithejan/r10n/blob/main/LICENSE) for details.
