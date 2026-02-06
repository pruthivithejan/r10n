---
icon: lucide/square-terminal
---

# Run on Terminal

Run r10n directly from your terminal without cloning or installing anything. Perfect for quick, one-off automation tasks.

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

## Run Any Automation Instantly

Use `uvx` to run r10n without installing:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
```

This downloads r10n temporarily, runs it, and cleans up automatically.

---

## Available Commands

List all available automations:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n --help
```

Output:

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

## Quick Examples

### Generate Contact Cards

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts \
  --input numbers.txt \
  --prefix Customer \
  --output customers.vcf
```

### Optimize Images

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images \
  --input ./photos \
  --output ./optimized \
  --quality 85
```

### Convert Colors to oklch

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors \
  --file styles.css
```

### Generate Certificates

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n certificates \
  --template template.pdf \
  --recipients participants.csv \
  --output ./certificates
```

### Send Bulk Emails

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n email \
  --config email-config.json \
  --recipients recipients.csv \
  --body message.txt
```

---

## Interactive Mode

Run any command without arguments to enter interactive mode:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts
```

The CLI will guide you through each step:

```
╭─────────────────────────────────────────────────────────────╮
│                    📇 Contact Generator                      │
│         Generate VCF contact cards from phone numbers        │
╰─────────────────────────────────────────────────────────────╯

Step 1/3: Select input file
Enter path to file with phone numbers: numbers.txt

Step 2/3: Set contact name prefix
Enter prefix for contact names [Contact]: Customer

Step 3/3: Set output file
Enter output VCF file path [contacts.vcf]: customers.vcf

Summary:
  Input file: numbers.txt
  Prefix: Customer
  Output: customers.vcf

Proceed with contact generation? [y/n]: y
```

---

## Creating Input Files

For most automations, you'll need to create input files first. Here are examples:

### Phone Numbers (for contacts)

Create `numbers.txt`:

```text
# Phone numbers (comments start with #)
0771234567
0781234567
+94791234567
```

### Recipient List (for email)

Create `recipients.csv`:

```csv
Name,Email
John Doe,john@example.com
Jane Smith,jane@example.com
Support Team,support@company.org
```

### CSV Data (for certificates)

Create `participants.csv`:

```csv
name,course,date
John Doe,Web Development,2025-01-15
Jane Smith,Data Science,2025-01-15
```

---

## Tips

1. **Create an alias** for frequent use:
   ```bash
   alias r10n='uvx --from git+https://github.com/pruthivithejan/r10n.git r10n'
   ```

   Then run:
   ```bash
   r10n contacts --help
   ```

2. **Use absolute paths** when specifying files:
   ```bash
   uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts \
     --input /Users/you/Desktop/numbers.txt \
     --output /Users/you/Desktop/contacts.vcf
   ```

3. **Check command help** for all available options:
   ```bash
   uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts --help
   ```

---

## Troubleshooting

### "Command not found: uvx"

Install uv first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your terminal or run:

```bash
source ~/.bashrc  # or ~/.zshrc
```

### "No such file or directory"

Make sure your input file exists and the path is correct:

```bash
ls -la numbers.txt
```

### Network Issues

If you're behind a firewall or have slow internet, consider [setting up locally](setup-locally.md) instead.

---

## Next Steps

- [Setup Locally](setup-locally.md) — For repeated use or development
- [Automations](../automations/index.md) — Detailed guides for each automation
- [GitHub Issues](https://github.com/pruthivithejan/r10n/issues) — Get help or report bugs
