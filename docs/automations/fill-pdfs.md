---
icon: lucide/file-text
---

# Fill PDFs

Create personalized PDFs from a template and recipient data.

## Overview

The PDF automation places recipient fields on a chosen PDF template. Template
layout is configured once in a named profile using the terminal; profiles are
saved to system settings, not to a project JSON file or browser service.

## Configure a profile

Start the terminal setup wizard:

```bash
r10n configure --template /path/to/template.pdf
```

Optionally pass a CSV, XLSX, or TXT recipient file so r10n can suggest field
names:

```bash
r10n configure \
  --template /path/to/template.pdf \
  --recipients /path/to/recipients.csv \
  --name conference
```

The guided form collects coordinates in PDF points, font styling, and an output
directory. It previews a sample and asks before saving the profile. Coordinates
use the PDF page's left and bottom edges as the origin.

## Generate documents

Select the saved profile and the input data:

```bash
r10n fill-pdfs \
  --config conference \
  --recipients /path/to/recipients.csv \
  --yes
```

For interactive use, `r10n fill-pdfs` opens a guided form. `--config` (also
`-c`) is the saved profile name; it is no longer a path to a JSON file.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--config` | `-c` | No | Active profile or `default` | Saved system PDF profile name |
| `--recipients` | `-r` | Yes | — | CSV, XLSX, or TXT recipient data |
| `--yes` | `-y` | No | `false` | Skip interactive confirmation |

## Input data

CSV and XLSX inputs use a header row for field names. TXT inputs contain one
recipient name per line. For example:

```csv
Name,Role
Alex Morgan,Speaker
Sam Lee,Organizer
```

The columns used in the profile must match the recipient file's field names.

## Output

Generated PDFs are written to the directory saved in the selected profile.
Each output uses a sanitized recipient name; collisions get a numeric suffix.
The completion summary reports generated and failed files.

## Troubleshooting

**Profile not found:** Run `r10n configure --template /path/to/template.pdf`
and save a profile first. Use `r10n config path` to inspect the system settings
location.

**Recipient field missing:** Check that CSV/XLSX column headers match the field
names saved in the profile.

**Text appears in the wrong place:** Reopen `r10n configure`, select the profile
name, adjust the field coordinates, and save the updated profile.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Contacts automation](contacts.md)
- [Get started](../get-started/index.md)
