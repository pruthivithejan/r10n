---
icon: material/home
---

# r10n

Automate repetitive data and workflow tasks on your terms — with a beautiful CLI and full transparency.

---

<div style="display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 2rem">
  <a href="get-started/index.md" style="flex:1; min-width:250px; border:1px solid var(--md-default-fg-color--lightest); border-radius:.7rem; padding:1.2rem 1rem; display:flex; align-items:center; text-decoration:none; background:var(--md-primary-fg-color--lightest)"><span class="md-icon" aria-hidden="true">rocket_launch</span><span style="font-size:1.2rem; font-weight:600; margin-left:.7rem;">Get Started</span></a>
  <a href="automations/index.md" style="flex:1; min-width:250px; border:1px solid var(--md-default-fg-color--lightest); border-radius:.7rem; padding:1.2rem 1rem; display:flex; align-items:center; text-decoration:none; background:var(--md-accent-fg-color--lightest)"><span class="md-icon" aria-hidden="true">auto_awesome</span><span style="font-size:1.2rem; font-weight:600; margin-left:.7rem;">Automations</span></a>
</div>

---

**r10n lets you instantly automate contact card generation, certificates, image conversion, bulk email, and more!**

---

## 👋 What is r10n?

A Python CLI toolkit to automate day-to-day tasks without code. Each automation is interactive, safe, and auditable. Run anywhere using [uv](https://docs.astral.sh/uv/) — no install needed!

---

## 🚀 Quick Start

=== "Run Instantly (uvx)"

    Run any automation from the repo (no installation!):

    ```bash
    uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
    ```

=== "Install Locally"

    Clone and use offline for repeated workflows:

    ```bash
    git clone https://github.com/pruthivithejan/r10n.git
    cd r10n
    uv sync
    uv run r10n --help
    ```

---

## 💡 Explore Automations

See guides for every feature:

- [Contacts](automations/contacts.md): Generate VCF contact cards.
- [Certificates](automations/certificates.md): Build branded PDF certificates.
- [Images](automations/images.md): Optimize and convert images.
- [Email](automations/email.md): Send bulk emails with attachments.

Or browse all at once ➡️ [Automations Index](automations/index.md)

---

## 🆘 Get Help | Join Community

- [Get Started](get-started/index.md) — Step-by-step tutorial for new users.
- [Automations](automations/index.md) — All automation docs.
- [GitHub Issues](https://github.com/pruthivithejan/r10n/issues) — Ask & report bugs.
- Coming soon: [Discussions](https://github.com/pruthivithejan/r10n/discussions)

---

## ⚡ Example: Run an Automation

```bash
$ uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts

Step 1/3: Select input file
Enter path to file with phone numbers: numbers.txt
Step 2/3: Set contact name prefix
Enter prefix for contact names: Customer
Step 3/3: Set output file
Enter output VCF file path: customers.vcf

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

## 📦 Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

---

## 🛡 License
MIT — see [LICENSE](https://github.com/pruthivithejan/r10n/blob/main/LICENSE) for details.
