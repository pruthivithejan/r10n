---
icon: lucide/palette
---

# Colors

Convert CSS color codes to the perceptual `oklch()` format. Makes color editing and mixing more predictable across lightness and hue.

---

## Overview

The Colors automation finds CSS files and converts hex colors, HSL/HSLA, RGB/RGBA, and named colors to the modern `oklch()` color function.

**Key Features:**

- Convert `#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa` formats
- Convert `hsl()`, `hsla()`, `rgb()`, `rgba()` functions
- Convert named CSS colors (e.g., `red`, `rebeccapurple`)
- Process single files or entire directories
- Preserves alpha transparency
- Interactive file selection
- Automatic backup file creation (.bak)

---

## Quick Start

### Run Instantly (No Installation)

```bash
# Convert a single file
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors --file styles.css

# Convert all CSS files in a directory
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors --path ./src
```

### Run Locally

```bash
git clone https://github.com/pruthivithejan/r10n.git
cd r10n
uv sync
uv run r10n colors --file styles.css
```

---

## Usage

### Interactive Mode

Run without arguments for step-by-step prompts:

```bash
uv run r10n colors
```

Example session:

```
╭───────────────────────────────────────────────────────────────╮
│                  CSS Color Converter                           │
│       Convert colors to perceptual oklch() format              │
╰───────────────────────────────────────────────────────────────╯

Step 1/2: Select CSS file or directory
  Process a single file or directory? [file/directory]: file
  Enter path to CSS file [styles.css]: ./src/app.css

Step 2/2: Backup option
  Backup: Enabled (.bak files will be created)

Summary:
  File:   ./src/app.css
  Backup: Enabled

Proceed with color conversion? [y/n]: y

Converting CSS colors to oklch()...

Done!

┌─────────────────────┬──────────────────────────────┐
│ Files found         │ 1                            │
│ Files modified      │ 1                            │
│ Total color changes │ 15                           │
└─────────────────────┴──────────────────────────────┘

Changes made:

./src/app.css (15 changes)
  Line 12: #3b82f6 → oklch(63.3% 0.213 255deg)
  Line 15: hsl(270, 60%, 50%) → oklch(48.4% 0.187 303deg)
  Line 18: #22c55e → oklch(72.3% 0.195 143deg)
  ... and 12 more

Backup files created with .bak extension
```

### Single File Mode

Process a single CSS file:

```bash
uv run r10n colors --file styles.css
```

### Directory Mode

Process all CSS files in a directory:

```bash
uv run r10n colors --path ./src/styles
```

### Non-Interactive Mode

Skip confirmation prompts with `-a`:

```bash
uv run r10n colors --file styles.css --all
```

---

## Parameters

| Parameter | Short | Type | Required | Default | Description |
|-----------|-------|------|----------|---------|-------------|
| `--path` | `-p` | string | No* | `.` | Directory containing CSS files |
| `--file` | `-f` | string | No* | - | Single CSS file to process |
| `--no-backup` | | flag | No | `false` | Don't create `.bak` backup files |
| `--all` | `-a` | flag | No | `false` | Process without confirmation prompt |

*Either `--path` or `--file` should be provided. If neither is given, interactive mode prompts for input.

---

## Examples

### Example 1: Convert Single File

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors \
  --file ./src/app.css
```

### Example 2: Convert Directory

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors \
  --path ./src/styles
```

### Example 3: Convert Without Backup

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors \
  --file styles.css \
  --no-backup
```

### Example 4: Non-Interactive (CI/Scripts)

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors \
  --path ./src \
  --all
```

### Example 5: Interactive Mode

```bash
uvx --from git+https://github.com/pruthivithejan/r10n.git r10n colors
```

---

## Color Conversions

### Input Formats

| Format | Example | Description |
|--------|---------|-------------|
| Hex 3-digit | `#f00` | Short hex |
| Hex 4-digit | `#f00a` | Short hex with alpha |
| Hex 6-digit | `#ff0000` | Full hex |
| Hex 8-digit | `#ff0000aa` | Full hex with alpha |
| HSL | `hsl(0, 100%, 50%)` | Hue, saturation, lightness |
| HSLA | `hsla(0, 100%, 50%, 0.5)` | HSL with alpha |
| RGB | `rgb(255, 0, 0)` | Red, green, blue |
| RGBA | `rgba(255, 0, 0, 0.5)` | RGB with alpha |
| Named | `red`, `rebeccapurple` | CSS color keywords |

### Output Format

All colors are converted to `oklch()`:

```css
/* Input */
.button {
  color: #ff0000;
  background: hsl(240, 100%, 50%);
  border-color: #00ff0080;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* Output */
.button {
  color: oklch(62.8% 0.258 29deg);
  background: oklch(45.2% 0.313 264deg);
  border-color: oklch(86.6% 0.295 143deg / 0.502);
  box-shadow: 0 2px 4px oklch(0% 0 0deg / 0.2);
}
```

---

## Why OKLCH?

OKLCH is a perceptually uniform color space that offers:

1. **Predictable lightness**: Equal steps in L produce equal perceived brightness changes
2. **Consistent chroma**: Colors with the same C value appear equally vivid
3. **Intuitive hue**: H rotates through the color wheel (0-360)
4. **Better gradients**: Smooth transitions without muddy midpoints

### OKLCH Format

```
oklch(L C H / A)
```

| Component | Range | Description |
|-----------|-------|-------------|
| L (Lightness) | 0% - 100% | Perceived brightness |
| C (Chroma) | 0 - 0.4+ | Color intensity/saturation |
| H (Hue) | 0 - 360 | Color angle on the wheel |
| A (Alpha) | 0 - 1 | Transparency (optional) |

---

## Output

The automation modifies CSS files in place:

**Before:**
```css
:root {
  --primary: #3b82f6;
  --secondary: hsl(270, 60%, 50%);
  --accent: #22c55e;
}

.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
```

**After:**
```css
:root {
  --primary: oklch(63.3% 0.213 255deg);
  --secondary: oklch(48.4% 0.187 303deg);
  --accent: oklch(72.3% 0.195 143deg);
}

.card {
  background: oklch(100% 0 0deg);
  border: 1px solid oklch(91.5% 0.006 265deg);
  box-shadow: 0 1px 3px oklch(0% 0 0deg / 0.15);
}
```

### Backup Files

By default, a `.bak` backup file is created for each modified file:

```
styles.css      # Modified file
styles.css.bak  # Original backup
```

Use `--no-backup` to disable backup creation.

---

## Excluded Directories

The following directories are automatically excluded:

- `.venv`, `venv` — Python virtual environments
- `node_modules` — Node.js dependencies
- `.git` — Git directory
- `dist`, `build` — Build output directories
- `__pycache__` — Python cache

---

## Troubleshooting

### "No CSS files found"

Ensure your path contains `.css` files:

```bash
find ./src -name "*.css"
```

### "File not found"

Check the file path is correct:

```bash
ls -la styles.css
```

### Colors Not Converting

The script skips colors that are already in `oklch()` format to prevent double-conversion.

### File Permissions

Ensure you have write access to the CSS files:

```bash
chmod 644 ./styles/*.css
```

### Restoring from Backup

If you need to restore the original file:

```bash
mv styles.css.bak styles.css
```

---

## See Also

- [Images Automation](images.md) — Optimize images for web
- [Get Started Guide](../get-started/index.md) — Setup instructions
- [OKLCH Color Picker](https://oklch.com/) — Interactive OKLCH tool
