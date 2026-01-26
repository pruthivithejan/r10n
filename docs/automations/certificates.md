---
icon: lucide/file-text
---

# Certificates

Generate personalized PDF certificates from a template. Perfect for courses, events, workshops, and awards.

---

## Overview

The Certificates automation takes a PDF template and a list of recipients, then generates individual PDF certificates with personalized text overlaid on the template.

**Key Features:**

- Uses your own PDF template design
- Supports TXT or CSV recipient files
- Configurable text positioning, fonts, colors, and alignment
- Batch generates all certificates in one run

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n certificates
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n certificates
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n certificates
```

Example session:

```
╭───────────────────────────────────────────────────────────────╮
│               Certificate Generator                            │
│     Create personalized PDF certificates from templates        │
╰───────────────────────────────────────────────────────────────╯

Step 1/4: Select configuration
  Enter path to configuration file [local/configs/certificates.json]: 

Step 2/4: Select PDF template
  Enter path to PDF template [local/inputs/certificates/template.pdf]: 

Step 3/4: Select recipients file
  Enter path to recipients file (TXT or CSV) [local/inputs/certificates/recipients.txt]: 

Step 4/4: Set output directory
  Enter output directory [local/outputs/certificates]: 

Summary:
  Config:     local/configs/certificates.json
  Template:   local/inputs/certificates/template.pdf
  Recipients: local/inputs/certificates/recipients.txt
  Output:     local/outputs/certificates

Proceed with certificate generation? [y/n]: y

Generating certificates...

Done!
┌─────────────────────┬──────────────────────────────┐
│ Total recipients    │ 25                           │
│ Generated           │ 25                           │
│ Failed              │ 0                            │
│ Output directory    │ local/outputs/certificates   │
└─────────────────────┴──────────────────────────────┘
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n certificates \
  --config local/configs/certificates.json \
  --template local/inputs/certificates/template.pdf \
  --recipients local/inputs/certificates/recipients.csv \
  --output local/outputs/certificates
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--config` | `-c` | string | No | `local/configs/certificates.json` | Certificate configuration file |
| `--template` | `-t` | string | No | From config or `local/inputs/certificates/template.pdf` | PDF template file |
| `--recipients` | `-r` | string | Yes | `local/inputs/certificates/recipients.txt` | Recipients data file (TXT or CSV) |
| `--output` | `-o` | string | No | `local/outputs/certificates` | Output directory |

---

## Examples

### Example 1: Basic Usage with uvx

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n certificates \
  --template template.pdf \
  --recipients participants.csv \
  --output ./certificates
```

### Example 2: With Full Configuration

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n certificates \
  --config cert-config.json \
  --template ~/Desktop/certificate-template.pdf \
  --recipients ~/Desktop/workshop-attendees.csv \
  --output ~/Desktop/generated-certificates
```

### Example 3: Local Installation

```bash
uv run r10n certificates \
  --config local/configs/certificates.json \
  --template local/inputs/certificates/template.pdf \
  --recipients local/inputs/certificates/recipients.csv \
  --output local/outputs/certificates
```

### Example 4: Interactive Mode

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n certificates
```

---

## Input Files

### Recipients File (TXT Format)

Tab-separated values, one recipient per line:

```text
# Recipients file (one per line)
# Format: Name<TAB>Position
John Doe	Team Lead
Jane Smith	Developer
Bob Johnson	Designer
```

### Recipients File (CSV Format)

CSV with headers matching your configuration fields:

```csv
name,position
John Doe,Team Lead
Jane Smith,Developer
Bob Johnson,Designer
```

### PDF Template

Design your certificate in any PDF editor (Canva, Adobe Illustrator, etc.). Leave blank spaces where text will be inserted. Note the X,Y coordinates for text placement.

---

## Configuration

Create `local/configs/certificates.json`:

```json
{
  "template_pdf": "local/inputs/certificates/template.pdf",
  "output_directory": "local/outputs/certificates",
  "font_family": "Helvetica",
  "fields": {
    "name": {
      "x": 300,
      "y": 400,
      "font_size": 36,
      "font_weight": "bold",
      "alignment": "center",
      "color": [0, 0, 0]
    },
    "position": {
      "x": 300,
      "y": 350,
      "font_size": 24,
      "font_weight": "normal",
      "alignment": "center",
      "color": [50, 50, 50]
    }
  }
}
```

### Configuration Options

| Key | Type | Description |
|-----|------|-------------|
| `template_pdf` | string | Path to PDF template |
| `output_directory` | string | Where to save generated certificates |
| `font_family` | string | Font to use (Helvetica, Times-Roman, Courier) |
| `fields` | object | Field configurations (see below) |

### Field Configuration

| Key | Type | Description |
|-----|------|-------------|
| `x` | number | Horizontal position in points (from left) |
| `y` | number | Vertical position in points (from bottom) |
| `font_size` | number | Font size in points |
| `font_weight` | string | `normal` or `bold` |
| `alignment` | string | `left`, `center`, or `right` |
| `color` | array | RGB values [R, G, B] (0-255) |

---

## Output

Generated certificates are saved as individual PDF files:

```
local/outputs/certificates/
├── John_Doe.pdf
├── Jane_Smith.pdf
└── Bob_Johnson.pdf
```

Filenames are based on the recipient's name with spaces replaced by underscores.

---

## Troubleshooting

### "Template not found"

Ensure your PDF template exists:

```bash
ls -la local/inputs/certificates/template.pdf
```

### Text Appears in Wrong Position

Adjust the `x` and `y` values in your configuration. PDF coordinates start from the bottom-left corner:

- `x`: Distance from left edge (in points, 72 points = 1 inch)
- `y`: Distance from bottom edge

### Fonts Not Rendering Correctly

Use built-in PDF fonts: `Helvetica`, `Times-Roman`, `Courier`. Custom fonts require additional setup.

### CSV Parsing Errors

Ensure your CSV has proper headers matching the field names in your configuration:

```csv
name,position
John Doe,Team Lead
```

---

## See Also

- [Email Automation](email.md) — Send certificates via email
- [Get Started Guide](../get-started/index.md) — Setup instructions
