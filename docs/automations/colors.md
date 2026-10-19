---
icon: lucide/palette
---

# Convert CSS colors

Convert CSS colors to perceptually consistent `oklch()` values.

## Run

The operation defaults to a safe preview:

```bash
r10n colors --file /path/to/styles.css
```

Convert all CSS files in a directory:

```bash
r10n colors \
  --path /path/to/styles \
  --no-dry-run \
  --yes
```

Review the preview before adding `--no-dry-run`. Backups are created by default.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--path` | `-p` | No | `.` | Directory containing CSS files |
| `--file` | `-f` | No | — | Process one CSS file instead of a directory |
| `--dry-run` | — | No | `true` | Preview without writing changes |
| `--no-dry-run` | — | No | `false` | Write converted CSS |
| `--no-backup` | — | No | `false` | Do not keep `.bak` copies when writing |
| `--yes` | `-y` | No | `false` | Skip the review prompt |

When `--file` is set, it takes precedence over `--path`. Explicit file paths are
used as provided; no project input folder is created.

## Example

Input:

```css
.button {
  color: #3b82f6;
  background: rgb(255 255 255);
}
```

Preview the result, then run with `--no-dry-run` to write changes. The
automation reports the files changed and the number of colors converted.

## Troubleshooting

**No CSS files found:** Check the selected path and ensure it contains `.css`
files. Use `--file` to process a single file.

**Want to undo a conversion:** Restore the generated `.bak` file, unless
`--no-backup` was used.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Get started](../get-started/index.md)
