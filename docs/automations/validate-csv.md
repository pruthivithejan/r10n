---
icon: lucide/clipboard-check
---

# Validate CSV

Validate CSV files against a schema and generate readable reports. Optionally clean data for consistent formatting.

---

## Overview

The Validate CSV automation checks rows and columns for type errors, missing fields, and rule violations. It supports schema-based validation and report generation in multiple formats.

**Key Features:**

- Validate against JSON schemas
- Check required fields and data types
- Enforce ranges, patterns, and enums
- Generate reports in text, JSON, or HTML
- Clean and normalize data

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n validate
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n validate
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n validate
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n validate \
  --input ./data/users.csv \
  --schema ./schemas/users.json \
  --format json \
  --output ./reports/users.json
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--input` | `-i` | string | Yes | `local/inputs/validate/data.csv` | Input CSV file |
| `--schema` | `-s` | string | No | - | JSON schema file |
| `--output` | `-o` | string | No | - | Report output file |
| `--strict` | - | flag | No | `false` | Treat warnings as failures |
| `--clean` | - | flag | No | `false` | Trim whitespace and normalize data |
| `--format` | `-f` | string | No | `text` | Report format: `text`, `json`, `html` |

---

## Examples

### Example 1: Validate with Schema

```bash
uv run r10n validate \
  --input ./data/users.csv \
  --schema ./schemas/users.json
```

### Example 2: Generate an HTML Report

```bash
uv run r10n validate \
  --input ./data/users.csv \
  --schema ./schemas/users.json \
  --format html \
  --output ./reports/users.html
```

### Example 3: Clean Data During Validation

```bash
uv run r10n validate \
  --input ./data/users.csv \
  --schema ./schemas/users.json \
  --clean
```

---

## Input Format

Your CSV should include headers in the first row:

```
name,email,age,department
John Doe,john@example.com,30,Engineering
Jane Smith,jane@example.com,25,Marketing
```

### Schema Format

Create a JSON schema with validation rules:

```json
{
  "fields": {
    "name": {"type": "string", "required": true, "min_length": 1},
    "email": {"type": "email", "required": true},
    "age": {"type": "integer", "min": 0, "max": 150},
    "department": {"type": "string", "enum": ["Engineering", "Marketing", "Sales"]}
  }
}
```

---

## Output

- Validation summary printed to the terminal
- Optional report file in text, JSON, or HTML
- Optional cleaned CSV file when prompted

---

## Configuration

No configuration file is required. Validation rules are provided via schema files.

---

## Troubleshooting

**Issue: Schema file not found**
- Cause: Incorrect path or filename.
- Solution: Provide the correct path with `--schema`.

**Issue: Report not saved**
- Cause: Missing `--output` path.
- Solution: Provide an output file path with `--output`.

---

## See Also

- [Contacts](./contacts.md)
- [Rename Files](./rename-files.md)
