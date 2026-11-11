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
| `--css` | `-c` | No | — | Stylesheet with supported element styles |
| `--page-size` | — | No | `A4` | Page size: A4, Letter, or Legal |
| `--toc` | — | No | `false` | Include a linked table of contents |
| `--syntax-highlight` | — | No | `true` | Highlight fenced code blocks with a recognized language |
| `--recursive` | `-r` | No | `false` | Process nested directories |
| `--yes` | `-y` | No | `false` | Skip confirmation |

## Output

The automation reports the generated PDF path and any conversion errors.
Existing files at an explicitly selected output path may be replaced; confirm
the destination before running a batch.

The optional stylesheet supports simple `h1`–`h6`, `p`, `pre`, `code`, and
`blockquote` element selectors, including comma-separated selectors. Supported
properties are `color`, `background-color`, and `font-size` in points, for
example `h1 { color: #336699; font-size: 18pt; }`. Other CSS selectors and
properties are ignored. A table of contents is included only when headings exist.
For syntax highlighting, label a fenced block with a Pygments language name,
such as `python`; unknown languages render as plain code.

## Troubleshooting

**Stylesheet not applied:** Check that the selector and property are among the
supported styles above.

**Directory output missing files:** Use `--recursive` when Markdown files are
in nested directories.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Get started](../get-started/index.md)
