---
icon: lucide/file-text
---

# Markdown to PDF

Convert Markdown files into styled PDF documents with optional custom CSS and table of contents.

---

## Overview

The Markdown to PDF automation turns Markdown content into print-ready PDFs. It supports headings, lists, tables, code blocks, and optional syntax highlighting.

**Key Features:**

- Convert single files or entire directories
- Optional custom CSS styling
- Table of contents support
- Syntax highlighting for code blocks
- Preserves folder structure in batch mode

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n md2pdf
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n md2pdf
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n md2pdf
```

### Command Line Mode

```bash
uv run r10n md2pdf \
  --input ./docs/guide.md \
  --output ./exports/guide.pdf \
  --page-size A4 \
  --syntax-highlight
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--input` | `-i` | string | Yes | `local/inputs/markdown` | Markdown file or directory |
| `--output` | `-o` | string | No | Auto | Output PDF file or directory |
| `--css` | `-c` | string | No | - | Custom CSS file |
| `--page-size` | - | string | No | `A4` | Page size (`A4`, `Letter`, `Legal`*) |
| `--toc` | - | flag | No | `false` | Include table of contents |
| `--syntax-highlight` | - | flag | No | `false` | Enable syntax highlighting |
| `--recursive` | `-r` | flag | No | `false` | Process subdirectories |

\*Note: `Legal` currently falls back to `A4` size.

---

## Examples

### Example 1: Convert a Single File

```bash
uv run r10n md2pdf --input ./docs/guide.md
```

### Example 2: Convert a Directory

```bash
uv run r10n md2pdf \
  --input ./docs \
  --output ./exports \
  --recursive
```

### Example 3: Apply Custom Styles

```bash
uv run r10n md2pdf \
  --input ./docs/guide.md \
  --css ./styles/pdf.css
```

---

## Input Format

Any Markdown file with standard syntax:

```
# Title

## Section

- Bullet 1
- Bullet 2

```python
print("Hello, PDF")
```
```

---

## Output

- Single file mode outputs a PDF next to the input file by default.
- Directory mode outputs PDFs into the provided output folder.

---

## Configuration

No configuration file is required. Optional CSS files can be passed using `--css`.

---

## Troubleshooting

**Issue: Output not created**
- Cause: Input file path incorrect or missing.
- Solution: Verify the path and file extension.

**Issue: Styling not applied**
- Cause: CSS file path not found.
- Solution: Provide a valid `--css` file path.

---

## See Also

- [Fill PDFs](./fill-pdfs.md)
- [Rename Files](./rename-files.md)
