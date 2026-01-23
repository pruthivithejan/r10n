---
icon: material/school
---

# Certificates Automation

Create custom PDF certificates from a template for each recipient in your list.

## What It Does
- Uses your template PDF
- Places names/fields dynamically
- Supports rich formatting (font size, position, style)
- Outputs personalized PDF certificates in batch

## Usage

Interactive:
```bash
uv run r10n certificates
```

Command-line:
```bash
uv run r10n certificates 
```

## Quick Start Steps
1. Place your template at `local/inputs/certificates/template.pdf`.
2. Prepare a recipients file in either format:
   - **TXT:**
     ```text
     John Doe\tTeam Lead
     Jane Smith\tDeveloper
     ```
   - **CSV:**
     ```csv
     name,position
     John Doe,Team Lead
     Jane Smith,Developer
     ```
3. Optionally edit or create a config at `local/configs/certificates.json` (fields, font, colors).

## Configuration Example

```json
{
  "template_pdf": "local/inputs/certificates/template.pdf",
  "output_directory": "local/outputs/certificates",
  "font_family": "Helvetica",
  "fields": {
    "name": { "x": 300, "y": 400, "font_size": 36, "font_weight": "bold", "alignment": "center", "color": [0,0,0] },
    "position": { "x": 300, "y": 350, "font_size": 24, "font_weight": "normal", "alignment": "center", "color": [50,50,50] }
  }
}
```

## Output
- Personalized PDFs saved in `local/outputs/certificates/`.

## Options
| Option           | Description                           |
|------------------|---------------------------------------|
| `--config`       | Path to certificates config JSON       |
| `--recipients`   | Recipients file path (.txt or .csv)   |
| `--template`     | Template PDF file                     |
| `--output`       | Output folder                         |

## Troubleshooting
- Ensure your template matches the config field positions
- Make sure output folder exists and is writable
- PDF not generated? Check config and input paths carefully