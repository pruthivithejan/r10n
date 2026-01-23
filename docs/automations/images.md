---
icon: material/image
---

# Images Automation

Optimize, resize, and convert images to WebP for fast web delivery.

## What It Does
- Processes images in a folder (JPEG, PNG, GIF, BMP, TIFF, WebP)
- By default compresses to high-quality WebP (85%)
- Allows control over size, dimensions, and filename handling

## Usage

Interactive:
```bash
uv run r10n images
```

Command-line:
```bash
uv run r10n images --quality 85 --max-width 1920 --max-height 1080
```

## Quick Start Steps
1. Place source images in `local/inputs/images/`
2. Run the automation as above

## Configuration Options
| Option         | Description                                | Default |
|----------------|--------------------------------------------|---------|
| `--quality`    | Compression quality (1-100)                | 85      |
| `--max-size`   | Maximum file size in MB                    | 1.0     |
| `--max-width`  | Maximum width (px)                         | 1920    |
| `--max-height` | Maximum height (px)                        | 1080    |
| `--preserve-names` | Keep original filenames                | true    |

## Output
- Optimized WebP images saved to `local/outputs/images/`

## Troubleshooting
- Images are not showing up? Check input/output folders
- For errors, confirm supported file formats and available disk space