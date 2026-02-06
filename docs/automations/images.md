---
icon: lucide/image
---

# Images

Optimize and convert images to WebP format for fast web delivery. Reduce file sizes while maintaining quality.

---

## Overview

The Images automation processes images in a folder, converting them to WebP format with configurable quality, size limits, and dimensions.

**Key Features:**

- Batch process entire folders of images
- Convert JPEG, PNG, GIF, BMP, TIFF to WebP
- Configurable quality and file size limits
- Preserve or rename original filenames
- Automatic dimension scaling

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n images
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n images
```

Example session:

```
╭───────────────────────────────────────────────────────────────╮
│                    Image Optimizer                             │
│          Convert and optimize images for web use               │
╰───────────────────────────────────────────────────────────────╯

Step 1/5: Select input directory
  Enter path to directory with images [local/inputs/images]: ./photos

  Found 42 images in: ./photos

Step 2/5: Set output directory
  Enter output directory [local/outputs/images]: ./optimized

Step 3/5: Set image quality
  Enter quality percentage (1-100) [85]: 85

Step 4/5: Set maximum file size
  Enter maximum file size in MB [1.0]: 1.0

Step 5/5: Set output filenames
  Keep original filenames or use prefix? [keep/prefix]: keep

Summary:
  Input:    ./photos (42 images)
  Output:   ./optimized
  Quality:  85%
  Max size: 1.0MB
  Format:   WebP

Proceed with optimization? [y/n]: y

Optimizing images...

Done!
┌─────────────────────┬──────────────────────────────┐
│ Processed           │ 42                           │
│ Skipped             │ 0                            │
│ Failed              │ 0                            │
│ Output directory    │ ./optimized                  │
└─────────────────────┴──────────────────────────────┘
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n images \
  --input ./photos \
  --output ./optimized \
  --quality 85 \
  --max-size 1.0 \
  --preserve-names
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--input` | `-i` | string | Yes | `local/inputs/images` | Input directory with images |
| `--output` | `-o` | string | No | `local/outputs/images` | Output directory |
| `--quality` | `-q` | int | No | `85` | Image quality (1-100) |
| `--max-size` | `-s` | float | No | `1.0` | Maximum file size in MB |
| `--prefix` | `-p` | string | No | `img` | Prefix for output filenames |
| `--preserve-names` | | flag | No | `false` | Keep original filenames |

---

## Examples

### Example 1: Basic Usage with uvx

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images \
  --input ./photos \
  --output ./optimized
```

### Example 2: High Quality, Large Files Allowed

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images \
  --input ~/Desktop/product-photos \
  --output ~/Desktop/web-ready \
  --quality 95 \
  --max-size 2.0 \
  --preserve-names
```

### Example 3: Aggressive Compression

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images \
  --input ./raw-images \
  --output ./compressed \
  --quality 70 \
  --max-size 0.5
```

### Example 4: With Custom Prefix

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images \
  --input ./uploads \
  --output ./processed \
  --prefix product \
  --quality 85
```

Output filenames: `product1.webp`, `product2.webp`, etc.

### Example 5: Local Installation

```bash
uv run r10n images \
  --input local/inputs/images \
  --output local/outputs/images \
  --quality 85 \
  --preserve-names
```

### Example 6: Interactive Mode

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n images
```

---

## Supported Formats

### Input Formats

| Format | Extensions |
|--------|------------|
| JPEG | `.jpg`, `.jpeg` |
| PNG | `.png` |
| GIF | `.gif` |
| BMP | `.bmp` |
| TIFF | `.tiff`, `.tif` |
| WebP | `.webp` |

### Output Format

All images are converted to **WebP** format, which offers:

- 25-35% smaller files than JPEG at equivalent quality
- Support for transparency (like PNG)
- Wide browser support (Chrome, Firefox, Safari, Edge)

---

## Output

Optimized images are saved to the output directory:

```
local/outputs/images/
├── photo1.webp
├── photo2.webp
├── photo3.webp
└── ...
```

Or with prefix:

```
local/outputs/images/
├── img_001.webp
├── img_002.webp
├── img_003.webp
└── ...
```

---

## Configuration

Advanced configuration is supported programmatically via `ImageOptimizationConfig`.
The CLI currently does not load a config file, so these values are for reference or
for calling the module directly.

```json
{
  "input_directory": "local/inputs/images",
  "output_directory": "local/outputs/images",
  "prefix": "img",
  "max_size_mb": 1.0,
  "quality": 85,
  "max_width": 1920,
  "max_height": 1080,
  "convert_to_webp": true,
  "preserve_aspect_ratio": true,
  "auto_orient": true,
  "preserve_filename": false
}
```

---

## Troubleshooting

### "No images found"

Ensure your input directory contains supported image formats:

```bash
ls -la ./photos/*.{jpg,jpeg,png,gif,bmp,tiff,webp}
```

### Images Are Too Large

Lower the quality or max-size values:

```bash
uv run r10n images --quality 70 --max-size 0.5
```

### Colors Look Different

WebP uses different compression algorithms. For color-critical work, use higher quality (90+).

### "Permission denied"

Ensure you have write permissions to the output directory:

```bash
mkdir -p local/outputs/images
chmod 755 local/outputs/images
```

### Original Files Modified

The automation never modifies original files. It always writes to the output directory.

---

## See Also

- [Contacts Automation](contacts.md) — Generate VCF contact cards
- [Get Started Guide](../get-started/index.md) — Setup instructions
