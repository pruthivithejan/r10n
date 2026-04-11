---
icon: lucide/file-text
---

# Fill PDFs

Fill PDF templates with data from CSV or TXT files. Perfect for certificates, awards, letters, invoices, name badges, and any document that needs personalized text overlaid on a PDF template.

---

## Overview

The Fill PDFs automation takes a PDF template and a data file, then generates individual PDFs with personalized text overlaid on the template.

**Key Features:**

- Uses your own PDF template design
- Supports TXT or CSV data files
- Visual field picker -- click on the template to place fields
- Preview-and-approve loop before batch generation
- Configurable text positioning, fonts, colors, and alignment
- Batch generates all PDFs in one run

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n fill-pdfs
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n fill-pdfs
```

---

## Usage

### Interactive Mode

Run without arguments for a guided two-step process:

```bash
uv run r10n fill-pdfs
```

The CLI walks you through two steps:

1. **Select your data file** (CSV or TXT with one row per document)
2. **Select or create a configuration** -- if no config exists, the visual field picker opens automatically

After configuration, a **preview** of the first entry opens in your PDF viewer. If it looks correct, approve it and the full batch is generated. If not, the visual picker re-opens so you can adjust field positions.

Example session:

```
+---------------------------------------------------------------+
|                       PDF Filler                              |
|       Fill PDF templates with data from CSV/TXT files         |
+---------------------------------------------------------------+

Step 1/2: Select data file
  Enter path to data file (CSV or TXT) [local/inputs/fill-pdfs/data.csv]:

Step 2/2: Configuration
  Enter path to configuration file [local/configs/fill-pdfs.json]:

  Config not found: local/configs/fill-pdfs.json
  Opening visual picker to configure field positions...

  Enter path to PDF template [local/inputs/fill-pdfs/template.pdf]:
  Config saved: local/configs/fill-pdfs.json

Generating preview for: John Doe
  Preview generated.
  Preview opened in your default PDF viewer.

Does the preview look correct? [Y/n]: y

Generating 25 PDFs...

Done!
+---------------------+------------------------------+
| Total recipients    | 25                           |
| Generated           | 25                           |
| Failed              | 0                            |
| Output directory    | local/outputs/fill-pdfs      |
+---------------------+------------------------------+
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n fill-pdfs \
  --config local/configs/fill-pdfs.json \
  --recipients local/inputs/fill-pdfs/data.csv
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--config` | `-c` | string | No | `local/configs/fill-pdfs.json` | Configuration file |
| `--recipients` | `-r` | string | Yes | `local/inputs/fill-pdfs/data.csv` | Data file (TXT or CSV) |
| `--template` | `-t` | string | No | From config or `local/inputs/fill-pdfs/template.pdf` | PDF template file (used for initial setup) |

---

## Visual Field Picker

Instead of manually writing coordinates in JSON, use the visual picker to place fields by clicking on your PDF template:

```bash
uv run r10n configure --template template.pdf --recipients data.csv
```

This opens a browser-based tool where you can:

1. **Click on the template** to place fields at exact positions
2. **Drag markers** to reposition fields
3. **Configure each field** -- font size, weight, alignment, and color
4. **Preview** the result with sample data
5. **Save** the configuration JSON

### Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--template` | `-t` | string | Yes | -- | PDF template file |
| `--recipients` | `-r` | string | No | -- | CSV file (used to populate field name dropdown) |
| `--output` | `-o` | string | No | `local/configs/fill-pdfs.json` | Output config path |

The visual picker is also offered automatically when you run `r10n fill-pdfs` without an existing configuration file.

### Preview-Approve Loop

After configuring fields (or loading an existing config), the CLI generates a **preview PDF** using the first row of your data and opens it in your default PDF viewer. You can then:

- **Approve** the preview to proceed with batch generation
- **Reject** the preview to re-open the visual picker and adjust field positions

This loop repeats until you're satisfied with the result, ensuring the final batch looks exactly right.

---

## Examples

### Example 1: Certificates

```bash
r10n fill-pdfs \
  --template certificate-template.pdf \
  --recipients participants.csv
```

### Example 2: Name Badges

```bash
r10n fill-pdfs \
  --config badge-config.json \
  --recipients attendees.csv
```

### Example 3: Letters

```bash
r10n fill-pdfs \
  --config letter-config.json \
  --recipients clients.csv
```

### Example 4: Interactive Mode

```bash
r10n fill-pdfs
```

---

## Input Files

### Data File (TXT Format)

Tab-separated values, one entry per line:

```text
# Data file (one per line)
# Format: Name<TAB>Position
John Doe	Team Lead
Jane Smith	Developer
Bob Johnson	Designer
```

### Data File (CSV Format)

CSV with headers matching your configuration fields:

```csv
name,position
John Doe,Team Lead
Jane Smith,Developer
Bob Johnson,Designer
```

### PDF Template

Design your template in any PDF editor (Canva, Adobe Illustrator, etc.). Leave blank spaces where text will be inserted. Use `r10n configure` to visually place fields.

---

## Configuration

Create `local/configs/fill-pdfs.json` (or use the visual picker to generate it):

```json
{
  "template_pdf": "local/inputs/fill-pdfs/template.pdf",
  "output_directory": "local/outputs/fill-pdfs",
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
| `output_directory` | string | Where to save generated PDFs |
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

Generated PDFs are saved as individual files:

```
local/outputs/fill-pdfs/
+-- John_Doe.pdf
+-- Jane_Smith.pdf
+-- Bob_Johnson.pdf
```

Filenames are based on the name field with spaces replaced by underscores.

---

## Troubleshooting

### "Template not found"

Ensure your PDF template exists:

```bash
ls -la local/inputs/fill-pdfs/template.pdf
```

### Text Appears in Wrong Position

Use `r10n configure --template your-template.pdf` to visually reposition fields instead of guessing coordinates. If editing manually, PDF coordinates start from the bottom-left corner:

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

- [Email Automation](email.md) -- Send filled PDFs via email
- [Get Started Guide](../get-started/index.md) -- Setup instructions
