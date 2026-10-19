---
icon: lucide/image
---

# Optimize images

Compress and convert an image directory to WebP.

## Run

Use the guided terminal form:

```bash
r10n images
```

Or provide explicit paths and settings:

```bash
r10n images \
  --input /path/to/photos \
  --output /path/to/optimized \
  --quality 85 \
  --max-size 1 \
  --yes
```

The default output directory is `r10n-output/images`. Change the output root
with `r10n setup`.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | — | Directory of source images |
| `--output` | `-o` | No | `r10n-output/images` | Directory for optimized WebP files |
| `--quality` | `-q` | No | `85` | WebP quality, from 1 to 100 |
| `--max-size` | `-s` | No | `1.0` MB | Maximum output size per image |
| `--prefix` | `-p` | No | `img` | Filename prefix when original names are not preserved |
| `--preserve-names` | — | No | `true` | Keep original filenames |
| `--yes` | `-y` | No | `false` | Skip interactive confirmation |

## Output

The automation writes WebP files and reports processed, skipped, and failed
images. Source files are not modified. Existing output files follow the
automation's overwrite behavior; review the summary before confirming.

## Troubleshooting

**Input directory not found:** Select a valid directory or pass its absolute
path with `--input`.

**Image exceeds the configured size:** Lower `--max-size` or lower `--quality`.
Some source images cannot meet a very small size limit without a visible
quality reduction.

## See also

- [Website images](website-images.md)
- [Logos](logos.md)
- [Terminal configuration](../get-started/terminal-configuration.md)
