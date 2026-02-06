---
icon: lucide/files
---

# Rename Files

Batch rename files using patterns, prefixes, suffixes, and smart transformations. Preview changes before applying them.

---

## Overview

The Rename Files automation helps you standardize filenames across a folder. Use patterns, replace rules, case conversion, and sequencing to quickly clean up messy file names.

**Key Features:**

- Rename with patterns like `{name}_{date}{ext}`
- Add prefixes or suffixes
- Replace text across filenames
- Convert to lowercase or uppercase
- Add dates and sequence numbers
- Preview changes with dry run
- Optional recursive folder processing

---

## Quick Start

### Run Instantly (No Installation)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n rename
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n rename
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n rename
```

Example session:

```
╭───────────────────────────────────────────────────────────────╮
│                         File Renamer                           │
│        Batch rename files with patterns and transformations     │
╰───────────────────────────────────────────────────────────────╯

Step 1/4: Select input directory
  Enter path to directory with files [local/inputs/rename]: ./files

  Found 24 files in: ./files

Step 2/4: Select rename strategy
  Choose rename strategy [pattern/prefix/suffix/replace/case/date/sequence]: pattern
  Enter pattern (use {name}, {ext}, {date}, {sequence}) [{name}_{date}{ext}]: {name}_{sequence}{ext}

Step 3/4: Filter files (optional)
  Filter by file pattern? [all/images/documents/custom]: all

Step 4/4: Preview changes
  Preview changes before renaming (dry run)? [y/n]: y

Summary:
  Input:     ./files (24 files)
  Pattern:   {name}_{sequence}{ext}
  Sequence:  Yes

Dry Run Preview:
┌─────────────────────┬──────────────────────────────┐
│ Total files         │ 24                           │
│ Would rename        │ 24                           │
│ Skipped             │ 0                            │
│ Errors              │ 0                            │
└─────────────────────┴──────────────────────────────┘
```

### Command Line Mode

Pass all options directly:

```bash
uv run r10n rename \
  --input ./files \
  --pattern "{name}_{sequence}{ext}" \
  --add-sequence \
  --dry-run
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--input` | `-i` | string | Yes | `local/inputs/rename` | Input directory with files |
| `--pattern` | `-p` | string | No | - | Pattern with placeholders `{name}`, `{ext}`, `{date}`, `{sequence}` |
| `--prefix` | - | string | No | - | Prefix to add to filenames |
| `--suffix` | - | string | No | - | Suffix to add before extension |
| `--replace-from` | - | string | No | - | Text to replace in filenames |
| `--replace-to` | - | string | No | - | Replacement text |
| `--lowercase` | - | flag | No | `false` | Convert filenames to lowercase |
| `--uppercase` | - | flag | No | `false` | Convert filenames to uppercase |
| `--add-date` | - | flag | No | `false` | Append current date |
| `--add-sequence` | - | flag | No | `false` | Append sequence numbers |
| `--recursive` | `-r` | flag | No | `false` | Process subdirectories |
| `--dry-run` | `-n` | flag | No | `false` | Preview changes only |
| `--file-pattern` | - | string | No | `*` | Glob pattern to filter files |

---

## Examples

### Example 1: Add a Prefix

```bash
uv run r10n rename \
  --input ./photos \
  --prefix "event_"
```

### Example 2: Replace Text

```bash
uv run r10n rename \
  --input ./docs \
  --replace-from "draft" \
  --replace-to "final"
```

### Example 3: Rename Images with Sequence Numbers

```bash
uv run r10n rename \
  --input ./images \
  --pattern "img_{sequence}{ext}" \
  --add-sequence \
  --file-pattern "*.{jpg,jpeg,png}"
```

---

## Input Format

- Input is a directory of files.
- Optional filters can limit which files are renamed.

---

## Output

- Files are renamed in place within the input directory.
- Dry run mode prints a preview without changing anything.

---

## Configuration

No configuration file is required for this automation.

---

## Troubleshooting

**Issue: Files were skipped**
- Cause: The new filename already exists or is unchanged.
- Solution: Adjust your pattern, prefix, or suffix.

**Issue: No files matched**
- Cause: The `--file-pattern` filter didn't match any files.
- Solution: Try a broader pattern like `*` or `*.txt`.

---

## See Also

- [Images](./images.md)
- [Markdown to PDF](./markdown-to-pdf.md)
