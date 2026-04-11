---
icon: lucide/cpu
---

# MCP Server

Use r10n automations directly from AI assistants like Claude Desktop via the Model Context Protocol (MCP).

---

## Overview

The r10n MCP server exposes all automations as tools that AI assistants can invoke programmatically. Instead of using the interactive CLI, an AI assistant can call `generate_contacts`, `optimize_images`, `validate_csv`, and more — passing parameters directly and receiving structured results.

The server also provides resources like config templates, so AI assistants can understand the expected formats before invoking tools.

**What you get:**

- All 8 automations available as MCP tools
- Config templates exposed as readable resources
- stdio transport for seamless integration with Claude Desktop
- Structured JSON responses for every tool call

---

## Quick Start

### Claude Desktop

Add the following to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "r10n": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/pruthivithejan/r10n.git", "r10n-mcp"]
    }
  }
}
```

Restart Claude Desktop. You should see r10n's tools available in the tools menu.

### Local Installation

If you have r10n installed locally:

```bash
uv run r10n mcp
```

Or use the direct entry point:

```bash
r10n-mcp
```

---

## Available Tools

### generate_contacts

Generate VCF contact cards from a file of phone numbers.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_file` | string | Yes | — | Path to text file with phone numbers |
| `output_name` | string | No | `contacts.vcf` | Output VCF filename |
| `prefix` | string | No | `Contact` | Prefix for contact names |

**Returns:** Total numbers, valid contacts, duplicates removed, invalid count, output file path.

---

### fill_pdfs

Fill PDF templates with data from CSV/TXT files.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `recipients_file` | string | Yes | -- | Path to CSV/TXT with row data |
| `config_file` | string | Yes | -- | Path to JSON configuration file |
| `base_dir` | string | No | `data/fill-pdfs` | Base directory for relative paths |

**Returns:** Total entries, generated count, failed count, errors, output directory.

See the [fill-pdfs config template](#config-templates) for the expected JSON format.

---

### optimize_images

Optimize and convert images to WebP format.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_dir` | string | Yes | — | Directory containing images |
| `output_dir` | string | No | auto-generated | Output directory |
| `prefix` | string | No | `img` | Filename prefix |
| `max_size_mb` | float | No | `1.0` | Target max file size in MB |
| `quality` | integer | No | `85` | Image quality (1-100) |
| `max_width` | integer | No | `1920` | Max width in pixels |
| `max_height` | integer | No | `1080` | Max height in pixels |
| `preserve_filename` | boolean | No | `false` | Keep original filenames |

**Returns:** Processed count, skipped count, failed count, size before/after, file details.

---

### send_email

Send bulk personalized emails with optional PDF attachments.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `email_list_file` | string | Yes | — | CSV file with Name and Email columns |
| `subject` | string | Yes | — | Email subject line |
| `body_template` | string | Yes | — | Path to email body template file |
| `config_file` | string | Yes | — | Path to SMTP configuration JSON |
| `certificates_dir` | string | No | -- | Directory with PDF attachments |

**Returns:** Sent count, failed count, total, failed emails list, missing PDFs list.

See the [email config template](#config-templates) for SMTP configuration format.

---

### convert_colors

Convert CSS color codes (hex, rgb, hsl, named) to oklch() format.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | — | Directory with CSS files |
| `file` | string | No | — | Single CSS file (overrides `path`) |
| `dry_run` | boolean | No | `false` | Preview changes without writing |
| `no_backup` | boolean | No | `false` | Skip creating `.bak` files |
| `excludes` | list | No | — | Additional directories to exclude |

**Returns:** Files found, files modified, total changes, per-file details.

---

### rename_files

Batch rename files using patterns, prefixes, suffixes, and more.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_directory` | string | Yes | — | Directory with files to rename |
| `pattern` | string | No | — | Pattern with `{name}`, `{ext}`, `{date}`, `{sequence}` placeholders |
| `prefix` | string | No | — | Add prefix to filenames |
| `suffix` | string | No | — | Add suffix before extension |
| `replace_from` | string | No | — | Text to find |
| `replace_to` | string | No | — | Replacement text |
| `add_date` | boolean | No | `false` | Prepend date to filename |
| `add_sequence` | boolean | No | `false` | Add sequence numbers |
| `lowercase` | boolean | No | `false` | Convert to lowercase |
| `uppercase` | boolean | No | `false` | Convert to uppercase |
| `recursive` | boolean | No | `false` | Process subdirectories |
| `dry_run` | boolean | No | `false` | Preview only |
| `file_pattern` | string | No | `*` | Glob pattern to match files |

**Returns:** Success status, total files, renamed count, skipped count, errors, renamed file pairs.

---

### validate_csv

Validate CSV files against a schema with optional cleaning.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_file` | string | Yes | — | CSV file to validate |
| `schema_file` | string | No | — | JSON schema file |
| `output_file` | string | No | — | Path for cleaned output |
| `strict_mode` | boolean | No | `false` | Fail on warnings |

**Returns:** Validity status, total/valid/invalid row counts, errors, warnings.

---

### convert_markdown_to_pdf

Convert Markdown documents to styled PDF files.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_path` | string | Yes | — | Markdown file path |
| `output_path` | string | No | auto-generated | Output PDF path |
| `css_file` | string | No | — | Custom CSS file |
| `page_size` | string | No | `A4` | Page size (`A4`, `Letter`) |
| `margin_top` | integer | No | `20` | Top margin in mm |
| `margin_bottom` | integer | No | `20` | Bottom margin in mm |
| `include_toc` | boolean | No | `false` | Include table of contents |

**Returns:** Success status, input/output paths, page count.

---

## Available Resources

The MCP server exposes config templates and automation metadata as resources.

| Resource URI | Description |
|-------------|-------------|
| `r10n://configs/fill-pdfs` | Default PDF fill config |
| `r10n://configs/email` | Default SMTP and email config |
| `r10n://configs/images` | Default image optimization config |
| `r10n://configs/blog` | Default blog generation config |
| `r10n://automations` | List of all automations with descriptions |

Use the `r10n://configs/*` resources to see the expected JSON format before creating config files for tools that need them.

---

## Config Templates

### Fill PDFs Config

```json
{
  "template_pdf": "path/to/template.pdf",
  "output_directory": "path/to/output",
  "font_family": "Helvetica",
  "fields": {
    "name": {
      "x": 300, "y": 400,
      "font_size": 36,
      "font_weight": "bold",
      "alignment": "center",
      "color": [0, 0, 0]
    }
  }
}
```

### Email Config

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "email": "sender@example.com",
  "password": "app-password",
  "subject": "Your Subject",
  "use_tls": true
}
```

### Images Config

```json
{
  "input_directory": "path/to/images",
  "output_directory": "path/to/output",
  "prefix": "img",
  "max_size_mb": 1.0,
  "quality": 85,
  "max_width": 1920,
  "max_height": 1080,
  "convert_to_webp": true,
  "preserve_filename": false
}
```

---

## Troubleshooting

### Server Not Appearing in Claude Desktop

1. Make sure the config path is correct for your OS
2. Restart Claude Desktop after changing the config
3. Check that `uvx` is installed and accessible from your PATH

### "Tool execution failed" Errors

The server returns structured error messages. Common causes:

- **File not found**: Check that file paths are absolute or relative to the working directory
- **Missing config**: Some tools (fill-pdfs, email) require a config file -- use the resources to see the expected format
- **Permission denied**: Ensure the server process has read/write access to the specified directories

### Testing the Server

Run the server manually to check for startup errors:

```bash
uv run r10n mcp
```

The server communicates via stdin/stdout. If it starts without errors, it's ready to accept MCP messages.

---

## See Also

- [Run on Terminal](run-on-terminal.md) — Use r10n interactively via CLI
- [Setup Locally](setup-locally.md) — Install r10n for local development
- [Automations](../automations/index.md) — Detailed docs for each automation
