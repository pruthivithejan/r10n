---
icon: material/home
---

# r10n

Automate repetitive data and workflow tasks on your terms — with a beautiful CLI and full transparency.

---

<div style="display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 2rem">
  <a href="get-started/" style="flex:1; min-width:250px; border:1px solid var(--md-default-fg-color--lightest); border-radius:.7rem; padding:1.2rem 1rem; display:flex; align-items:center; text-decoration:none; background:var(--md-primary-fg-color--lightest)">
    <span class="twemoji" style="font-size:1.5rem;">:material-rocket-launch:</span>
    <span style="font-size:1.2rem; font-weight:600; margin-left:.7rem;">Get Started</span>
  </a>
  <a href="automations/" style="flex:1; min-width:250px; border:1px solid var(--md-default-fg-color--lightest); border-radius:.7rem; padding:1.2rem 1rem; display:flex; align-items:center; text-decoration:none; background:var(--md-accent-fg-color--lightest)">
    <span class="twemoji" style="font-size:1.5rem;">:material-robot:</span>
    <span style="font-size:1.2rem; font-weight:600; margin-left:.7rem;">Automations</span>
  </a>
</div>

---

## What is r10n?

**r10n** (routine automation) is a Python CLI toolkit to automate day-to-day tasks without code. Each automation is interactive, safe, and auditable.

Run anywhere using [uv](https://docs.astral.sh/uv/) — no install needed!

**Features:**

- Beautiful Rich-powered terminal UI
- Step-by-step interactive prompts
- Run instantly with `uvx` or install locally
- Generate contacts, certificates, optimize images, send emails, and more

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

---

## Available Automations

| Automation | Command | Description |
|------------|---------|-------------|
| [Contacts](automations/contacts/) | `r10n contacts` | Generate VCF contact cards from phone numbers |
| [Certificates](automations/certificates/) | `r10n certificates` | Create personalized PDF certificates |
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
