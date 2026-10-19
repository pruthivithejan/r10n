---
icon: lucide/briefcase-business
---

# Download logos

Find and download logos for a list of companies or brands.

## Run

```bash
r10n logos
```

The form accepts comma-separated names. For scripting, specify an output
directory and review the selected brands:

```bash
r10n logos \
  --names "Example Co,Northwind" \
  --output /path/to/logos \
  --yes
```

The default destination is `r10n-output/logos`; use `r10n setup` to change the
default output root.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--names` | `-n` | Yes | — | Comma-separated company or brand names |
| `--output` | `-o` | No | `r10n-output/logos` | Download destination |
| `--timeout` | — | No | `5` seconds | Request timeout |
| `--max-candidates` | — | No | `20` | Maximum candidates checked per logo |
| `--overwrite` | — | No | `false` | Replace existing output files |
| `--no-manifest` | — | No | `false` | Do not write a JSON manifest |
| `--yes` | `-y` | No | `false` | Skip interactive confirmation |

## Output

The automation writes each successfully retrieved logo and a JSON manifest
unless `--no-manifest` is set. Failed names appear in the completion summary.

## Troubleshooting

**Logo not found:** Try the company's shorter brand name, check network access,
or increase `--max-candidates`.

**Existing files were kept:** Use `--overwrite` only after reviewing the
destination directory.

## See also

- [Optimize images](images.md)
- [Download website images](website-images.md)
- [Get started](../get-started/index.md)
