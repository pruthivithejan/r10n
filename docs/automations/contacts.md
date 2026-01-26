---
icon: material/account-box
---

# Contacts Automation

Easily generate VCF (vCard) contact cards from a bulk list of phone numbers.

## What It Does
- Reads phone numbers from a simple text file (supports Sri Lankan and international formats)
- Adds a prefix (like "Customer") if desired
- Outputs ready-to-import .vcf contact cards

## Usage

Interactive:
```bash
uv run r10n contacts
```

Command-line (bypass prompts):
```bash
uv run r10n contacts \
  --input local/inputs/contacts/numbers.txt \
  --prefix Customer \
  --output local/outputs/contacts/customers.vcf
```

Run with uv / uvx

Run instantly (no install):

```
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts
```

Install locally and run:

```
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n contacts
```

## Input File Format
Create `local/inputs/contacts/numbers.txt`:

```text
# Phone numbers (comments start with #)
0771234567
0781234567
+94791234567
```

## Output
- VCF file is saved to `local/outputs/contacts/`
- Can be imported into any address book or contacts app

## Options
| Option    | Description                           | Example                                  |
|-----------|---------------------------------------|------------------------------------------|
| `--input`   | Path to numbers file                    | `--input local/inputs/contacts/numbers.txt` |
| `--prefix`  | Text to add before each name            | `--prefix Customer`                         |
| `--output`  | Output .vcf file path                  | `--output local/outputs/contacts/my.vcf`     |

## Troubleshooting
- If you see "Command Not Found", ensure you’re in the project folder and uv is installed:
  ```bash
  cd path/to/r10n
  uv run r10n contacts --help
  ```
- Numbers must be valid mobile formats (10-12 digits or with +94 country code).
- Output folder must exist, or you’ll get a file not found/file write error.
