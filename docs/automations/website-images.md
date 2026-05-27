---
icon: material/image-multiple
---

# Website Images

Download images from a web page and convert them to a chosen file format.

---

## Overview

Website Images scans a website for common image references, follows same-site page links, downloads each raster image, and saves converted files into folders that mirror the website page structure. It supports `img` tags, `srcset`, `picture` sources, page icons, and inline CSS `url(...)` references.

**Key Features:**
- Downloads image references from a website URL and linked same-site pages
- Stores homepage images in the output root and subpage images in matching folders
- Converts images to WebP, PNG, JPG, or JPEG
- Works interactively or with CLI flags for scripts

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n website-images
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n website-images
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n website-images
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n website-images \
  --url https://example.com \
  --output local/outputs/website-images \
  --format webp \
  --quality 85 \
  --max-pages 50 \
  --yes
```

---

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--url` / `-u` | string | Yes | - | Website URL to scan |
| `--output` / `-o` | string | No | `local/outputs/website-images` | Output directory |
| `--format` / `-f` | choice | No | `webp` | Output format: `webp`, `png`, `jpg`, or `jpeg` |
| `--quality` / `-q` | integer | No | `85` | Quality for JPG/WebP output, from 1 to 100 |
| `--timeout` | integer | No | `20` | Request timeout in seconds |
| `--max-pages` | integer | No | `50` | Maximum same-site pages to scan. Use `0` for no limit |
| `--yes` / `-y` | flag | No | `false` | Skip confirmation prompt |

---

## Examples

### Example 1: Basic Usage

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n website-images \
  --url https://example.com \
  --max-pages 50 \
  --yes
```

### Example 2: Convert to PNG

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n website-images \
  --url https://example.com \
  --format png \
  --output downloads/example-images \
  --max-pages 25 \
  --yes
```

### Example 3: Local Installation

```bash
uv run r10n website-images \
  --url https://example.com \
  --output local/outputs/website-images/example \
  --format jpg \
  --quality 90 \
  --max-pages 0 \
  --yes
```

---

## Input Format

The input is a website URL. The command scans that page and follows same-site links found in `<a href="...">` elements:

```text
https://example.com
```

The command scans the HTML for image references in:

```html
<img src="/image.png">
<img srcset="/small.jpg 1x, /large.jpg 2x">
<source srcset="/photo.webp 800w">
<link rel="icon" href="/favicon.png">
<div style="background-image: url('/background.jpg')"></div>
<a href="/about">About</a>
<a href="/tours/rafting/">Rafting</a>
```

---

## Output

- Output location: `local/outputs/website-images/`
- Output format: converted image files in the selected format
- Homepage images: saved directly in the output directory
- Subpage images: saved in folders matching the page path
- File naming: numbered files based on the source filename, such as `001-hero.webp`

Example output:

```text
local/outputs/website-images/
├── 001-home-hero.webp
├── 002-logo.webp
├── about/
│   └── 001-team.webp
└── tours/
    └── rafting/
        ├── 001-rafting-hero.webp
        └── 002-river.webp
```

Unsupported image downloads, such as SVG files or broken URLs, are reported as failed while the rest of the images continue processing.

---

## Troubleshooting

### Common Issues

**Issue: Some images are missing**
- Cause: The website may load images with JavaScript after the page loads.
- Solution: Use the static page URL that contains the image references, or download those assets separately.

**Issue: Not all website pages were scanned**
- Cause: The `--max-pages` limit was reached, or some pages are not linked in static HTML.
- Solution: Increase `--max-pages` or use `--max-pages 0` for no limit.

**Issue: Unsupported image format**
- Cause: The source image may be SVG or another format Pillow cannot convert.
- Solution: Use source raster images such as PNG, JPG, JPEG, or WebP.

**Issue: Website could not be fetched**
- Cause: The URL is invalid, the site is down, or the request timed out.
- Solution: Include `https://` in the URL and try increasing `--timeout`.

---

## See Also

- [Images](./images.md)
- [Get Started Guide](../get-started/index.md)
