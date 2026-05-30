---
icon: material/vector-square
---

# Logos

Download company logos from the SVGL API into a local folder.

---

## Overview

Logos accepts a comma-separated list of company or brand names, searches the SVGL API, and saves one SVG file per matched name. If SVGL does not have a usable logo for a name, that name is reported as failed.

**Key Features:**
- Accepts names such as `OpenAI, Apple, Google`
- Uses SVGL as the only logo source
- Saves predictable filenames such as `openai.svg`
- Skips existing files by default and supports `--overwrite`

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n logos \
  --names "OpenAI, Apple, Google" \
  --yes
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n logos --names "OpenAI, Apple, Google"
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n logos
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n logos \
  --names "OpenAI, Apple, Google" \
  --output local/outputs/logos \
  --max-candidates 20 \
  --yes
```

---

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--names` / `-n` | string | Yes | - | Comma-separated company or brand names |
| `--output` / `-o` | string | No | `local/outputs/logos` | Output directory |
| `--timeout` | integer | No | `5` | Request timeout in seconds |
| `--max-candidates` | integer | No | `20` | Maximum ranked logo URLs to try per name |
| `--overwrite` | flag | No | `false` | Replace existing logo files |
| `--no-manifest` | flag | No | `false` | Do not write `logos_manifest.json` |
| `--yes` / `-y` | flag | No | `false` | Skip confirmation prompt |

---

## Examples

### Example 1: Basic Usage

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n logos \
  --names "OpenAI, Apple, Google" \
  --yes
```

### Example 2: Save to a Custom Folder

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n logos \
  --names "Stripe, Shopify, Notion" \
  --output downloads/company-logos \
  --yes
```

### Example 3: Replace Existing Logos

```bash
uv run r10n logos \
  --names "Microsoft, GitHub, Figma" \
  --output local/outputs/logos \
  --overwrite \
  --yes
```

---

## Input Format

The input is a comma-separated list of logo names:

```text
OpenAI, Apple, Google, Microsoft
```

Names are trimmed, empty entries are ignored, and duplicates are removed while preserving the original order.

---

## Output

- Output location: `local/outputs/logos/`
- Output format: SVG
- Manifest: `logos_manifest.json`

Example output:

```text
local/outputs/logos/
├── apple.svg
├── google.svg
├── openai.svg
└── logos_manifest.json
```

The manifest includes the source URL, saved file path, format, and download result for each requested name.

---

## Source

The downloader queries the SVGL API only:

```text
https://api.svgl.app?search=<name>
```

Broken or unsupported SVGL candidates are skipped until a working SVG is found. If no SVGL candidate works, the logo is marked as failed.

---

## Troubleshooting

### Common Issues

**Issue: A logo could not be found**
- Cause: SVGL does not have a matching logo for that name.
- Solution: Try the exact brand name, product name, or parent company name.

**Issue: The downloaded logo is an icon instead of a full wordmark**
- Cause: SVGL may publish a brand mark instead of a wordmark for that brand.
- Solution: Increase `--max-candidates` or try a more specific name such as `OpenAI logo` or `Google Cloud`.

**Issue: A logo was skipped**
- Cause: A file with the same name already exists.
- Solution: Use `--overwrite` to replace existing files.

**Issue: Download timed out**
- Cause: The SVGL API responded slowly.
- Solution: Increase `--timeout`.

Always verify brand usage rights before publishing downloaded logos.

---

## See Also

- [Website Images](./website-images.md)
- [Images](./images.md)
- [Get Started Guide](../get-started/index.md)
