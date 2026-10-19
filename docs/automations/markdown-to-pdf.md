---
icon: lucide/file-output
---

# Markdown to PDF

Convert Markdown files or directories to PDF documents.

## Run

Convert one file:

```bash
r10n md2pdf --input /path/to/guide.md
```

Choose an output path and page options:

```bash
r10n md2pdf \
  --input /path/to/guide.md \
  --output /path/to/guide.pdf \
  --page-size Letter \
  --toc \
  --yes
```

By default, the output PDF is created beside its input. Use `--recursive` to
process nested Markdown files in a directory.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | — | Markdown file or directory |
| `--output` | `-o` | No | Beside input | PDF file or output directory |
| `--css` | `-c` | No | — | Optional stylesheet |
| `--page-size` | — | No | `A4` | Page size: A4, Letter, or Legal |
| `--toc` | — | No | `false` | Include a table of contents |
| `--syntax-highlight` | — | No | `true` | Highlight fenced code blocks |
| `--recursive` | `-r` | No | `false` | Process nested directories |
| `--yes` | `-y` | No | `false` | Skip confirmation |

## Output

The automation reports the generated PDF path and any conversion errors.
Existing files at an explicitly selected output path may be replaced; confirm
the destination before running a batch.

## Troubleshooting

**Stylesheet not applied:** Confirm the CSS path is readable and contains valid
styles.

**Directory output missing files:** Use `--recursive` when Markdown files are
in nested directories.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Get started](../get-started/index.md)
