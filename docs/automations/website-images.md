---
icon: lucide/images
---

# Download website images

Crawl a website and download its images into a local output directory.

## Run

Use the guided form:

```bash
r10n website-images
```

Or provide a URL and output options:

```bash
r10n website-images \
  --url https://example.com/gallery \
  --output /path/to/downloaded \
  --format webp \
  --max-pages 10 \
  --yes
```

The default output directory is `r10n-output/website-images`. Change the
default output root with `r10n setup`.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--url` | `-u` | Yes | — | Starting page URL |
| `--output` | `-o` | No | `r10n-output/website-images` | Download destination |
| `--format` | `-f` | No | `webp` | Converted image format: WebP, JPG, or PNG |
| `--quality` | `-q` | No | `85` | Quality for lossy formats |
| `--timeout` | — | No | `5` seconds | Request timeout |
| `--max-pages` | — | No | `50` | Same-site pages to crawl; `0` means unlimited |
| `--yes` | `-y` | No | `false` | Skip interactive confirmation |

The crawler restricts page traversal to the starting site. Always review the
URL and crawl limits before running a large scan.

## Output

Downloaded images are converted to the requested format and written under the
output directory. The results include pages scanned, images found, successes,
and failures.

## Troubleshooting

**No images found:** Check the page URL, network access, and whether images are
loaded dynamically by JavaScript.

**Request timeout:** Increase `--timeout` for a slow site or reduce
`--max-pages`.

## See also

- [Optimize images](images.md)
- [Logos](logos.md)
- [Terminal configuration](../get-started/terminal-configuration.md)
