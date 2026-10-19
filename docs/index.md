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

**r10n** (routine automation) is a native Go CLI with a Python automation engine for day-to-day tasks without code. Each automation supports reviewed interactive execution and explicit headless execution.

Install the standalone application once for regular use, or run a released
version with [uvx](https://docs.astral.sh/uv/).

**Features:**

- Searchable native Charm picker with generated, validated forms
- Review screens, live logs, progress, cancellation, and artifact paths
- Step-by-step interactive prompts
- Checksum-verified standalone installer with real download progress
- Per-user system settings and profiles; no project-local setup folders
- Generate contacts, fill PDFs, optimize images, send emails, and more

---

## Quick Start

=== "Install Binary"

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

=== "Run with uvx"

    Run the released application without a persistent standalone install:

    ```bash
    uvx --from git+https://github.com/pruthivithejan/r10n.git r10n
    ```

    uvx requires Python 3.10+ and may need Go for unreleased source versions.

=== "Configure in the terminal"

    Save accessibility and output preferences to your system settings:

    ```bash
    r10n setup
    r10n config path
    ```

---

## Available Automations

| Automation | Command | Description |
|------------|---------|-------------|
| [Contacts](automations/contacts/) | `r10n contacts` | Generate VCF contact cards from phone numbers |
| [Fill PDFs](automations/fill-pdfs/) | `r10n fill-pdfs` | Fill PDF templates with data |
| [Images](automations/images/) | `r10n images` | Optimize and convert images to WebP |
| [Logos](automations/logos/) | `r10n logos` | Download company logos from SVGL |
| [Email](automations/email/) | `r10n email` | Send bulk emails with attachments |
| [Colors](automations/colors/) | `r10n colors` | Convert CSS colors to oklch() |

Browse all: [Automations](automations/)

---

## Example: Generate Contacts

```bash
$ r10n contacts --input /path/to/numbers.txt --output /path/to/customers.vcf
Review the resolved paths in the terminal form, then confirm to run.
```

---

## Requirements

- Standalone installer: `curl` on Linux x86_64 or macOS arm64; Python is not required
- uvx: [uv](https://docs.astral.sh/uv/) and Python 3.10+ (uv can provision Python)
- Windows x86_64: download the standalone `.exe` from GitHub Releases

Install uv only when you plan to use `uvx`:

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
