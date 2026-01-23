---
icon: material/home
---

# r10n

**Routine Automation** - Automate repetitive tasks with a beautiful CLI.

r10n helps you automate common tasks like generating contact cards, creating certificates, optimizing images, and sending emails. Run it instantly with `uvx` or set it up locally for repeated use.

---

## Navigation

| [Home](index.md) | [Get Started](get-started.md) | [Automations](automations/index.md) |
|------------------|-------------------------------|-------------------------------------|

---

## Quick Start

=== "Run Instantly (uvx)"

    No installation needed. Just run:

    ```bash
    uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
    ```

=== "Setup Locally"

    Clone and install for repeated use:

    ```bash
    git clone https://github.com/pruthivithejan/r10n.git
    cd r10n
    uv sync
    uv run r10n --help
    ```


## Automations

See full guides for each feature:

| Automation      | Description                                         |
|----------------|-----------------------------------------------------|
| [Contacts](automations/contacts.md)      | Generate VCF contact cards from phone numbers         |
| [Certificates](automations/certificates.md) | Create personalized PDF certificates from templates |
| [Images](automations/images.md)          | Optimize and convert images to WebP format           |
| [Email](automations/email.md)            | Send bulk personalized emails with attachments       |

You can also see all automations at a glance: [Automations Index](automations/index.md)


## How It Works

Each automation is interactive - just run the command and follow the prompts:

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

## Requirements

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager

## License

MIT License - see [LICENSE](https://github.com/pruthivithejan/r10n/blob/main/LICENSE) for details.
