---
icon: lucide/file-pen-line
---

# Rename files

Batch-rename files in a directory using patterns, prefixes, dates, or case
changes.

## Run

Use the guided form to preview changes before applying them:

```bash
r10n rename
```

For a script, specify the input directory and transformation:

```bash
r10n rename \
  --input /path/to/files \
  --prefix archived_ \
  --dry-run \
  --yes
```

Dry-run is enabled by default. Remove `--dry-run` or use `--no-dry-run` to
apply changes. `--yes` skips the review prompt, so only use it after checking
the pattern and target directory.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | — | Directory containing files |
| `--pattern` | `-p` | No | — | Rename pattern supporting `{name}`, `{ext}`, `{sequence}` |
| `--prefix` | — | No | — | Text to add before each filename |
| `--suffix` | — | No | — | Text to add before each extension |
| `--replace-from` | — | No | — | Text to replace in each name |
| `--replace-to` | — | No | — | Replacement text |
| `--lowercase` / `--uppercase` | — | No | `false` | Change filename letter case |
| `--add-date` / `--add-sequence` | — | No | `false` | Add date or sequence number |
| `--recursive` | `-r` | No | `false` | Include nested directories |
| `--file-pattern` | — | No | `*` | Glob used to select files |
| `--dry-run` / `--no-dry-run` | `-n` | No | `true` | Preview or apply changes |
| `--yes` | `-y` | No | `false` | Skip confirmation |

## Safety

The automation previews planned names by default and checks for collisions
before renaming. Keep a backup when renaming important files.

## Troubleshooting

**No files matched:** Check the input directory and `--file-pattern`.

**Name collision:** Adjust the pattern or include a sequence field to make
target names unique.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Get started](../get-started/index.md)
