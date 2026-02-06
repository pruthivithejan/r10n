---
icon: lucide/book-user
---

# Contacts

Generate VCF contact cards from a list of phone numbers. Perfect for bulk importing contacts into your phone or CRM.

---

## Overview

The Contacts automation reads phone numbers from a text file and generates a VCF (vCard) file that can be imported into any contacts app or address book.

**Key Features:**

- Supports Sri Lankan phone formats (`+94` and `0xxxxxxxxx`)
- Adds custom prefix to contact names (e.g., "Customer 1", "Customer 2")
- Removes duplicate numbers automatically
- Validates phone number formats

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n contacts
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n contacts
```

Example session:

```
╭───────────────────────────────────────────────────────────────╮
│               Contact Card Generator                           │
│        Convert phone numbers to VCF contact cards              │
╰───────────────────────────────────────────────────────────────╯

Step 1/3: Select input file
  Enter path to file with phone numbers [local/inputs/contacts/numbers.txt]: numbers.txt

Step 2/3: Set contact name prefix
  Enter prefix for contact names [Contact]: Customer

Step 3/3: Set output file
  Enter output VCF file path [local/outputs/contacts/customer_contacts.vcf]: customers.vcf

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

### Command Line Mode

Pass all options directly for scripting:

```bash
uv run r10n contacts \
  --input numbers.txt \
  --prefix Customer \
  --output customers.vcf
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--input` | `-i` | string | Yes | `local/inputs/contacts/numbers.txt` | Path to file with phone numbers |
| `--prefix` | `-p` | string | No | `Contact` | Prefix for contact names |
| `--output` | `-o` | string | No | `local/outputs/contacts/{prefix}_contacts.vcf` | Output VCF file path |

---

## Examples

### Example 1: Basic Usage with uvx

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts \
  --input numbers.txt \
  --output contacts.vcf
```

### Example 2: With Custom Prefix

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts \
  --input ~/Desktop/phone-list.txt \
  --prefix "Lead" \
  --output ~/Desktop/leads.vcf
```

### Example 3: Local Installation

```bash
uv run r10n contacts \
  --input local/inputs/contacts/numbers.txt \
  --prefix Customer \
  --output local/outputs/contacts/customers.vcf
```

### Example 4: Minimal (Interactive)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts
```

---

## Input Format

Create a text file with one phone number per line. Comments start with `#`.

```text
# Customer phone numbers
# Supports various formats

0771234567
0781234567
+94791234567
94761234567
```

**Supported Formats:**

| Format | Example | Description |
|--------|---------|-------------|
| Local 10-digit | `0771234567` | Sri Lankan mobile |
| With country code | `+94771234567` | Sri Lankan mobile with country code |
| Without plus | `94771234567` | Country code without + |

---

## Output

The automation generates a standard VCF (vCard 3.0) file:

```vcf
BEGIN:VCARD
VERSION:3.0
FN:Customer 1
TEL;TYPE=CELL:+94771234567
END:VCARD
BEGIN:VCARD
VERSION:3.0
FN:Customer 2
TEL;TYPE=CELL:+94781234567
END:VCARD
```

**Import locations:**

- **iPhone**: AirDrop the file or email it to yourself
- **Android**: Open with Contacts app
- **Gmail**: Import via Google Contacts
- **Outlook**: Import via People > Manage > Import contacts

---

## Troubleshooting

### "File not found" Error

Make sure your input file exists:

```bash
ls -la numbers.txt
```

The automation will offer to create an example file if it doesn't exist.

### "Invalid number" Warnings

Numbers must be valid Sri Lankan mobile formats:

- `0xxxxxxxxx` (10 digits)
- `+94xxxxxxxxx` or `94xxxxxxxxx`
- No spaces or special characters

### "Output directory does not exist"

The automation creates the output directory automatically. If you get permission errors, check folder permissions:

```bash
mkdir -p local/outputs/contacts
chmod 755 local/outputs/contacts
```

### Duplicates in Output

The automation automatically removes duplicates. The summary shows how many were removed.

---

## See Also

- [Email Automation](email.md) — Send emails to contacts
- [Get Started Guide](../get-started/index.md) — Setup instructions
