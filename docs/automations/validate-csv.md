---
icon: lucide/list-checks
---

# Validate CSV

Check a CSV file for missing values, malformed rows, and schema violations.

## Run

Validate a CSV using built-in checks:

```bash
r10n validate --input /path/to/data.csv
```

For stricter rules, provide a JSON schema and choose a report destination:

```bash
r10n validate \
  --input /path/to/data.csv \
  --schema /path/to/schema.json \
  --strict \
  --format json \
  --output /path/to/report.json \
  --yes
```

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | — | CSV file to validate |
| `--schema` | `-s` | No | — | Optional JSON validation schema |
| `--strict` | — | No | `false` | Treat warnings as failures |
| `--trim-whitespace` | — | No | `true` | Trim values before checks |
| `--output` | `-o` | No | — | Optional report file path |
| `--format` | `-f` | No | `text` | Report format: text, JSON, or HTML |
| `--clean` | — | No | `false` | Write a cleaned CSV if validation fails |
| `--yes` | `-y` | No | `false` | Skip confirmation |

## Output

Without `--output`, the report is shown in the terminal. When supplied,
`--output` writes the selected report format to the path you choose.

## Troubleshooting

**Schema rejected:** Confirm that the schema is valid JSON and that its column
names match the CSV header.

**Warnings but no failures:** Use `--strict` if warnings should stop the
workflow, or inspect the detailed report before using `--clean`.

## See also

- [Terminal configuration](../get-started/terminal-configuration.md)
- [Get started](../get-started/index.md)
