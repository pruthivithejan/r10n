---
icon: lucide/book-user
---

# Contacts

Generate VCF contact cards from a text file of phone numbers.

## Overview

The contacts automation reads one number per line, validates Sri Lankan mobile
formats, removes duplicates, and writes a standard vCard 3.0 file.

## Run

The recommended setup is the standalone terminal app:

```bash
r10n contacts
```

The guided form asks for an input file, a contact-name prefix, and an output
path. To run noninteractively, supply all required values and `--yes`:

```bash
r10n contacts \
  --input /path/to/numbers.txt \
  --prefix Customer \
  --output /path/to/customers.vcf \
  --yes
```

`uvx` can run a released version without a persistent binary installation:

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n contacts
```

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | — | Text file containing one phone number per line |
| `--prefix` | `-p` | No | `Contact` | Prefix used in generated contact names |
| `--output` | `-o` | No | `r10n-output/contacts.vcf` | VCF output file |
| `--yes` | `-y` | No | `false` | Skip interactive confirmation |

The default output root can be changed with `r10n setup`. Input and explicitly
specified output paths are used as given; r10n does not create project-local
configuration folders.

## Input format

Put one number per line. Lines beginning with `#` and blank lines are ignored.

```text
# Customer phone numbers
0771234567
+94791234567
94761234567
```

Supported formats include `0771234567`, `+94771234567`, and `94771234567`.

## Output

The output is a VCF file that can be imported into phone contacts, Gmail,
Outlook, and other address books:

```vcf
BEGIN:VCARD
VERSION:3.0
FN:Customer 1
TEL;TYPE=CELL:+94771234567
END:VCARD
```

## Troubleshooting

**Input file not found:** Check the path with `ls -l /path/to/numbers.txt` and
select the file in the guided form or pass its path with `--input`.

**Invalid phone number:** Use a Sri Lankan mobile number in a supported format.
The completion summary reports invalid entries and duplicates.

**Output permission error:** Choose a writable destination, or set another
default output directory in `r10n setup`.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Email automation](email.md)
- [Get started](../get-started/index.md)
